import hashlib
import json
from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from src.models.prompt_version import PromptVersion
from src.models.workflow_definition import (
    WorkflowDefinition,
    WorkflowVersion,
    WorkflowVersionPrompt,
)
from src.schemas.workflow_definition import ValidationResult
from src.schemas.workflow_graph import WorkflowGraph
from src.services.audit import record_audit
from src.services.graph_validation import ensure_executable
from src.services.permissions import authorize


def definition(db, identity, *, lock=False):
    query = select(WorkflowDefinition).where(WorkflowDefinition.id == identity)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    item = db.scalar(query)
    if item is None:
        raise HTTPException(404, "Workflow definition not found")
    return item


def version(db, definition_id, identity):
    item = db.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.id == identity,
            WorkflowVersion.definition_id == definition_id,
        ).execution_options(populate_existing=True)
    )
    if item is None:
        raise HTTPException(404, "Workflow version not found")
    return item


def check_revision(item, expected):
    if item.draft_revision != expected:
        raise HTTPException(409, "Draft revision changed; reload before editing or publishing")
    if item.archived:
        raise HTTPException(409, "Workflow definition is archived")


def validation_errors(error):
    return error.errors(include_url=False, include_context=False, include_input=False)


def validate_draft(graph):
    try:
        parsed = WorkflowGraph.model_validate(graph)
    except ValidationError as error:
        return ValidationResult(valid=False, errors=validation_errors(error))
    try:
        ensure_executable(parsed)  # No generic executors exist in Phase 71.
    except ValidationError as error:
        return ValidationResult(valid=True, runtime_errors=validation_errors(error))
    return ValidationResult(valid=True, executable=True)


def create_definition(db, body):
    principal = authorize(db, "workflow.draft", lock=True)
    item = WorkflowDefinition(
        name=body.name,
        description=body.description,
        draft_graph=body.graph,
        created_by_user_id=principal.user_id,
    )
    db.add(item)
    db.flush()
    record_audit(db, principal, "workflow.definition.create", "workflow_definition", item.id)
    db.commit()
    return item


def update_draft(db, identity, body):
    principal = authorize(db, "workflow.draft", lock=True)
    item = definition(db, identity, lock=True)
    check_revision(item, body.expected_revision)
    item.name, item.description, item.draft_graph = body.name, body.description, body.graph
    item.draft_revision += 1
    record_audit(
        db,
        principal,
        "workflow.draft.update",
        "workflow_definition",
        item.id,
        revision=item.draft_revision,
    )
    db.commit()
    return item


def publish(db, identity, expected_revision):
    principal = authorize(db, "workflow.publish", lock=True)
    item = definition(db, identity, lock=True)
    check_revision(item, expected_revision)
    try:
        graph = WorkflowGraph.model_validate(item.draft_graph)
    except ValidationError as error:
        raise HTTPException(422, validation_errors(error)) from error
    snapshots = {}
    prompts = sorted({node.config.prompt_version_id for node in graph.nodes if node.type == "llm"})
    for prompt_id in prompts:
        prompt = db.scalar(
            select(PromptVersion)
            .where(PromptVersion.id == prompt_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if prompt is None:
            raise HTTPException(422, "Referenced prompt is not available in this organization")
        snapshots[str(prompt.id)] = {
            "template": prompt.template,
            "version": prompt.version,
            "agent_type": prompt.agent_type.value,
            "name": prompt.name,
        }
    snapshot = graph.model_dump(mode="json")
    number = (
        db.scalar(
            select(func.max(WorkflowVersion.number)).where(
                WorkflowVersion.definition_id == item.id,
            )
        )
        or 0
    ) + 1
    result = WorkflowVersion(
        definition_id=item.id,
        number=number,
        source_revision=item.draft_revision,
        name=item.name,
        description=item.description,
        graph=snapshot,
        graph_hash=hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        prompt_snapshots=snapshots,
        created_by_user_id=principal.user_id,
    )
    db.add(result)
    db.flush()
    for prompt_id in prompts:
        db.add(WorkflowVersionPrompt(version_id=result.id, prompt_id=prompt_id))
    item.published_version_id = result.id
    item.draft_revision += 1  # Competing publication of the same draft conflicts.
    record_audit(
        db,
        principal,
        "workflow.publish",
        "workflow_version",
        result.id,
        definition_id=str(item.id),
        number=number,
        source_revision=result.source_revision,
    )
    db.commit()
    return result


def archive(db, identity, expected_revision, version_id=None):
    principal = authorize(db, "workflow.publish", lock=True)
    item = definition(db, identity, lock=True)
    check_revision(item, expected_revision)
    if version_id:
        target = version(db, identity, version_id)
        target.archived_at = target.archived_at or datetime.now(UTC)
        if item.published_version_id == target.id:
            item.published_version_id = None
    else:
        target = item
        item.archived = True
        item.published_version_id = None
    item.draft_revision += 1
    record_audit(db, principal, "workflow.archive", target.__tablename__, target.id)
    db.commit()
    return item


def require_runnable_version(db, definition_id, version_id):
    item = definition(db, definition_id)
    selected = version(db, definition_id, version_id)
    if item.archived or selected.archived_at:
        raise HTTPException(409, "Workflow definition or version is archived")
    try:
        ensure_executable(WorkflowGraph.model_validate(selected.graph))
    except ValidationError as error:
        raise HTTPException(409, validation_errors(error)) from error
    return selected
