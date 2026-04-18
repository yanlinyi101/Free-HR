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
