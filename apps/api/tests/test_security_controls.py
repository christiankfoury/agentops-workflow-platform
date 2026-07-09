from fastapi.testclient import TestClient
from pydantic import SecretStr

from src.config import Settings, settings
from src.main import app
from src.security import reset_rate_limit_state


def test_settings_repr_masks_secret_values():
    configured = Settings(
        openai_api_key="sk-test-secret",
        api_key="local-api-secret",
        agentops_telemetry_api_key="platform-telemetry-secret",
    )

    rendered = repr(configured)

    assert "sk-test-secret" not in rendered
    assert "local-api-secret" not in rendered
    assert "platform-telemetry-secret" not in rendered
    assert "SecretStr" in rendered


def test_authenticated_routes_reject_missing_api_key(monkeypatch):
    monkeypatch.setattr(settings, "api_auth_enabled", True)
    monkeypatch.setattr(settings, "api_key", SecretStr("local-api-secret"))
    client = TestClient(app)

    response = client.get("/uploaded-inputs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_role_check_rejects_viewer_for_operator_upload(monkeypatch):
    monkeypatch.setattr(settings, "api_auth_enabled", True)
    monkeypatch.setattr(settings, "api_key", SecretStr("local-api-secret"))
    client = TestClient(app)

    response = client.post(
        "/uploaded-inputs",
        headers={
            "x-agentops-api-key": "local-api-secret",
            "x-agentops-role": "viewer",
        },
        json={
            "title": "Q1 Sales Report",
            "input_type": "sales_report",
            "raw_text": "Revenue increased 12%.",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient API role"


def test_rate_limit_returns_safe_error_after_threshold(monkeypatch):
    reset_rate_limit_state()
    monkeypatch.setattr(settings, "api_rate_limit_per_minute", 2)
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    limited = client.get("/health")

    assert limited.status_code == 429
    assert limited.json()["detail"] == "Rate limit exceeded"
    reset_rate_limit_state()
