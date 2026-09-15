"""Append audit evidence to the caller-owned transaction; never commit separately."""

from sqlalchemy.orm import Session

from src.models.audit_event import AuditEvent
from src.services.identity import Principal
from src.services.tenancy import tenant_id


def record_audit(
    db: Session, principal: Principal, action: str, target_type: str, target_id: object, **details
) -> None:
    if not isinstance(db, Session):
        return
    db.add(
        AuditEvent(
            organization_id=tenant_id(db),
            actor_user_id=principal.user_id,
            service_principal_id=principal.service_principal_id,
            actor_kind="service"
            if principal.service_principal_id
            else ("user" if principal.user_id else "local"),
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            details_json={"actor_role": principal.role, **details},
        )
    )
