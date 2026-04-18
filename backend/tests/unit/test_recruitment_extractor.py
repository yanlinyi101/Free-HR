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
    assert result == current


async def test_extract_accepts_json_with_code_fence():
    llm = FakeLLMProvider(script=[
        '```json\n{"position": {"title": "PM"}, "responsibilities": [], '
        '"hard_requirements": {"skills": []}, "soft_preferences": {}, "compensation": {}}\n```'
    ])
    result = await extract_profile(llm, history=[{"role": "user", "content": "x"}], current_profile=empty_profile())
    assert result["position"]["title"] == "PM"
