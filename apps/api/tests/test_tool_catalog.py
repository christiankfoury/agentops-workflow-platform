from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.tool import ToolCredential, ToolVersion
from src.schemas.tool import CredentialCreate, ToolContract, ToolCreate, ToolPublish
from src.services import tool_catalog as catalog
from src.services.identity import Principal
from src.services.tenancy import bind_tenant
from tests.test_identity import auth_config as auth_config
from tests.test_identity import signing_key as signing_key
from tests.test_permissions_audit import prepare
from tests.test_tenant_isolation import tenant_client as tenant_client
from tests.test_tenant_isolation import tenants as tenants
from tests.test_tool_effects import SCHEMA
from tests.test_workflow_transactions_postgres import database as database

CONTRACT = {"adapter": "http", "input_schema": SCHEMA, "output_schema": SCHEMA}


@pytest.mark.parametrize("role", ["viewer", "operator", "reviewer", "admin"])
def test_tool_management_requires_admin(tenant_client, database, tenants, role):
    prepare(database, tenants[0], role)
    response = tenant_client.post("/tools", json={"name": "Tool", "contract": CONTRACT})
    assert response.status_code == (201 if role == "admin" else 403), response.text
    response = tenant_client.post("/tools/credentials", json={"name": "Key", "source_alias": "key"})
    assert response.status_code == (201 if role == "admin" else 403), response.text
    assert tenant_client.get("/tools").status_code == 200


def test_cross_tenant_credential_and_version_access_fail_closed(database, tenants):
    first, second = tenants
    actor = prepare(database, first, "admin")
    with Session(database) as db:
        bind_tenant(db, first["org"])
        db.info["principal"] = Principal("admin", actor, first["org"])
        key = catalog.create_credential(db, CredentialCreate(name="Private", source_alias="key"))
        version = catalog.create(
            db,
            ToolCreate(
                name="Private tool", contract=ToolContract(**CONTRACT, credential_ref=key.id)
            ),
        )
        key_id, version_id = key.id, version.id
    actor = prepare(database, second, "admin")
    with Session(database) as db:
        bind_tenant(db, second["org"])
        db.info["principal"] = Principal("admin", actor, second["org"])
        for model, identity in [(ToolCredential, key_id), (ToolVersion, version_id)]:
            with pytest.raises(HTTPException) as error:
                catalog.get(db, model, identity)
            assert error.value.status_code == 404
        with pytest.raises(HTTPException) as error:
            catalog.create(
                db,
                ToolCreate(
                    name="Wrong key", contract=ToolContract(**CONTRACT, credential_ref=key_id)
                ),
            )
        assert error.value.status_code == 404
        db.rollback()


def test_rejected_tool_configuration_does_not_echo_credentials(tenant_client, database, tenants):
    prepare(database, tenants[0], "admin")
    for options in [
        {"Authorization": "private-test-key"},
        {"url": "https://user:private-test-key@example.com"},
    ]:
        response = tenant_client.post(
            "/tools", json={"name": "Unsafe", "contract": {**CONTRACT, "options": options}}
        )
        assert response.status_code == 422
        assert "private-test-key" not in response.text


@pytest.mark.parametrize(
    "change",
    [
        {"input_schema": {"type": "array"}},
        {"output_schema": {"type": "string"}},
        {"timeout_seconds": 0},
        {"retry": {"max_attempts": 11}},
        {"options": {"nested": {"authorization": "secret"}}},
        {"options": {"large": "x" * 130_000}},
    ],
)
def test_malformed_contracts_and_inline_credential_fields_rejected(change):
    with pytest.raises(ValidationError):
        ToolContract.model_validate({**deepcopy(CONTRACT), **change})


def test_concurrent_publication_conflicts_and_pins_previous_contract(database):
    with Session(database) as db:
        first = catalog.create(db, ToolCreate(name="Tool", contract=ToolContract(**CONTRACT)))
        identity, first_id = first.definition_id, first.id
    barrier = Barrier(2)

    def publish():
        with Session(database) as db:
            barrier.wait(timeout=10)
            try:
                return catalog.publish(
                    db,
                    identity,
                    ToolPublish(
                        expected_version=1, contract=ToolContract(**CONTRACT, timeout_seconds=5)
                    ),
                ).number
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: publish(), range(2))) == [2, 409]
    with Session(database) as db:
        first = db.get(ToolVersion, first_id)
        assert first.contract["timeout_seconds"] == 30
        assert len(db.scalars(select(ToolVersion)).all()) == 2
        first.contract = {**first.contract, "timeout_seconds": 7}
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
