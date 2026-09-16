"""Catalog-bound graph tools and exact human authorization at worker dispatch."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models.execution_approval import ExecutionApproval
from src.models.identity import Membership, User
from src.models.tool import ToolDefinition, ToolVersion
from src.models.workflow_execution import StepRun
from src.schemas.tool import ToolContract
from src.services.approval_runtime import digest, source_hash
from src.services.execution_registry import NodeResult
from src.services.graph_expressions import ExecutionError
from src.services.graph_validation import compatible, invalid
from src.services.retry_runtime import runtime_now
from src.services.tenancy import bind_tenant, tenant_id
from src.services.tool_effects import (
    ADAPTERS,
    ToolAdapter,
    ToolFailure,
    active_credential,
    execute_tool,
)


def pinned_tool(db, node):
    version = db.scalar(
        select(ToolVersion).where(
            ToolVersion.definition_id == node.config.tool_id,
            ToolVersion.number == node.config.version,
        )
    )
    definition = db.get(ToolDefinition, node.config.tool_id)
    if version is None or definition is None or not definition.active:
        raise ValueError("Referenced tool version is unavailable")
    contract = ToolContract.model_validate(version.contract)
    if contract.adapter != node.config.adapter:
        raise ValueError("Tool adapter does not match the pinned contract")
    return version, contract


def validate_references(db, graph, *, bind_policy=False, require_bound=False):
    nodes = {node.id: node for node in graph.nodes}
    for index, node in enumerate(graph.nodes):
        if node.type != "tool":
            continue
        try:
            _, contract = pinned_tool(db, node)
            credential = active_credential(db, contract)
            factory = ADAPTERS.get(contract.adapter)
            adapter = factory(contract, tenant_id(db), credential) if callable(factory) else factory
            if not isinstance(adapter, ToolAdapter):
                raise ValueError("Tool adapter is unavailable")
            if bind_policy:
                node.config.policy_fingerprint = adapter.policy_identity or None
            elif adapter.policy_identity and (
                (require_bound and node.config.policy_fingerprint is None)
                or (
                    node.config.policy_fingerprint is not None
                    and node.config.policy_fingerprint != adapter.policy_identity
                )
            ):
                raise ValueError("Server policy changed; publish a new workflow version")
            side_effecting = (
                adapter.side_effecting(contract.options)
                if callable(adapter.side_effecting)
                else adapter.side_effecting
            )
            if side_effecting != contract.side_effecting:
                raise ValueError("Tool effect policy disagrees with its adapter")
            if not compatible(node.input_schema, contract.input_schema) or not compatible(
                contract.output_schema, node.output_schema
            ):
                raise ValueError("Node schemas disagree with the pinned tool contract")
            if contract.side_effecting and adapter.requires_approval:
                gate = nodes.get(node.config.approval_node)
                ancestors, pending = set(), [node.id]
                while pending:
                    target = pending.pop()
                    for edge in graph.edges:
                        if edge.target == target and edge.source not in ancestors:
                            ancestors.add(edge.source)
                            pending.append(edge.source)
                if gate is None or gate.type != "approval" or gate.id not in ancestors:
                    raise ValueError("Side-effecting tools require an upstream approval node")
        except (ValueError, ExecutionError, ToolFailure, HTTPException):
            invalid(
                ("nodes", index, "config"),
                "Tool reference, policy, schema or approval is unavailable",
            )


def require_approval(db, run, step, node, arguments):
    gate = db.scalar(
        select(StepRun)
        .where(
            StepRun.execution_id == run.id,
            StepRun.node_id == node.config.approval_node,
        )
        .order_by(StepRun.iteration.desc())
        .limit(1)
    )
    item = (
        db.scalar(
            select(ExecutionApproval)
            .where(
                ExecutionApproval.step_run_id == gate.id,
                ExecutionApproval.status == "approved",
            )
            .order_by(ExecutionApproval.revision.desc())
            .limit(1)
        )
        if gate
        else None
    )
    expected = {
        "node_id": node.id,
        "tool_id": str(node.config.tool_id),
        "version": node.config.version,
        "arguments": arguments,
    }
    if (
        gate is None
        or gate.status != "completed"
        or item is None
        or item.version_id != run.version_id
        or gate.iteration < step.iteration
        or digest(item.payload_json) != digest(expected)
        or digest(gate.output_json) != digest(expected)
        or item.source_hash != source_hash(run, gate)
        or (item.expires_at and runtime_now(db) >= item.expires_at)
    ):
        raise ExecutionError(
            "tool_approval_required", "Exact tool action requires current approval"
        )
    if settings.identity_enabled:
        roles = (
            ["admin"]
            if any(
                issue["severity"] in {"high", "critical"} for issue in item.review_json["issues"]
            )
            else ["reviewer", "admin"]
        )
        allowed = db.execute(
            select(Membership.user_id)
            .join(User)
            .where(
                Membership.user_id == item.decided_by_user_id,
                Membership.organization_id == run.organization_id,
                Membership.active.is_(True),
                Membership.role.in_(roles),
                User.active.is_(True),
                User.kind == "user",
            )
            .with_for_update(read=True)
        ).first()
        if allowed is None:
            raise ExecutionError("tool_approval_required", "Tool approver is no longer authorized")


def execute_node(engine, claim, work):
    try:
        with Session(engine) as db:
            bind_tenant(db, claim.organization_id)
            version, _ = pinned_tool(db, work.node)
            version_id = version.id
        return NodeResult(
            execute_tool(
                engine,
                claim,
                work.attempt_id,
                version_id,
                work.inputs,
                control=work.control,
            )
        )
    except ExecutionError:
        raise
    except ToolFailure as error:
        raise ExecutionError(error.code, "Tool policy denied dispatch") from None
    except (ValueError, HTTPException):
        raise ExecutionError("tool_contract_mismatch", "Pinned tool is unavailable") from None
