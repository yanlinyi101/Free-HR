import os
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://free_hr:free_hr@localhost:5432/free_hr_test")
os.environ.setdefault("JWT_SECRET", "test-secret")
