# 招聘需求协作模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Free-HR 的新模块「招聘需求协作」：业务提需求 → AI 多轮对话抽取候选人画像 → 字段齐备后生成 JD → HR 审核并通过。

**Architecture:** 后端新增独立 `recruitment` 模块（models / extractor / jd_generator / service / api routes），复用现有 `LLMProvider` 与 `AsyncSession`；不复用 `/api/chat`。前端在 Next.js App Router 下新增 `/recruitment` 列表页与 `/recruitment/[id]` 详情页，顶部导航加入口。抽取用 LLM 结构化 JSON 输出（低温度），回复用自然对话（两次独立调用）。状态机两态：`drafting → pending_review → approved`。

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + pgvector (已有) + pytest / httpx；Next.js App Router + React + lib/api.ts fetch 客户端。

**Spec 引用:** [docs/superpowers/specs/2026-04-18-recruitment-request-collab-design.md](../specs/2026-04-18-recruitment-request-collab-design.md)

---

## File Structure

### Backend（新增）

| 路径 | 职责 |
|---|---|
| `backend/src/free_hr/recruitment/__init__.py` | 包标记 |
| `backend/src/free_hr/recruitment/schemas.py` | Pydantic 模型：`Profile`、`RequestRead`、`MessageRead`、`PostMessageResponse`、`JDRead` |
| `backend/src/free_hr/recruitment/profile.py` | 纯函数：`empty_profile()`、`merge_profile(old, new)`、`missing_fields(profile)`、`is_ready_for_jd(profile)` |
| `backend/src/free_hr/recruitment/extractor.py` | `extract_profile(llm, history, current_profile) -> Profile`（LLM 结构化抽取 + JSON 解析回退） |
| `backend/src/free_hr/recruitment/jd_generator.py` | `generate_jd(llm, profile) -> str`（返回 Markdown） |
| `backend/src/free_hr/recruitment/service.py` | 编排：`create_request`、`append_user_message`（抽取 + 回复 + 持久化）、`generate_and_save_jd`、`patch_request` |
| `backend/src/free_hr/recruitment/llm_util.py` | 辅助：`collect_full_text(llm, messages, opts)` — 把 `chat_stream` 聚成完整字符串 |
| `backend/src/free_hr/api/routes/recruitment.py` | FastAPI 路由 `/api/recruitment/*` |

### Backend（修改）

| 路径 | 修改内容 |
|---|---|
| `backend/src/free_hr/models.py` | 追加 `RecruitmentRequest` / `RequestMessage` / `JDDraft` ORM 类 |
| `backend/src/free_hr/api/main.py` | `include_router(recruitment_routes.router)` |
| `backend/migrations/versions/0003_recruitment.py` | 新 Alembic revision |

### Backend 测试（新增）

| 路径 | 职责 |
|---|---|
| `backend/tests/unit/test_recruitment_profile.py` | 合并/缺项/ready 判定 |
| `backend/tests/unit/test_recruitment_extractor.py` | mock LLM，验证 JSON 解析、重试、回退 |
| `backend/tests/unit/test_recruitment_jd_generator.py` | mock LLM，验证 prompt 包含 profile、返回 Markdown |
| `backend/tests/unit/test_recruitment_service.py` | 状态机、必填校验 |
| `backend/tests/integration/test_recruitment_api.py` | 全链路：创建 → 对话 → 生成 JD → 审核通过（mock LLM，stub DB） |

### Frontend（新增）

| 路径 | 职责 |
|---|---|
| `frontend/lib/recruitment.ts` | API 客户端：`createRequest`、`listRequests`、`getRequest`、`postMessage`、`generateJD`、`patchRequest`；类型定义 |
| `frontend/app/recruitment/page.tsx` | 列表页 |
| `frontend/app/recruitment/[id]/page.tsx` | 详情页（对话 + 画像卡片 + JD 预览） |
| `frontend/components/ProfileCard.tsx` | 右栏上半：画像字段卡片 |
| `frontend/components/JDPanel.tsx` | 右栏下半：JD 预览 + 编辑 + 通过按钮 |
| `frontend/components/RecruitmentChat.tsx` | 左栏：对话 UI（简化版，不复用 ChatPanel 避免纠缠法律 RAG 逻辑） |

### Frontend（修改）

| 路径 | 修改内容 |
|---|---|
| `frontend/components/Sidebar.tsx` 或 `frontend/app/layout.tsx` | 增加「招聘协作」入口（取决于现有导航实现） |
| `frontend/app/page.tsx` | 不改（保留法律问答首页） |

### 文档（修改）

| 路径 | 修改内容 |
|---|---|
| `README.md` | API 概览表追加 `/api/recruitment/*`；MVP 包含内容补一行 |

---

## Important Codebase Conventions

在写任何代码前，执行这些已知的约定：

1. **Backend 包路径**：import 一律从 `free_hr.*` 开始（`src/free_hr` 是 src-layout 包根），路由内部 import 用相对路径（如 `from ...recruitment.service import ...`）。
2. **LLM 只有流式接口**：`LLMProvider.chat_stream(messages, opts)` → `AsyncIterator[ChatCompletionChunk]`。要取完整字符串必须累积 `chunk.delta_text`。参见 `backend/src/free_hr/chat/service.py:51-58`。我们在 `recruitment/llm_util.py` 提供统一辅助。
3. **DB session**：路由通过 `Depends(get_db_dep)` 获取 `AsyncSession`；测试用 `app.dependency_overrides` 覆盖（参考 `backend/tests/integration/test_api_endpoints.py:13-27`）。
4. **Next.js 注意**：前端 CLAUDE.md/AGENTS.md 明确说明 **"This is NOT the Next.js you know"**。在写任何 `app/` 下的页面、`use client`、`Link`、`fetch`、metadata 等之前，先读 `frontend/node_modules/next/dist/docs/` 下相关章节。
5. **测试异步**：`pytestmark = pytest.mark.asyncio` 放文件顶部。已装 `pytest-asyncio`。
6. **Pydantic 版本**：项目用 Pydantic v2（`model_dump()`、`model_validate()`）。
7. **现有迁移命名**：`0001_initial_auth_chat.py`、`0002_knowledge_store.py`。新迁移用 `0003_recruitment.py`，`down_revision = "0002_knowledge_store"`（需确认现有 revision id，见 Task 1 Step 0）。

---

## Task 0: 模块骨架与导入占位

**Files:**
- Create: `backend/src/free_hr/recruitment/__init__.py`

- [ ] **Step 1: 创建包目录与空 `__init__.py`**

```python
# backend/src/free_hr/recruitment/__init__.py
"""Recruitment request collaboration module."""
```

- [ ] **Step 2: 验证 import 正常**

Run: `cd backend && uv run python -c "import free_hr.recruitment; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/src/free_hr/recruitment/__init__.py
git commit -m "feat(recruitment): scaffold module package"
```

---

## Task 1: DB 模型 + Alembic 迁移

### Step 0: 确认上一条 revision id

在写迁移前，读 `backend/migrations/versions/0002_knowledge_store.py` 顶部的 `revision = "..."` 字符串，记下来作为新迁移的 `down_revision`。

**Files:**
- Modify: `backend/src/free_hr/models.py` (append at end of file)
- Create: `backend/migrations/versions/0003_recruitment.py`

- [ ] **Step 1: 在 `models.py` 末尾追加三张表模型**

```python
# Append to backend/src/free_hr/models.py


class RecruitmentRequest(Base):
    __tablename__ = "recruitment_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('drafting','pending_review','approved')",
            name="recruitment_requests_status_ck",
        ),
        Index("ix_recruitment_requests_status_updated", "status", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="drafting")
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    messages: Mapped[list["RequestMessage"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="RequestMessage.created_at"
    )
    jd_draft: Mapped["JDDraft | None"] = relationship(
        back_populates="request", cascade="all, delete-orphan", uselist=False
    )


class RequestMessage(Base):
    __tablename__ = "recruitment_request_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="recruitment_messages_role_ck"),
        Index("ix_recruitment_messages_request_created", "request_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recruitment_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request: Mapped[RecruitmentRequest] = relationship(back_populates="messages")


class JDDraft(Base):
    __tablename__ = "recruitment_jd_drafts"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recruitment_requests.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    edited_content_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    request: Mapped[RecruitmentRequest] = relationship(back_populates="jd_draft")
```

