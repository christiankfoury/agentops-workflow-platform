import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.main import app
from src.production import validate_configuration
from src.worker import main as worker_main
from tests.test_workflow_transactions_postgres import database as database


def test_worker_rejects_unverified_production_before_claiming(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "identity_enabled", False)
    with pytest.raises(RuntimeError, match="verified identity"):
        worker_main()


def test_production_requires_https_identity_and_bounded_hosts(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "identity_enabled", True)
    monkeypatch.setattr(settings, "oidc_audience", "example")
    monkeypatch.setattr(settings, "oidc_issuer", "https://example.test")
    monkeypatch.setattr(settings, "oidc_jwks_url", "https://example.test/jwks")
    validate_configuration()
    monkeypatch.setattr(settings, "trusted_hosts", ["*"])
    with pytest.raises(RuntimeError, match="trusted hosts"):
        validate_configuration()
    monkeypatch.setattr(settings, "oidc_jwks_url", "http://example.test/jwks")
    with pytest.raises(RuntimeError, match="HTTPS"):
        validate_configuration()


def test_untrusted_host_rejected_and_database_outage_not_ready(monkeypatch):
    monkeypatch.setattr("src.main.check_db", lambda: False)
    with TestClient(app) as client:
        assert client.get("/health", headers={"host": "attacker.test"}).status_code == 400
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503


def test_secret_files_load_before_import_and_conflicts_fail_closed(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "container_entrypoint",
        Path(__file__).resolve().parents[1] / "container_entrypoint.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    secret = tmp_path / "database"
    secret.write_text("postgresql://synthetic-only\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL_FILE", str(secret))
    module.load_secrets()
    with pytest.raises(RuntimeError, match="either DATABASE_URL"):
        module.load_secrets()


def test_readiness_requires_current_worker_instance(database, tmp_path, monkeypatch):
    from src import container_health
    from src.services.worker_presence import beat

    monkeypatch.setattr(container_health, "engine", database)
    identity = tmp_path / "worker-identity"
    identity.write_text("same-container:new-process", encoding="utf-8")
    beat(database, "same-container:old-process", 2)
    assert not container_health.ready(identity)
    beat(database, "same-container:new-process", 2)
    assert container_health.ready(identity)
    beat(database, "same-container:new-process", 2, "draining")
    assert not container_health.ready(identity)
