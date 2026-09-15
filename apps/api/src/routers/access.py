import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.audit_event import AuditEvent
from src.models.identity import Membership, Organization, User
from src.services.audit import record_audit
from src.services.permissions import PERMISSIONS, authorize, current_principal, permits
from src.services.tenancy import tenant_id

router = APIRouter()


class MembershipUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["viewer", "operator", "reviewer", "admin"]
    active: bool = True


@router.get("/permissions")
def permissions(db: Session = Depends(get_db)):
    principal = current_principal(db)
    return {
        "organization_id": principal.organization_id,
        "role": principal.role,
        "actions": sorted(action for action in PERMISSIONS if permits(principal, action)),
    }


@router.get("/members")
def members(db: Session = Depends(get_db)):
    authorize(db, "membership.manage")
    return [
        dict(row)
        for row in db.execute(
            select(Membership.user_id, Membership.role, Membership.active, User.display_name)
            .join(User)
            .where(Membership.organization_id == tenant_id(db))
            .order_by(User.display_name, Membership.user_id)
        ).mappings()
    ]


@router.put("/members/{user_id}")
def update_membership(user_id: uuid.UUID, body: MembershipUpdate, db: Session = Depends(get_db)):
    org = tenant_id(db)
    # Serialize administrators before reading their role: prevents concurrent
    # revocations and last-admin races without upgrading shared row locks.
    db.execute(select(Organization.id).where(Organization.id == org).with_for_update())
    principal = authorize(db, "membership.manage", lock=True)
    target = db.get(User, user_id)
    if target is None or target.kind != "user" or not target.active:
        raise HTTPException(404, "Active user not found")
    member = db.scalar(
        select(Membership)
        .where(
            Membership.organization_id == org,
            Membership.user_id == user_id,
        )
        .with_for_update()
    )
    if (
        member
        and member.role == "admin"
        and member.active
        and (body.role != "admin" or not body.active)
    ):
        other_admin = db.scalar(
            select(Membership.id)
            .join(User)
            .where(
                Membership.organization_id == org,
                Membership.role == "admin",
                Membership.active.is_(True),
                Membership.user_id != user_id,
                User.active.is_(True),
                User.kind == "user",
            )
        )
        if other_admin is None:
            raise HTTPException(409, "An organization must retain an active administrator")
    if member is None:
        member = Membership(user_id=user_id, organization_id=org)
        db.add(member)
    previous = {"role": member.role, "active": member.active}
    member.role, member.active = body.role, body.active
    record_audit(
        db,
        principal,
        "membership.update",
        "user_membership",
        user_id,
        previous=previous,
        role=body.role,
        active=body.active,
    )
    db.commit()
    return {"user_id": user_id, "role": body.role, "active": body.active}


@router.get("/audit")
def audit(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    authorize(db, "audit.read")
    return db.scalars(
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
