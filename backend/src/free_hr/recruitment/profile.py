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
