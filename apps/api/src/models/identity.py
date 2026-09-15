"""Server-owned identity and membership records; subjects are scoped by issuer."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base

ROLE_CHECK = "role IN ('viewer', 'operator', 'reviewer', 'admin')"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("issuer", "subject"),
        CheckConstraint("kind IN ('user', 'service')"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issuer: Mapped[str] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16), default="user", server_default="user")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"), CheckConstraint(ROLE_CHECK))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ServicePrincipal(Base):
    __tablename__ = "service_principals"
    __table_args__ = (CheckConstraint("role IN ('viewer', 'operator')"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="operator")
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class IdentitySession(Base):
    __tablename__ = "identity_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