- [ ] **Step 2: 创建 Alembic migration `0003_recruitment.py`**

```python
# backend/migrations/versions/0003_recruitment.py
"""recruitment module tables

Revision ID: 0003_recruitment
Revises: <PUT_0002_REVISION_ID_HERE>
Create Date: 2026-04-18
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID


revision = "0003_recruitment"
down_revision = "<PUT_0002_REVISION_ID_HERE>"  # 替换为 Step 0 记下的 id
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recruitment_requests",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="drafting"),
        sa.Column("profile", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('drafting','pending_review','approved')",
            name="recruitment_requests_status_ck",
        ),
    )
    op.create_index(
        "ix_recruitment_requests_status_updated",
        "recruitment_requests",
        ["status", "updated_at"],
    )

    op.create_table(
        "recruitment_request_messages",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("recruitment_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('user','assistant')", name="recruitment_messages_role_ck"),
    )
    op.create_index(
        "ix_recruitment_messages_request_created",
        "recruitment_request_messages",
        ["request_id", "created_at"],
    )

    op.create_table(
        "recruitment_jd_drafts",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("recruitment_requests.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("content_md", sa.Text, nullable=False),
        sa.Column("edited_content_md", sa.Text, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("recruitment_jd_drafts")
    op.drop_index("ix_recruitment_messages_request_created", table_name="recruitment_request_messages")
    op.drop_table("recruitment_request_messages")
    op.drop_index("ix_recruitment_requests_status_updated", table_name="recruitment_requests")
    op.drop_table("recruitment_requests")
```

- [ ] **Step 3: 验证模型可导入**

Run: `cd backend && uv run python -c "from free_hr.models import RecruitmentRequest, RequestMessage, JDDraft; print('ok')"`
Expected: `ok`

- [ ] **Step 4（可选、若有真 DB）: 运行迁移**

Run: `cd backend && uv run alembic upgrade head`
Expected: 新表创建成功。若没有本地 DB，跳过，不阻塞后续（集成测试用 mock）。

- [ ] **Step 5: Commit**

```bash
git add backend/src/free_hr/models.py backend/migrations/versions/0003_recruitment.py
git commit -m "feat(recruitment): add ORM models and alembic migration"
```

---

## Task 2: Profile 纯函数（schema + 合并 + 缺项判定）

**Files:**
- Create: `backend/src/free_hr/recruitment/schemas.py`
- Create: `backend/src/free_hr/recruitment/profile.py`
- Create: `backend/tests/unit/test_recruitment_profile.py`

- [ ] **Step 1: 先写测试 `test_recruitment_profile.py`（TDD）**

```python
# backend/tests/unit/test_recruitment_profile.py
from free_hr.recruitment.profile import (
    empty_profile,
    merge_profile,
    missing_fields,
    is_ready_for_jd,
)


def test_empty_profile_has_all_keys():
    p = empty_profile()
    assert p["position"]["title"] is None
    assert p["responsibilities"] == []
    assert p["hard_requirements"]["skills"] == []
    assert p["compensation"]["salary_range"] is None


def test_merge_prefers_new_non_null_over_old():
    old = empty_profile()
    old["position"]["title"] = "后端"
    new = empty_profile()
    new["position"]["title"] = "资深后端"
    new["position"]["department"] = "技术部"
    merged = merge_profile(old, new)
    assert merged["position"]["title"] == "资深后端"
    assert merged["position"]["department"] == "技术部"


def test_merge_does_not_clear_filled_field_with_null():
    old = empty_profile()
    old["position"]["title"] = "后端"
    new = empty_profile()  # title 是 None
    merged = merge_profile(old, new)
    assert merged["position"]["title"] == "后端"  # 不被 None 覆盖


def test_merge_does_not_clear_filled_list_with_empty():
    old = empty_profile()
    old["responsibilities"] = ["写代码"]
    new = empty_profile()  # []
    merged = merge_profile(old, new)
    assert merged["responsibilities"] == ["写代码"]


def test_missing_fields_lists_required_when_empty():
    p = empty_profile()
    missing = missing_fields(p)
    assert "position.title" in missing
    assert "position.department" in missing
    assert "responsibilities" in missing
    assert "hard_requirements.skills" in missing
    assert "compensation.salary_range" in missing


def test_is_ready_for_jd_requires_all_required():
    p = empty_profile()
    p["position"]["title"] = "后端"
    p["position"]["department"] = "技术部"
    p["responsibilities"] = ["写代码"]
    p["hard_requirements"]["skills"] = ["Python"]
    assert is_ready_for_jd(p) is False  # 缺 salary_range
    p["compensation"]["salary_range"] = "25-40k"
    assert is_ready_for_jd(p) is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/unit/test_recruitment_profile.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'free_hr.recruitment.profile'`

- [ ] **Step 3: 写 `schemas.py`（Pydantic 模型，给 extractor / API 用）**

```python
# backend/src/free_hr/recruitment/schemas.py
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class Position(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    report_to: Optional[str] = None
    headcount: Optional[int] = None
    location: Optional[str] = None
    start_date: Optional[str] = None  # 自由文本，如 "2026Q3" / "ASAP"


class HardRequirements(BaseModel):
    education: Optional[str] = None
    years: Optional[str] = None  # "3-5年"
    skills: list[str] = Field(default_factory=list)
    industry: Optional[str] = None


class SoftPreferences(BaseModel):
    bonus_points: list[str] = Field(default_factory=list)
    culture_fit: Optional[str] = None
    team_style: Optional[str] = None


class Compensation(BaseModel):
    salary_range: Optional[str] = None
    level: Optional[str] = None
    employment_type: Optional[str] = None  # 全职/外包/实习


class Profile(BaseModel):
    position: Position = Field(default_factory=Position)
    responsibilities: list[str] = Field(default_factory=list)
    hard_requirements: HardRequirements = Field(default_factory=HardRequirements)
    soft_preferences: SoftPreferences = Field(default_factory=SoftPreferences)
    compensation: Compensation = Field(default_factory=Compensation)


Status = Literal["drafting", "pending_review", "approved"]


class MessageRead(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class JDRead(BaseModel):
    content_md: str
    edited_content_md: Optional[str] = None
    generated_at: datetime
    approved_at: Optional[datetime] = None


class RequestRead(BaseModel):
    id: UUID
    title: str
    status: Status
    profile: dict  # 存为 dict（JSONB），外层 Profile 仅用于类型校验
    missing_fields: list[str]
    ready_for_jd: bool
    messages: list[MessageRead] = Field(default_factory=list)
    jd: Optional[JDRead] = None
    created_at: datetime
    updated_at: datetime


class RequestListItem(BaseModel):
    id: UUID
    title: str
    status: Status
    updated_at: datetime


class PostMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class PostMessageResponse(BaseModel):
    assistant_message: MessageRead
    profile: dict
    missing_fields: list[str]
    ready_for_jd: bool


class PatchRequestBody(BaseModel):
    edited_content_md: Optional[str] = None
    action: Optional[Literal["approve"]] = None
```

- [ ] **Step 4: 写 `profile.py`**

