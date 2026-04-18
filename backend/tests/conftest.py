import os

os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://free_hr:free_hr@localhost:5432/free_hr_test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from free_hr.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
