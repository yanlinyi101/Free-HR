import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from free_hr.api import deps as api_deps
from free_hr.api.main import app
from free_hr.db import Base
from free_hr.llm_gateway.fake import FakeLLMProvider
from free_hr.models import JDDraft, RecruitmentRequest, RequestMessage  # noqa: F401


pytestmark = pytest.mark.asyncio


FULL_PROFILE_JSON = (
    '{"position": {"title": "后端工程师", "department": "技术部", "report_to": null, '
    '"headcount": 1, "location": "北京", "start_date": null}, '
    '"responsibilities": ["写API","review代码"], '
    '"hard_requirements": {"education": "本科", "years": "3-5年", "skills": ["Python","FastAPI"], "industry": null}, '
    '"soft_preferences": {"bonus_points": [], "culture_fit": null, "team_style": null}, '
    '"compensation": {"salary_range": "25-40k", "level": null, "employment_type": "全职"}}'
)


@pytest.fixture
async def sqlite_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    RecruitmentRequest.__table__,
                    RequestMessage.__table__,
                    JDDraft.__table__,
                ],
            )
        )
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(sqlite_engine):
    session_maker = async_sessionmaker(sqlite_engine, expire_on_commit=False, class_=AsyncSession)

    async def _fake_db():
        async with session_maker() as s:
            yield s

    llm_holder = {"llm": FakeLLMProvider(script=[FULL_PROFILE_JSON])}
    app.dependency_overrides[api_deps.get_db_dep] = _fake_db
    app.dependency_overrides[api_deps.get_llm_dep] = lambda: llm_holder["llm"]
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c, llm_holder
    finally:
        app.dependency_overrides.clear()


async def test_full_recruitment_flow(client):
    c, llm_holder = client

    r = await c.post("/api/recruitment/requests")
    assert r.status_code == 200, r.text
    req = r.json()
    req_id = req["id"]
    assert req["status"] == "drafting"
    assert req["ready_for_jd"] is False

    r = await c.post(f"/api/recruitment/requests/{req_id}/messages", json={"content": "招聘后端工程师"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ready_for_jd"] is True
    assert body["profile"]["position"]["title"] == "后端工程师"

    llm_holder["llm"] = FakeLLMProvider(script=["# 后端工程师\n\n## 岗位职责\n- 写API\n\n## 任职要求\n- Python"])
    app.dependency_overrides[api_deps.get_llm_dep] = lambda: llm_holder["llm"]
    r = await c.post(f"/api/recruitment/requests/{req_id}/jd")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending_review"
    assert body["jd"]["content_md"].startswith("# 后端工程师")

    r = await c.patch(
        f"/api/recruitment/requests/{req_id}",
        json={"edited_content_md": "# 后端（编辑版）"},
    )
    assert r.status_code == 200
    assert r.json()["jd"]["edited_content_md"] == "# 后端（编辑版）"

    r = await c.patch(f"/api/recruitment/requests/{req_id}", json={"action": "approve"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    r = await c.patch(f"/api/recruitment/requests/{req_id}", json={"action": "approve"})
    assert r.status_code == 409


async def test_generate_jd_before_ready_returns_400(client):
    c, _ = client

    app.dependency_overrides[api_deps.get_llm_dep] = lambda: FakeLLMProvider(script=["{}"])
    r = await c.post("/api/recruitment/requests")
    req_id = r.json()["id"]

    r = await c.post(f"/api/recruitment/requests/{req_id}/jd")
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "missing_fields"


async def test_list_requests_returns_items(client):
    c, _ = client
    await c.post("/api/recruitment/requests")
    await c.post("/api/recruitment/requests")
    r = await c.get("/api/recruitment/requests")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2
    assert {"id", "title", "status", "updated_at"} <= set(items[0].keys())


async def test_get_request_404(client):
    c, _ = client
    r = await c.get("/api/recruitment/requests/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
