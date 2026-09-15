"""Organization-scoped ORM sessions, including legacy reads and aggregates."""

import uuid

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session, with_loader_criteria

from src.config import settings
from src.models.tenant import DEFAULT_ORGANIZATION_ID, TenantOwned


class TenantAccessError(Exception):
    pass


def tenant_id(db: Session) -> uuid.UUID:
    selected = db.info.get("organization_id")
    if selected is None:
        if settings.identity_enabled:
            raise TenantAccessError("A verified organization scope is required")
        return DEFAULT_ORGANIZATION_ID
    return selected


def bind_tenant(db: Session, organization_id: uuid.UUID) -> None:
    if not isinstance(db, Session):
        return
    if any(
        isinstance(item, TenantOwned) and item.organization_id != organization_id
        for item in [*db.identity_map.values(), *db.new]
    ):
        raise TenantAccessError("Use a new session when changing organization")
    existing = db.info.get("organization_id")
    if existing is not None and existing != organization_id:
        raise TenantAccessError("An organization scope cannot change within a session")
    db.info["organization_id"] = organization_id


@event.listens_for(Session, "do_orm_execute")
def tenant_reads(state):
    if not any(issubclass(mapper.class_, TenantOwned) for mapper in state.all_mappers):
        return
    if state.is_update or state.is_delete or state.is_insert:
        raise TenantAccessError("Bulk business writes must use scoped entity operations")
    owner = tenant_id(state.session)
    state.statement = state.statement.options(
        with_loader_criteria(
            TenantOwned,
            lambda cls: cls.organization_id == owner,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def tenant_writes(db: Session, _context, _instances):
    records = [item for item in db.new | db.dirty | db.deleted if isinstance(item, TenantOwned)]
    if not records:
        return
    owner = tenant_id(db)
    for item in records:
        if item in db.new and item.organization_id is None:
            item.organization_id = owner
        if item.organization_id != owner:
            raise TenantAccessError("Resource belongs to another organization")
        if item not in db.new and inspect(item).attrs.organization_id.history.has_changes():
            raise TenantAccessError("Resource ownership is immutable")
    # Validate references before SQL errors and include not-yet-flushed seed records.
    pending = {
        (item.__tablename__, item.id): item for item in db.new if isinstance(item, TenantOwned)
    }
    with db.no_autoflush:
        for item in records:
            if item in db.deleted:
                continue
            for column in inspect(type(item)).columns:
                if column.key == "organization_id":
                    continue
                if item not in db.new and not inspect(item).attrs[column.key].history.has_changes():
                    continue
                value = getattr(item, column.key)
                if value is None:
                    continue
                checked_targets = set()
                for foreign_key in column.foreign_keys:
                    target = foreign_key.column.table
                    if target.name in checked_targets:
                        continue
                    checked_targets.add(target.name)
                    if "organization_id" not in target.c:
                        continue
                    if (target.name, value) in pending:
                        continue
                    found = (
                        db.connection()
                        .execute(
                            select(target.c.id).where(
                                target.c.id == value,
                                target.c.organization_id == owner,
                            )
                        )
                        .first()
                    )
                    if found is None:
                        raise TenantAccessError("Referenced resource is not in this organization")