```python
# backend/src/free_hr/recruitment/profile.py
from __future__ import annotations
from copy import deepcopy
from typing import Any


REQUIRED_FIELDS: list[str] = [
    "position.title",
    "position.department",
    "responsibilities",
    "hard_requirements.skills",
    "compensation.salary_range",
]

# Priority order for LLM prompt: 必填优先，其他次之
FIELD_PRIORITY: list[str] = REQUIRED_FIELDS + [
    "position.location",
    "position.headcount",
    "position.report_to",
    "position.start_date",
    "hard_requirements.years",
    "hard_requirements.education",
    "hard_requirements.industry",
    "compensation.level",
    "compensation.employment_type",
    "soft_preferences.bonus_points",
    "soft_preferences.culture_fit",
    "soft_preferences.team_style",
]


def empty_profile() -> dict[str, Any]:
    return {
        "position": {
            "title": None,
            "department": None,
            "report_to": None,
            "headcount": None,
            "location": None,
            "start_date": None,
        },
        "responsibilities": [],
        "hard_requirements": {
            "education": None,
            "years": None,
            "skills": [],
            "industry": None,
        },
        "soft_preferences": {
            "bonus_points": [],
            "culture_fit": None,
            "team_style": None,
        },
        "compensation": {
            "salary_range": None,
            "level": None,
            "employment_type": None,
        },
    }


def _get(profile: dict[str, Any], path: str) -> Any:
    cur: Any = profile
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, str)) and len(value) == 0:
        return True
    return False


def merge_profile(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Return a new profile where non-empty fields in `new` overwrite `old`.
    Empty/null fields in `new` never clear filled fields in `old`.
    """
    result = deepcopy(old)

    def _merge(dst: dict[str, Any], src: dict[str, Any]) -> None:
        for key, val in src.items():
            if isinstance(val, dict):
                if not isinstance(dst.get(key), dict):
                    dst[key] = {}
                _merge(dst[key], val)
            else:
                if not _is_empty(val):
                    dst[key] = val

    _merge(result, new)
    return result


def missing_fields(profile: dict[str, Any]) -> list[str]:
    return [f for f in FIELD_PRIORITY if _is_empty(_get(profile, f))]


def is_ready_for_jd(profile: dict[str, Any]) -> bool:
    return all(not _is_empty(_get(profile, f)) for f in REQUIRED_FIELDS)
```

- [ ] **Step 5: 运行测试，全部通过**

Run: `cd backend && uv run pytest tests/unit/test_recruitment_profile.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/src/free_hr/recruitment/schemas.py backend/src/free_hr/recruitment/profile.py backend/tests/unit/test_recruitment_profile.py
git commit -m "feat(recruitment): profile schema, merge and missing-field logic"
```

---

## Task 3: LLM 文本收集辅助 + Extractor

**Files:**
- Create: `backend/src/free_hr/recruitment/llm_util.py`
- Create: `backend/src/free_hr/recruitment/extractor.py`
- Create: `backend/tests/unit/test_recruitment_extractor.py`

- [ ] **Step 1: 写 `llm_util.py`（把流式聚成完整字符串）**

```python
# backend/src/free_hr/recruitment/llm_util.py
from __future__ import annotations
from collections.abc import Sequence

from ..llm_gateway import ChatMessage, ChatOptions, LLMProvider


async def collect_full_text(
    llm: LLMProvider, messages: Sequence[ChatMessage], opts: ChatOptions | None = None
) -> str:
    buf: list[str] = []
    async for chunk in llm.chat_stream(messages, opts or ChatOptions()):
        if chunk.delta_text:
            buf.append(chunk.delta_text)
    return "".join(buf)
```

- [ ] **Step 2: 写 extractor 测试（TDD）**

```python
# backend/tests/unit/test_recruitment_extractor.py
import pytest
from free_hr.llm_gateway.fake import FakeLLMProvider
from free_hr.recruitment.extractor import extract_profile
from free_hr.recruitment.profile import empty_profile


pytestmark = pytest.mark.asyncio


async def test_extract_merges_new_fields():
    llm = FakeLLMProvider(script=[
        '{"position": {"title": "后端工程师", "department": "技术部"}, '
        '"responsibilities": ["写API"], "hard_requirements": {"skills": ["Python"]}, '
        '"soft_preferences": {}, "compensation": {}}'
    ])
    history = [{"role": "user", "content": "招后端，技术部，写API，要会Python"}]
    result = await extract_profile(llm, history=history, current_profile=empty_profile())
    assert result["position"]["title"] == "后端工程师"
    assert result["responsibilities"] == ["写API"]
    assert result["hard_requirements"]["skills"] == ["Python"]


async def test_extract_preserves_old_when_llm_returns_null():
    llm = FakeLLMProvider(script=[
        '{"position": {"title": null}, "responsibilities": [], '
        '"hard_requirements": {"skills": []}, "soft_preferences": {}, "compensation": {}}'
    ])
    current = empty_profile()
    current["position"]["title"] = "已填后端"
    result = await extract_profile(llm, history=[{"role": "user", "content": "..."}], current_profile=current)
    assert result["position"]["title"] == "已填后端"


async def test_extract_falls_back_on_invalid_json():
    llm = FakeLLMProvider(script=["不是 JSON 的自然语言回答"])
    current = empty_profile()
    current["position"]["title"] = "后端"
    result = await extract_profile(llm, history=[{"role": "user", "content": "x"}], current_profile=current)
    # 回退：返回原 profile 不变
    assert result == current


async def test_extract_accepts_json_with_code_fence():
    llm = FakeLLMProvider(script=[
        '```json\n{"position": {"title": "PM"}, "responsibilities": [], '
        '"hard_requirements": {"skills": []}, "soft_preferences": {}, "compensation": {}}\n```'
    ])
    result = await extract_profile(llm, history=[{"role": "user", "content": "x"}], current_profile=empty_profile())
    assert result["position"]["title"] == "PM"
```

注：`FakeLLMProvider.chat_stream` 把 script[0] 按空格切 token 发射；JSON 里空格会被拆，但 `collect_full_text` 拼回后（每个 token 末尾带空格）得到带多余空格的 JSON。`json.loads` 对多余空格容忍，测试成立。若 FakeLLM 行为与预期不符，改写 `extract_profile` 时去首尾空白与冗余空格再解析。

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/unit/test_recruitment_extractor.py -v`
Expected: FAIL `ModuleNotFoundError: free_hr.recruitment.extractor`

- [ ] **Step 4: 写 `extractor.py`**

