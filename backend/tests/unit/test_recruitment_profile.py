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
    new = empty_profile()
    merged = merge_profile(old, new)
    assert merged["position"]["title"] == "后端"


def test_merge_does_not_clear_filled_list_with_empty():
    old = empty_profile()
    old["responsibilities"] = ["写代码"]
    new = empty_profile()
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
    assert is_ready_for_jd(p) is False
    p["compensation"]["salary_range"] = "25-40k"
    assert is_ready_for_jd(p) is True
