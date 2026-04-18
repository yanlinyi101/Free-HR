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
    with pytest.raises(StateError, match="missing_fields"):
        validate_transition_to_pending_review(status="drafting", profile=p)
    p["position"]["title"] = "T"
    p["position"]["department"] = "D"
    p["responsibilities"] = ["R"]
    p["hard_requirements"]["skills"] = ["S"]
    p["compensation"]["salary_range"] = "X"
    with pytest.raises(StateError, match="invalid_state"):
        validate_transition_to_pending_review(status="approved", profile=p)
    validate_transition_to_pending_review(status="drafting", profile=p)


def test_validate_transition_to_approved_requires_pending_review():
    with pytest.raises(StateError, match="invalid_state"):
        validate_transition_to_approved(status="drafting")
    with pytest.raises(StateError, match="invalid_state"):
        validate_transition_to_approved(status="approved")
    validate_transition_to_approved(status="pending_review")
