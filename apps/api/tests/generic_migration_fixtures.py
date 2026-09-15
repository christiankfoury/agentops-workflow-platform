"""Seed pre-deadline execution rows without using newer execution ORM columns."""

import json
import uuid

from sqlalchemy import text

from src.schemas.workflow_definition import DefinitionCreate
from src.services import workflow_definitions
from src.services.tenancy import tenant_id
from tests.test_graph_interpreter import branching_graph


def pre_deadline_execution(db):
    item = workflow_definitions.create_definition(
        db,
        DefinitionCreate(
            name="Migration execution",
            graph=branching_graph(),
        ),
    )
    version = workflow_definitions.publish(db, item.id, 1)
    identity = uuid.uuid4()
    db.execute(
        text("""
        INSERT INTO workflow_executions
        (id,organization_id,version_id,status,state_revision,input_json,checkpoint_json)
        VALUES (:id,:owner,:version,'pending',0,CAST(:input AS jsonb),'{}'::jsonb)
    """),
        {
            "id": identity,
            "owner": tenant_id(db),
            "version": version.id,
            "input": json.dumps({"value": 2}),
        },
    )
    db.commit()
    return identity