```python
# backend/src/free_hr/recruitment/extractor.py
from __future__ import annotations
import json
import logging
import re
from typing import Any

from ..llm_gateway import ChatMessage, ChatOptions, LLMProvider
from .llm_util import collect_full_text
from .profile import merge_profile

log = logging.getLogger("free_hr.recruitment.extractor")


SYSTEM_PROMPT = """你是招聘需求抽取助手。根据对话历史，把用户**明确提到**的岗位信息抽成严格 JSON。
不要推断、不要编造。用户没提的字段一律返回 null 或空数组。

输出必须是且仅是一个 JSON 对象，结构如下（所有字段都必须出现）：
{
  "position": {"title": null, "department": null, "report_to": null, "headcount": null, "location": null, "start_date": null},
  "responsibilities": [],
  "hard_requirements": {"education": null, "years": null, "skills": [], "industry": null},
  "soft_preferences": {"bonus_points": [], "culture_fit": null, "team_style": null},
  "compensation": {"salary_range": null, "level": null, "employment_type": null}
}

不要输出 JSON 之外的任何文字，不要加 ```json 标签外的解释。
"""


def _format_history(history: list[dict[str, str]]) -> str:
    return "\n".join(f"[{m['role']}] {m['content']}" for m in history)


def _parse_json(text: str) -> dict[str, Any] | None:
    """Try to extract a JSON object from LLM output, tolerating code fences and extra whitespace."""
    cleaned = text.strip()
    # Strip ```json fences
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    # Collapse internal whitespace introduced by fake tokenizer
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        # Find first { ... last } as fallback
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
    return None


async def extract_profile(
    llm: LLMProvider,
    *,
    history: list[dict[str, str]],
    current_profile: dict[str, Any],
) -> dict[str, Any]:
    """Extract profile from dialog history and merge with current_profile.
    On parse failure, return current_profile unchanged.
    """
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=f"已知画像:\n{json.dumps(current_profile, ensure_ascii=False)}\n\n对话:\n{_format_history(history)}"),
    ]
    opts = ChatOptions(temperature=0.0, max_tokens=1024)
    text = await collect_full_text(llm, messages, opts)

    parsed = _parse_json(text)
    if parsed is None:
        log.warning("extract_profile: JSON parse failed, keeping old profile")
        return current_profile

    return merge_profile(current_profile, parsed)
```

- [ ] **Step 5: 运行测试，全部通过**

Run: `cd backend && uv run pytest tests/unit/test_recruitment_extractor.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/src/free_hr/recruitment/llm_util.py backend/src/free_hr/recruitment/extractor.py backend/tests/unit/test_recruitment_extractor.py
git commit -m "feat(recruitment): LLM profile extractor with JSON fallback"
```

---

## Task 4: JD Generator

**Files:**
- Create: `backend/src/free_hr/recruitment/jd_generator.py`
- Create: `backend/tests/unit/test_recruitment_jd_generator.py`

- [ ] **Step 1: 写测试**

```python
# backend/tests/unit/test_recruitment_jd_generator.py
import pytest
from free_hr.llm_gateway.fake import FakeLLMProvider
from free_hr.recruitment.jd_generator import generate_jd
from free_hr.recruitment.profile import empty_profile


pytestmark = pytest.mark.asyncio


async def test_generate_jd_returns_text():
    llm = FakeLLMProvider(script=[
        "# 后端工程师\n\n## 岗位职责\n- 写API\n\n## 任职要求\n- Python\n\n## 薪资福利\n25-40k"
    ])
    p = empty_profile()
    p["position"]["title"] = "后端工程师"
    p["position"]["department"] = "技术部"
    p["responsibilities"] = ["写API"]
    p["hard_requirements"]["skills"] = ["Python"]
    p["compensation"]["salary_range"] = "25-40k"

    md = await generate_jd(llm, p)
    assert "后端工程师" in md
    assert "岗位职责" in md or "任职要求" in md
    assert len(md) > 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/unit/test_recruitment_jd_generator.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写 `jd_generator.py`**

```python
# backend/src/free_hr/recruitment/jd_generator.py
from __future__ import annotations
import json
from typing import Any

from ..llm_gateway import ChatMessage, ChatOptions, LLMProvider
from .llm_util import collect_full_text


SYSTEM_PROMPT = """你是一名资深 HR，基于以下候选人画像，撰写一份清晰、专业、可直接发布的 JD（职位描述）。

