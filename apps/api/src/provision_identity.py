"""Local administrator bootstrap, requiring direct database access (no public signup)."""

import argparse
import uuid

from sqlalchemy import select

from src.database import SessionLocal
from src.models.identity import Membership, Organization, User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--organization-id", required=True, type=uuid.UUID)
    parser.add_argument("--organization-name", required=True)
    parser.add_argument(
        "--role", required=True, choices=["viewer", "operator", "reviewer", "admin"]
    )
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        org = db.get(Organization, args.organization_id)
        if org is None:
            org = Organization(id=args.organization_id, name=args.organization_name)
            db.add(org)
        user = db.scalar(
            select(User).where(User.issuer == args.issuer, User.subject == args.subject)
        )
        if user is None:
            user = User(issuer=args.issuer, subject=args.subject, display_name=args.display_name)
            db.add(user)
            db.flush()
        elif user.kind != "user" or not user.active:
            parser.error("Existing identity is disabled or is a service principal")
        db.flush()
        member = db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == org.id,
            )
        )
        if member is None:
            db.add(Membership(user_id=user.id, organization_id=org.id, role=args.role))
        elif member.role != args.role or not member.active:
            parser.error("Existing membership differs; use an explicit membership change")
    print("Identity and membership provisioned. No provider credentials were stored.")


if __name__ == "__main__":
    main()
