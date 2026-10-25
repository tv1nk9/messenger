from app.bootstrap.create_first_admin import _read_bootstrap_env


def test_read_bootstrap_env_missing_required(monkeypatch):
    monkeypatch.delenv("FIRST_ADMIN_EMAIL", raising=False)
    monkeypatch.setenv("FIRST_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("FIRST_ADMIN_NAME", "Admin")
    monkeypatch.setenv("FIRST_ADMIN_SURNAME", "User")

    _, missing = _read_bootstrap_env()

    assert missing == ["FIRST_ADMIN_EMAIL"]


def test_read_bootstrap_env_collects_payload(monkeypatch):
    monkeypatch.setenv("FIRST_ADMIN_EMAIL", " admin@mail.com ")
    monkeypatch.setenv("FIRST_ADMIN_PASSWORD", " secret ")
    monkeypatch.setenv("FIRST_ADMIN_NAME", " Admin ")
    monkeypatch.setenv("FIRST_ADMIN_SURNAME", " User ")
    monkeypatch.setenv("FIRST_ADMIN_PATRONYMIC", " Test ")

    payload, missing = _read_bootstrap_env()

    assert missing == []
    assert payload["FIRST_ADMIN_EMAIL"] == "admin@mail.com"
    assert payload["FIRST_ADMIN_PASSWORD"] == "secret"
    assert payload["FIRST_ADMIN_NAME"] == "Admin"
    assert payload["FIRST_ADMIN_SURNAME"] == "User"
    assert payload["FIRST_ADMIN_PATRONYMIC"] == "Test"