要求：
- 使用 Markdown 格式
- 按固定段落组织：一级标题为职位名称，然后依次为：## 岗位职责、## 任职要求、## 薪资福利、## 工作地点与汇报
- "岗位职责"用 bullet list，动宾短语，每条 10-30 字
- "任职要求"分硬性要求与加分项两组
- 不要编造画像中没有的信息；画像缺失的段落（如薪资）用画像提供的原文照抄
- 不输出 JSON、不输出解释、不要加额外的封面/签名
"""


async def generate_jd(llm: LLMProvider, profile: dict[str, Any]) -> str:
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=f"候选人画像（JSON）：\n{json.dumps(profile, ensure_ascii=False, indent=2)}",
        ),
    ]
    opts = ChatOptions(temperature=0.3, max_tokens=2048)
    text = await collect_full_text(llm, messages, opts)
    return text.strip()
```

- [ ] **Step 4: 运行测试通过**

Run: `cd backend && uv run pytest tests/unit/test_recruitment_jd_generator.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/free_hr/recruitment/jd_generator.py backend/tests/unit/test_recruitment_jd_generator.py
git commit -m "feat(recruitment): JD markdown generator"
```

---

## Task 5: Service 编排（DB 交互 + 状态机）

**Files:**
- Create: `backend/src/free_hr/recruitment/service.py`
- Create: `backend/tests/unit/test_recruitment_service.py`

- [ ] **Step 1: 写 service 单测（只测不依赖 DB 的纯逻辑 helper；DB 路径在集成测试覆盖）**

```python
# backend/tests/unit/test_recruitment_service.py
import pytest
from free_hr.recruitment.service import (
    StateError,
    validate_transition_to_pending_review,
    validate_transition_to_approved,
    derive_title,
)
from free_hr.recruitment.profile import empty_profile


def test_derive_title_from_profile():
    p = empty_profile()
    assert derive_title(p, fallback="新需求-X").startswith("新需求")
    p["position"]["title"] = "后端工程师"
    assert derive_title(p, fallback="新需求-X") == "后端工程师"
    p["position"]["department"] = "技术部"
    assert derive_title(p, fallback="新需求-X") == "技术部 · 后端工程师"


def test_validate_transition_to_pending_review_requires_drafting_and_ready():
    p = empty_profile()
    # ready=False
    with pytest.raises(StateError, match="missing_fields"):
        validate_transition_to_pending_review(status="drafting", profile=p)
    # 状态错
    p["position"]["title"] = "T"
    p["position"]["department"] = "D"
    p["responsibilities"] = ["R"]
    p["hard_requirements"]["skills"] = ["S"]
    p["compensation"]["salary_range"] = "X"
    with pytest.raises(StateError, match="invalid_state"):
        validate_transition_to_pending_review(status="approved", profile=p)
    # OK
    validate_transition_to_pending_review(status="drafting", profile=p)


def test_validate_transition_to_approved_requires_pending_review():
    with pytest.raises(StateError, match="invalid_state"):
        validate_transition_to_approved(status="drafting")
    with pytest.raises(StateError, match="invalid_state"):
        validate_transition_to_approved(status="approved")
    validate_transition_to_approved(status="pending_review")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/unit/test_recruitment_service.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写 `service.py`**

```python
# backend/src/free_hr/recruitment/service.py
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..llm_gateway import ChatMessage, ChatOptions, LLMProvider
from ..models import JDDraft, RecruitmentRequest, RequestMessage
from .extractor import extract_profile
from .jd_generator import generate_jd
from .llm_util import collect_full_text
from .profile import empty_profile, is_ready_for_jd, missing_fields


class StateError(Exception):
    """Raised when a state transition is invalid. Message includes a machine-readable code."""


REPLY_SYSTEM_PROMPT = """你是 HR 助手，帮业务部门梳理招聘需求。基于已知画像和缺项，自然地追问 1-2 个最相关的缺项（不要像填表单一样逐项盘问）。
若用户在上一轮提供了新信息，先简短确认（1 句），再追问缺项。
语气专业、友好、中文。不要输出 JSON 或代码块。
如果所有必填字段都已填写，告诉用户"信息已经齐备，可以点'生成 JD'了"。
"""


@dataclass
class MessageTurn:
    user_content: str
    assistant_content: str
    profile: dict[str, Any]
    missing: list[str]
    ready: bool


def derive_title(profile: dict[str, Any], *, fallback: str) -> str:
    title = profile.get("position", {}).get("title")
    dept = profile.get("position", {}).get("department")
    if title and dept:
        return f"{dept} · {title}"
    if title:
        return title
    return fallback


def validate_transition_to_pending_review(*, status: str, profile: dict[str, Any]) -> None:
    if status != "drafting":
        raise StateError("invalid_state")
    if not is_ready_for_jd(profile):
        raise StateError(f"missing_fields:{','.join(missing_fields(profile))}")


def validate_transition_to_approved(*, status: str) -> None:
    if status != "pending_review":
        raise StateError("invalid_state")


async def create_request(session: AsyncSession) -> RecruitmentRequest:
    now_tag = uuid.uuid4().hex[:8]
    req = RecruitmentRequest(
        title=f"新需求-{now_tag}",
        status="drafting",
        profile=empty_profile(),
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def get_request(session: AsyncSession, request_id: uuid.UUID) -> RecruitmentRequest | None:
    stmt = (
        select(RecruitmentRequest)
        .options(selectinload(RecruitmentRequest.messages), selectinload(RecruitmentRequest.jd_draft))
        .where(RecruitmentRequest.id == request_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_requests(session: AsyncSession) -> list[RecruitmentRequest]:
    stmt = select(RecruitmentRequest).order_by(RecruitmentRequest.updated_at.desc())
    return list((await session.execute(stmt)).scalars().all())


MAX_TURNS = 20


async def append_user_message(
    session: AsyncSession,
    *,
    llm: LLMProvider,
    request: RecruitmentRequest,
    user_content: str,
) -> MessageTurn:
    if len(request.messages) // 2 >= MAX_TURNS:
        raise StateError("conversation_too_long")

    session.add(RequestMessage(request_id=request.id, role="user", content=user_content))
    await session.flush()

    history = [{"role": m.role, "content": m.content} for m in request.messages] + [
        {"role": "user", "content": user_content}
    ]

    new_profile = await extract_profile(
        llm, history=history, current_profile=request.profile or empty_profile()
    )
    request.profile = new_profile
    request.title = derive_title(new_profile, fallback=request.title)
    miss = missing_fields(new_profile)
    ready = is_ready_for_jd(new_profile)

    reply_messages = [
        ChatMessage(role="system", content=REPLY_SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=(
                f"已知画像:\n{json.dumps(new_profile, ensure_ascii=False)}\n"
                f"缺项（按优先级）:\n{miss}\n"
                f"对话:\n" + "\n".join(f"[{m['role']}] {m['content']}" for m in history)
            ),
        ),
    ]
    assistant_text = await collect_full_text(
        llm, reply_messages, ChatOptions(temperature=0.5, max_tokens=800)
    )
    if not assistant_text.strip():
        assistant_text = "（系统提示：回复生成失败，请重试）"

    session.add(RequestMessage(request_id=request.id, role="assistant", content=assistant_text))
    await session.commit()
    await session.refresh(request)
    return MessageTurn(
        user_content=user_content,
        assistant_content=assistant_text,
        profile=new_profile,
        missing=miss,
        ready=ready,
    )


async def generate_and_save_jd(
    session: AsyncSession, *, llm: LLMProvider, request: RecruitmentRequest
) -> JDDraft:
    validate_transition_to_pending_review(status=request.status, profile=request.profile)

    md = await generate_jd(llm, request.profile)
    if not md.strip():
        raise StateError("jd_generation_empty")

    draft = JDDraft(request_id=request.id, content_md=md)
    session.add(draft)
    request.status = "pending_review"
    await session.commit()
    await session.refresh(request)
    return draft


async def patch_request(
    session: AsyncSession,
    *,
    request: RecruitmentRequest,
    edited_content_md: str | None,
    action: str | None,
) -> RecruitmentRequest:
    from datetime import datetime, timezone

    if edited_content_md is not None:
        if request.jd_draft is None:
            raise StateError("no_jd_to_edit")
        request.jd_draft.edited_content_md = edited_content_md

    if action == "approve":
        validate_transition_to_approved(status=request.status)
        request.status = "approved"
        if request.jd_draft is not None:
            request.jd_draft.approved_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(request)
    return request
```

- [ ] **Step 4: 运行 service 单测通过**

Run: `cd backend && uv run pytest tests/unit/test_recruitment_service.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/free_hr/recruitment/service.py backend/tests/unit/test_recruitment_service.py
git commit -m "feat(recruitment): service orchestration and state machine"
```

---

## Task 6: API 路由

**Files:**
- Create: `backend/src/free_hr/api/routes/recruitment.py`
- Modify: `backend/src/free_hr/api/main.py`

- [ ] **Step 1: 写路由文件**

```python
# backend/src/free_hr/api/routes/recruitment.py
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...llm_gateway import LLMProvider
from ...recruitment import service as svc
from ...recruitment.profile import is_ready_for_jd, missing_fields
from ...recruitment.schemas import (
    JDRead,
    MessageRead,
    PatchRequestBody,
    PostMessageRequest,
    PostMessageResponse,
    RequestListItem,
    RequestRead,
)
from ..deps import get_db_dep, get_llm_dep


router = APIRouter(prefix="/api/recruitment", tags=["recruitment"])


def _to_request_read(req) -> RequestRead:
    jd = None
    if req.jd_draft is not None:
        jd = JDRead(
            content_md=req.jd_draft.content_md,
            edited_content_md=req.jd_draft.edited_content_md,
            generated_at=req.jd_draft.generated_at,
            approved_at=req.jd_draft.approved_at,
        )
    return RequestRead(
        id=req.id,
        title=req.title,
        status=req.status,
        profile=req.profile,
        missing_fields=missing_fields(req.profile),
        ready_for_jd=is_ready_for_jd(req.profile),
        messages=[
            MessageRead(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
            for m in req.messages
        ],
        jd=jd,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.post("/requests", response_model=RequestRead)
async def create_request(session: AsyncSession = Depends(get_db_dep)) -> RequestRead:
    req = await svc.create_request(session)
    await session.refresh(req, attribute_names=["messages", "jd_draft"])
    return _to_request_read(req)


@router.get("/requests", response_model=list[RequestListItem])
async def list_requests(session: AsyncSession = Depends(get_db_dep)) -> list[RequestListItem]:
    reqs = await svc.list_requests(session)
    return [
        RequestListItem(id=r.id, title=r.title, status=r.status, updated_at=r.updated_at)
        for r in reqs
    ]


@router.get("/requests/{request_id}", response_model=RequestRead)
async def get_request(request_id: UUID, session: AsyncSession = Depends(get_db_dep)) -> RequestRead:
    req = await svc.get_request(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="not found")
    return _to_request_read(req)


@router.post("/requests/{request_id}/messages", response_model=PostMessageResponse)
async def post_message(
    request_id: UUID,
    body: PostMessageRequest,
    session: AsyncSession = Depends(get_db_dep),
    llm: LLMProvider = Depends(get_llm_dep),
) -> PostMessageResponse:
    req = await svc.get_request(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        turn = await svc.append_user_message(session, llm=llm, request=req, user_content=body.content.strip())
    except svc.StateError as e:
        code = str(e).split(":", 1)[0]
        if code == "conversation_too_long":
            raise HTTPException(status_code=409, detail={"error": code})
        raise HTTPException(status_code=400, detail={"error": code})

    # Re-fetch to get the assistant message row with id/created_at
    await session.refresh(req, attribute_names=["messages"])
    assistant_msg = req.messages[-1]
    return PostMessageResponse(
        assistant_message=MessageRead(
            id=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            created_at=assistant_msg.created_at,
        ),
        profile=turn.profile,
        missing_fields=turn.missing,
        ready_for_jd=turn.ready,
    )


@router.post("/requests/{request_id}/jd", response_model=RequestRead)
async def post_jd(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_dep),
    llm: LLMProvider = Depends(get_llm_dep),
) -> RequestRead:
    req = await svc.get_request(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        await svc.generate_and_save_jd(session, llm=llm, request=req)
    except svc.StateError as e:
        msg = str(e)
        if msg.startswith("missing_fields"):
            fields = msg.split(":", 1)[1].split(",") if ":" in msg else []
            raise HTTPException(status_code=400, detail={"error": "missing_fields", "fields": fields})
        if msg == "invalid_state":
            raise HTTPException(status_code=409, detail={"error": "invalid_state"})
        raise HTTPException(status_code=500, detail={"error": msg})

    await session.refresh(req, attribute_names=["messages", "jd_draft"])
    return _to_request_read(req)


@router.patch("/requests/{request_id}", response_model=RequestRead)
async def patch_request(
    request_id: UUID,
    body: PatchRequestBody,
    session: AsyncSession = Depends(get_db_dep),
) -> RequestRead:
    req = await svc.get_request(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        await svc.patch_request(
            session,
            request=req,
            edited_content_md=body.edited_content_md,
            action=body.action,
        )
    except svc.StateError as e:
        code = str(e)
        raise HTTPException(status_code=409, detail={"error": code})

    await session.refresh(req, attribute_names=["messages", "jd_draft"])
    return _to_request_read(req)
```

- [ ] **Step 2: 修改 `main.py` 挂载路由**

```python
# backend/src/free_hr/api/main.py (修改)
from ..config import get_settings
from .routes import chat as chat_routes
from .routes import knowledge as knowledge_routes
from .routes import recruitment as recruitment_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Free-HR API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_routes.router)
    app.include_router(knowledge_routes.router)
    app.include_router(recruitment_routes.router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

- [ ] **Step 3: 验证 app 可启动**

Run: `cd backend && uv run python -c "from free_hr.api.main import app; print([r.path for r in app.routes])"`
Expected: 输出包含 `/api/recruitment/requests`、`/api/recruitment/requests/{request_id}/messages` 等。

- [ ] **Step 4: Commit**

```bash
git add backend/src/free_hr/api/routes/recruitment.py backend/src/free_hr/api/main.py
git commit -m "feat(recruitment): FastAPI routes"
```

---

## Task 7: API 集成测试（mock LLM + in-memory DB）

由于现有集成测试用 `_fake_db: yield None` 跳过 DB（RAG 侧 repo 也被 monkeypatch 掉），招聘模块**必须走真 ORM**（DB 是核心链路）。方案：用 **SQLite + aiosqlite** 内存库 + 建表（招聘模块的表不依赖 pgvector，且 JSONB 在 SQLite 上退化为 JSON，CheckConstraint 兼容）。

**Files:**
- Create: `backend/tests/integration/test_recruitment_api.py`

- [ ] **Step 1: 写集成测试**

```python
# backend/tests/integration/test_recruitment_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from free_hr.api import deps as api_deps
from free_hr.api.main import app
from free_hr.db import Base
from free_hr.llm_gateway.fake import FakeLLMProvider

# Recruitment tables only (avoid pgvector-dependent models)
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
    # JSONB / PG_UUID types: SQLAlchemy maps JSONB→JSON and PG_UUID→CHAR(32) in SQLite fallback
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        # Create only the three recruitment tables
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

    # 1. Create request
    r = await c.post("/api/recruitment/requests")
    assert r.status_code == 200, r.text
    req = r.json()
    req_id = req["id"]
    assert req["status"] == "drafting"
    assert req["ready_for_jd"] is False

    # 2. Post a message — FakeLLM returns the full profile JSON for BOTH the extract
    #    and the reply call (same script). The reply text will still be that JSON,
    #    which is fine for test purposes.
    r = await c.post(f"/api/recruitment/requests/{req_id}/messages", json={"content": "招聘后端工程师"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ready_for_jd"] is True
    assert body["profile"]["position"]["title"] == "后端工程师"
    assert body["missing_fields"] == [] or "position.title" not in body["missing_fields"]

    # 3. Generate JD — LLM returns a Markdown string for this call
    llm_holder["llm"] = FakeLLMProvider(script=["# 后端工程师\n\n## 岗位职责\n- 写API\n\n## 任职要求\n- Python"])
    app.dependency_overrides[api_deps.get_llm_dep] = lambda: llm_holder["llm"]
    r = await c.post(f"/api/recruitment/requests/{req_id}/jd")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending_review"
    assert body["jd"]["content_md"].startswith("# 后端工程师")

    # 4. HR edits the JD
    r = await c.patch(
        f"/api/recruitment/requests/{req_id}",
        json={"edited_content_md": "# 后端（编辑版）"},
    )
    assert r.status_code == 200
    assert r.json()["jd"]["edited_content_md"] == "# 后端（编辑版）"

    # 5. HR approves
    r = await c.patch(f"/api/recruitment/requests/{req_id}", json={"action": "approve"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # 6. Approving again → 409
    r = await c.patch(f"/api/recruitment/requests/{req_id}", json={"action": "approve"})
    assert r.status_code == 409


async def test_generate_jd_before_ready_returns_400(client):
    c, _ = client

    # Create a fresh request with empty script LLM so profile stays empty
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
```

- [ ] **Step 2: 装 aiosqlite 依赖**

Run: `cd backend && uv add --dev aiosqlite`
Expected: `aiosqlite` 写入 `pyproject.toml` 的 dev deps。

- [ ] **Step 3: 运行集成测试**

Run: `cd backend && uv run pytest tests/integration/test_recruitment_api.py -v`
Expected: 4 passed.

如果 SQLite 对 `PG_UUID(as_uuid=True)` / `JSONB` 报错，fallback 方案：在测试里直接用真 Postgres 连接（`conftest.py` 已有 `POSTGRES_URL`），或在 `models.py` 里让 UUID 列使用 `sa.Uuid(as_uuid=True)`（SQLAlchemy 2.0 的跨方言 UUID 类型）并把 JSONB 改为 `sa.JSON` 的跨方言变体。先尝试 SQLite；失败再调整。

- [ ] **Step 4: 运行全量测试确保没有回归**

Run: `cd backend && uv run pytest tests/unit/ tests/integration/test_api_endpoints.py tests/integration/test_recruitment_api.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/integration/test_recruitment_api.py backend/pyproject.toml backend/uv.lock
git commit -m "test(recruitment): end-to-end API integration test"
```

---

## Task 8: 前端 API 客户端

在写前端代码前，**必读**：
- `frontend/AGENTS.md` —— "This is NOT the Next.js you know"
- `frontend/node_modules/next/dist/docs/` 下相关章节（App Router、client/server components、fetch）

**Files:**
- Create: `frontend/lib/recruitment.ts`

- [ ] **Step 1: 创建 API 客户端**

```typescript
// frontend/lib/recruitment.ts
import { getApiBase } from "./settings";

function API_BASE() {
  return getApiBase();
}

export type Status = "drafting" | "pending_review" | "approved";

export interface Profile {
  position: {
    title: string | null;
    department: string | null;
    report_to: string | null;
    headcount: number | null;
    location: string | null;
    start_date: string | null;
  };
  responsibilities: string[];
  hard_requirements: {
    education: string | null;
    years: string | null;
    skills: string[];
    industry: string | null;
  };
  soft_preferences: {
    bonus_points: string[];
    culture_fit: string | null;
    team_style: string | null;
  };
  compensation: {
    salary_range: string | null;
    level: string | null;
    employment_type: string | null;
  };
}

export interface MessageRead {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface JDRead {
  content_md: string;
  edited_content_md: string | null;
  generated_at: string;
  approved_at: string | null;
}

export interface RequestRead {
  id: string;
  title: string;
  status: Status;
  profile: Profile;
  missing_fields: string[];
  ready_for_jd: boolean;
  messages: MessageRead[];
  jd: JDRead | null;
  created_at: string;
  updated_at: string;
}

export interface RequestListItem {
  id: string;
  title: string;
  status: Status;
  updated_at: string;
}

export interface PostMessageResponse {
  assistant_message: MessageRead;
  profile: Profile;
  missing_fields: string[];
  ready_for_jd: boolean;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  return (await res.json()) as T;
}

export async function createRequest(): Promise<RequestRead> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests`, { method: "POST" });
  return json<RequestRead>(res);
}

export async function listRequests(): Promise<RequestListItem[]> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests`);
  return json<RequestListItem[]>(res);
}

export async function getRequest(id: string): Promise<RequestRead> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests/${id}`);
  return json<RequestRead>(res);
}

export async function postMessage(id: string, content: string): Promise<PostMessageResponse> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests/${id}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  return json<PostMessageResponse>(res);
}

export async function generateJD(id: string): Promise<RequestRead> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests/${id}/jd`, { method: "POST" });
  return json<RequestRead>(res);
}

export async function patchRequest(
  id: string,
  body: { edited_content_md?: string; action?: "approve" }
): Promise<RequestRead> {
  const res = await fetch(`${API_BASE()}/api/recruitment/requests/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json<RequestRead>(res);
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: 无 TS 错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/recruitment.ts
git commit -m "feat(recruitment): frontend API client"
```

---

## Task 9: 列表页 `/recruitment`

**Files:**
- Create: `frontend/app/recruitment/page.tsx`

- [ ] **Step 1: 写列表页**

```tsx
// frontend/app/recruitment/page.tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createRequest, listRequests, RequestListItem, Status } from "@/lib/recruitment";

const STATUS_LABEL: Record<Status, string> = {
  drafting: "对话中",
  pending_review: "待审核",
  approved: "已通过",
};

const STATUS_COLOR: Record<Status, string> = {
  drafting: "bg-gray-200 text-gray-800",
  pending_review: "bg-orange-200 text-orange-900",
  approved: "bg-green-200 text-green-900",
};

export default function RecruitmentListPage() {
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    listRequests()
      .then(setItems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function onCreate() {
    try {
      const req = await createRequest();
      router.push(`/recruitment/${req.id}`);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <main className="max-w-4xl mx-auto p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold">招聘需求</h1>
        <button
          onClick={onCreate}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          ＋ 新建招聘需求
        </button>
      </div>
      {error && <div className="text-red-600 mb-4">加载失败：{error}</div>}
      {loading ? (
        <div>加载中…</div>
      ) : items.length === 0 ? (
        <div className="text-gray-500">还没有招聘需求，点右上角新建一条。</div>
      ) : (
        <ul className="divide-y border rounded">
          {items.map((it) => (
            <li key={it.id}>
              <Link href={`/recruitment/${it.id}`} className="block p-4 hover:bg-gray-50 flex justify-between items-center">
                <div>
                  <div className="font-medium">{it.title}</div>
                  <div className="text-sm text-gray-500">
                    更新于 {new Date(it.updated_at).toLocaleString()}
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded ${STATUS_COLOR[it.status]}`}>
                  {STATUS_LABEL[it.status]}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: 无错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/app/recruitment/page.tsx
git commit -m "feat(recruitment): list page"
```

---

## Task 10: 详情页 `/recruitment/[id]`

**Files:**
- Create: `frontend/components/ProfileCard.tsx`
- Create: `frontend/components/JDPanel.tsx`
- Create: `frontend/components/RecruitmentChat.tsx`
- Create: `frontend/app/recruitment/[id]/page.tsx`

- [ ] **Step 1: `ProfileCard.tsx`**

```tsx
// frontend/components/ProfileCard.tsx
"use client";

import { Profile } from "@/lib/recruitment";

type FieldRow = { label: string; value: string | null };

function group(title: string, rows: FieldRow[]) {
  return (
    <div className="mb-4">
      <div className="text-xs font-semibold text-gray-500 mb-1">{title}</div>
      <div className="space-y-1 text-sm">
        {rows.map((r) => (
          <div key={r.label} className="flex">
            <div className="w-24 text-gray-500">{r.label}</div>
            <div className={r.value ? "text-gray-900" : "text-gray-400 italic"}>
              {r.value ?? "待补充"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function listOrPlaceholder(list: string[]): string | null {
  return list.length > 0 ? list.join("、") : null;
}

export function ProfileCard({ profile }: { profile: Profile }) {
  return (
    <div className="p-4 border-b">
      <h3 className="font-semibold mb-3">候选人画像</h3>
      {group("岗位基础", [
        { label: "职位名称", value: profile.position.title },
        { label: "所属部门", value: profile.position.department },
        { label: "汇报对象", value: profile.position.report_to },
        { label: "编制", value: profile.position.headcount?.toString() ?? null },
        { label: "工作地点", value: profile.position.location },
        { label: "到岗时间", value: profile.position.start_date },
      ])}
      {group("岗位职责", [
        { label: "核心职责", value: listOrPlaceholder(profile.responsibilities) },
      ])}
      {group("硬性要求", [
        { label: "学历", value: profile.hard_requirements.education },
        { label: "工作年限", value: profile.hard_requirements.years },
        { label: "必备技能", value: listOrPlaceholder(profile.hard_requirements.skills) },
        { label: "行业背景", value: profile.hard_requirements.industry },
      ])}
      {group("软性偏好", [
        { label: "加分项", value: listOrPlaceholder(profile.soft_preferences.bonus_points) },
        { label: "文化匹配", value: profile.soft_preferences.culture_fit },
        { label: "团队风格", value: profile.soft_preferences.team_style },
      ])}
      {group("薪资与汇报", [
        { label: "薪资范围", value: profile.compensation.salary_range },
        { label: "级别", value: profile.compensation.level },
        { label: "雇佣形式", value: profile.compensation.employment_type },
      ])}
    </div>
  );
}
```

- [ ] **Step 2: `JDPanel.tsx`**

```tsx
// frontend/components/JDPanel.tsx
"use client";

import { useState } from "react";
import { JDRead, patchRequest, RequestRead, Status } from "@/lib/recruitment";

export function JDPanel({
  request,
  onUpdated,
}: {
  request: RequestRead;
  onUpdated: (r: RequestRead) => void;
}) {
  const jd: JDRead | null = request.jd;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  if (jd === null) {
    return (
      <div className="p-4 text-gray-400 italic">
        完成对话后生成 JD
      </div>
    );
  }

  const current = jd.edited_content_md ?? jd.content_md;
  const status: Status = request.status;

  async function onSaveEdit() {
    try {
      const r = await patchRequest(request.id, { edited_content_md: draft });
      onUpdated(r);
      setEditing(false);
    } catch (e) {
      setError(String(e));
    }
  }

  async function onApprove() {
    try {
      const r = await patchRequest(request.id, { action: "approve" });
      onUpdated(r);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">JD 草稿</h3>
        <div className="space-x-2">
          {!editing && status === "pending_review" && (
            <>
              <button
                onClick={() => {
                  setDraft(current);
                  setEditing(true);
                }}
                className="text-sm px-3 py-1 border rounded"
              >
                编辑
              </button>
              <button
                onClick={onApprove}
                className="text-sm px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
              >
                通过
              </button>
            </>
          )}
          {status === "approved" && (
            <span className="text-sm text-green-700">已通过</span>
          )}
        </div>
      </div>
      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}
      {editing ? (
        <>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="w-full h-96 border rounded p-2 font-mono text-sm"
          />
          <div className="mt-2 space-x-2">
            <button onClick={onSaveEdit} className="px-3 py-1 bg-blue-600 text-white rounded">
              保存
            </button>
            <button onClick={() => setEditing(false)} className="px-3 py-1 border rounded">
              取消
            </button>
          </div>
        </>
      ) : (
        <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-3 rounded border">{current}</pre>
      )}
    </div>
  );
}
```

- [ ] **Step 3: `RecruitmentChat.tsx`**

```tsx
// frontend/components/RecruitmentChat.tsx
"use client";

import { useState } from "react";
import { generateJD, MessageRead, postMessage, RequestRead } from "@/lib/recruitment";

export function RecruitmentChat({
  request,
  onUpdated,
}: {
  request: RequestRead;
  onUpdated: (r: RequestRead) => void;
}) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<MessageRead[]>(request.messages);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSend() {
    if (!input.trim() || sending) return;
    const content = input.trim();
    const userMsg: MessageRead = {
      id: `local-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((ms) => [...ms, userMsg]);
    setInput("");
    setSending(true);
    setError(null);
    try {
      const resp = await postMessage(request.id, content);
      setMessages((ms) => [...ms, resp.assistant_message]);
      // Refresh parent for profile/ready_for_jd/status
      onUpdated({
        ...request,
        profile: resp.profile,
        missing_fields: resp.missing_fields,
        ready_for_jd: resp.ready_for_jd,
        messages: [...request.messages, userMsg, resp.assistant_message],
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setSending(false);
    }
  }

  async function onGenerate() {
    setSending(true);
    setError(null);
    try {
      const r = await generateJD(request.id);
      onUpdated(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setSending(false);
    }
  }

  const canGenerate = request.ready_for_jd && request.status === "drafting";
  const generateTooltip = canGenerate
    ? ""
    : request.status !== "drafting"
    ? "已生成 JD"
    : `还需补充：${request.missing_fields.join("、")}`;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-gray-500 text-sm">
            你好，请描述你要招聘的岗位。例如"我要招一个后端工程师，技术部，Python 方向，3-5 年经验，25-40k"。
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`max-w-[80%] p-3 rounded ${
              m.role === "user" ? "bg-blue-100 ml-auto" : "bg-gray-100"
            }`}
          >
            <div className="whitespace-pre-wrap text-sm">{m.content}</div>
          </div>
        ))}
        {sending && <div className="text-gray-400 text-sm">生成中…</div>}
        {error && <div className="text-red-600 text-sm">{error}</div>}
      </div>
      <div className="border-t p-3 space-y-2">
        <div className="flex space-x-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
            placeholder="描述你要招聘的岗位…（Enter 发送，Shift+Enter 换行）"
            className="flex-1 border rounded p-2 text-sm resize-none h-20"
            disabled={sending || request.status === "approved"}
          />
          <button
            onClick={onSend}
            disabled={sending || !input.trim() || request.status === "approved"}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:bg-gray-400"
          >
            发送
          </button>
        </div>
        <button
          onClick={onGenerate}
          disabled={!canGenerate || sending}
          title={generateTooltip}
          className="w-full py-2 bg-green-600 text-white rounded disabled:bg-gray-300 disabled:text-gray-500"
        >
          生成 JD
          {!canGenerate && request.status === "drafting" && (
            <span className="ml-2 text-xs">（{generateTooltip}）</span>
          )}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 详情页 `page.tsx`**

```tsx
// frontend/app/recruitment/[id]/page.tsx
"use client";

import { useEffect, useState, use } from "react";
import { getRequest, RequestRead } from "@/lib/recruitment";
import { ProfileCard } from "@/components/ProfileCard";
import { JDPanel } from "@/components/JDPanel";
import { RecruitmentChat } from "@/components/RecruitmentChat";

export default function RecruitmentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  // Next.js 15+ dynamic params are async — unwrap with React.use()
  const { id } = use(params);
  const [req, setReq] = useState<RequestRead | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRequest(id).then(setReq).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <main className="p-8 text-red-600">加载失败：{error}</main>;
  if (!req) return <main className="p-8">加载中…</main>;

  return (
    <main className="h-screen flex flex-col">
      <header className="border-b px-6 py-3 flex items-center justify-between">
        <div>
          <a href="/recruitment" className="text-sm text-blue-600">← 返回列表</a>
          <h1 className="text-lg font-semibold">{req.title}</h1>
        </div>
        <span className="text-xs px-2 py-1 rounded bg-gray-200">{req.status}</span>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-3/5 border-r">
          <RecruitmentChat request={req} onUpdated={setReq} />
        </div>
        <div className="w-2/5 overflow-y-auto">
          <ProfileCard profile={req.profile} />
          <JDPanel request={req} onUpdated={setReq} />
        </div>
      </div>
    </main>
  );
}
```

注：`params: Promise<...>` + `React.use(params)` 是 Next.js 15 的动态 params API。**写代码前先确认项目的 Next 版本**：
Run: `cd frontend && cat package.json | grep '"next"'`
若是 14.x，改回 `params: { id: string }` 同步形式。

- [ ] **Step 5: 类型检查与开发服务器自测**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: 无错误。

（可选，若后端已跑）Run: `cd frontend && pnpm dev` 然后在浏览器访问 `/recruitment`，走完"新建 → 发消息 → 生成 JD → 编辑 → 通过"；如有报错修复后再 commit。

- [ ] **Step 6: Commit**

```bash
git add frontend/components/ProfileCard.tsx frontend/components/JDPanel.tsx frontend/components/RecruitmentChat.tsx frontend/app/recruitment/[id]/page.tsx
git commit -m "feat(recruitment): detail page with chat, profile card, JD panel"
```

---

## Task 11: 导航入口 + README

- [ ] **Step 1: 查看当前导航实现**

Run: `cd frontend && cat components/Sidebar.tsx` 与 `cat app/layout.tsx`
读完决定：在 Sidebar 加链接，还是在 layout 顶部加链接。

- [ ] **Step 2: 添加入口（示例：Sidebar.tsx）**

在 Sidebar 的合适位置添加：

```tsx
import Link from "next/link";

// 在菜单项列表中增加
<Link href="/recruitment" className="block px-3 py-2 rounded hover:bg-gray-100">
  招聘协作
</Link>
```

若 Sidebar 是法律问答专用（用来选法律 / 切换会话），则改为在 `app/layout.tsx` 顶栏加一条导航：

```tsx
<nav className="border-b px-6 py-2 flex space-x-4 text-sm">
  <Link href="/" className="hover:underline">法律问答</Link>
  <Link href="/recruitment" className="hover:underline">招聘协作</Link>
</nav>
```

根据实际结构任选一种实现，保持与既有视觉风格一致。

- [ ] **Step 3: 更新 README**

修改 `README.md` 的 "API 概览（MVP）" 表格，追加：

```markdown
| POST | `/api/recruitment/requests` | 创建招聘需求单 |
| GET | `/api/recruitment/requests` | 列出招聘需求 |
| GET | `/api/recruitment/requests/{id}` | 需求单详情（对话 + 画像 + JD） |
| POST | `/api/recruitment/requests/{id}/messages` | 发送对话消息，返回画像更新 |
| POST | `/api/recruitment/requests/{id}/jd` | 基于画像生成 JD（需必填齐备） |
| PATCH | `/api/recruitment/requests/{id}` | HR 编辑 JD 或通过审核 |
```

并在 "当前 MVP 不包含" 节的上方新增一节：

```markdown
## 招聘需求协作（新模块）

`/recruitment` 页面：业务部门自助提交招聘需求，AI 多轮对话抽取画像，字段齐备后生成 JD，HR 审核通过。详见 [设计文档](docs/superpowers/specs/2026-04-18-recruitment-request-collab-design.md)。
```

- [ ] **Step 4: 最后跑一次全量测试**

Run: `cd backend && uv run pytest tests/unit/ tests/integration/test_api_endpoints.py tests/integration/test_recruitment_api.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/ README.md
git commit -m "feat(recruitment): navigation entry and README updates"
```

---

## Self-Review 备忘（已在撰写时校对）

- **Spec 覆盖**：
  - 架构（第 4 节）→ Tasks 0/1/6
  - 数据模型（第 5 节）→ Task 1
  - API 设计（第 6 节）→ Task 6（含错误码 400/409/404）
  - 对话编排（第 7 节）→ Tasks 3/5（抽取 + 合并 + 缺项 + 回复 + 20 轮硬限）
  - 两次 LLM 调用策略 → 分别在 Task 3（抽取）和 Task 5（回复）中落地
  - JD 一次性生成（第 7 节末）→ Task 4
  - 前端交互（第 8 节）→ Tasks 8–11
  - 错误处理（第 9 节）→ 路由中按表对应码返回；抽取失败回退在 extractor；对话过长在 service
  - 测试计划（第 10 节）→ Tasks 2/3/4/5/7 单测 + 集成全覆盖
  - 迁移（第 11 节）→ Task 1

- **类型/签名一致性**：`Profile`、`missing_fields`、`is_ready_for_jd` 在后端/前端命名一致；`PostMessageResponse.ready_for_jd` 与前端 `RequestRead.ready_for_jd` 同名。

- **无占位符**：每个代码步骤均有完整代码块；`0003_recruitment.py` 的 `down_revision` 需要 Step 0 填真实值（已标注 `<PUT_0002_REVISION_ID_HERE>`，不是 TODO 而是必须替换的运行时值）。

- **Next.js 版本假设**：Task 10 明确提醒先 check `package.json` 的 next 版本，避免 params API 不匹配。
