from free_hr.config import Settings


def test_settings_defaults_are_loaded():
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.jwt_algorithm == "HS256"
    assert s.embedding_dim == 1024
    assert s.llm_provider == "deepseek"


def test_settings_override_via_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "custom-secret")
    monkeypatch.setenv("LLM_MODEL", "deepseek-reasoner")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.jwt_secret == "custom-secret"
    assert s.llm_model == "deepseek-reasoner"
