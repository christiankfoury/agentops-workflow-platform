"""Seed pre-deadline execution rows without using newer execution ORM columns."""

import json
import uuid

from sqlalchemy import text

from src.schemas.workflow_definition import DefinitionCreate
from src.services import workflow_definitions
from src.services.tenancy import tenant_id
from tests.test_graph_interpreter import branching_graph


def legacy_business_rows(conn):
    """Representative historical data using only columns present before Phase 72."""
    ids = {key: uuid.uuid4() for key in ["source", "run", "step", "cost", "case", "result"]}
    statements = [
        (
            "INSERT INTO uploaded_inputs (id,title,input_type,raw_text) VALUES "
            "(:source,'Historical','sales_report','Revenue 10')"
        ),
        (
            "INSERT INTO workflow_runs "
            "(id,input_id,workflow_type,run_mode,status,final_output,total_cost) VALUES "
            "(:run,:source,'sales_report','baseline','completed','Revenue 10',0.01)"
        ),
        (
            "INSERT INTO agent_steps "
            "(id,workflow_run_id,agent_name,agent_type,step_order,status,output_json,model,cost) "
            "VALUES (:step,:run,'Historical "
            "baseline','baseline',1,'completed',jsonb_build_object('final_output','Revenue "
            "10'),'fixture',0.01)"
        ),
        (
            "INSERT INTO cost_events "
            "(id,workflow_run_id,agent_step_id,model,tokens_input,tokens_output,"
            "total_tokens,cost_input,cost_output,total_cost) "
            "VALUES (:cost,:run,:step,'fixture',10,5,15,0.006,0.004,0.01)"
        ),
        (
            "INSERT INTO evaluation_cases "
            "(id,workflow_type,title,input_text,expected_facts_json,expected_risks_json,"
            "expected_recommendations_json) "
            "VALUES (:case,'sales_report','Historical','Revenue 10','[\"Revenue "
            "10\"]','[]','[]')"
        ),
        (
            "INSERT INTO evaluation_results "
            "(id,evaluation_case_id,workflow_run_id,run_mode,status,cost) VALUES "
            "(:result,:case,:run,'baseline','completed',0.01)"
        ),
    ]
    for statement in statements:
        conn.execute(text(statement), ids)
    conn.commit()
    return ids


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
