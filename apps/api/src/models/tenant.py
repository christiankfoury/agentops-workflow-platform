import uuid

from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

DEFAULT_ORGANIZATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class TenantOwned:
    """All business resources belong to one immutable organization."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        default=DEFAULT_ORGANIZATION_ID,
        server_default=str(DEFAULT_ORGANIZATION_ID),
        index=True,
    )


def tenant_constraints(table: str, references: dict[str, str] | None = None):
    return (
        UniqueConstraint("id", "organization_id", name=f"uq_{table}_tenant_identity"),
        *(
            ForeignKeyConstraint(
                [column, "organization_id"],
                [f"{target}.id", f"{target}.organization_id"],
                name=f"fk_{table}_{column}_tenant",
                deferrable=True,
                initially="DEFERRED",
            )
            for column, target in (references or {}).items()
        ),
    )
