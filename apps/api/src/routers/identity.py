from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.identity import IdentitySession
from src.services.identity import (
    authenticate,
    create_session,
    memberships,
    resolve_principal,
    token_hash,
)

router = APIRouter()


class SessionCreate(BaseModel):
    nonce: str = Field(min_length=20, max_length=256)


@router.post("/sessions", status_code=201)
def start_session(
    body: SessionCreate, response: Response,
    authorization: str | None = Header(default=None), db: Session = Depends(get_db),
):
    scheme, _, bearer = (authorization or "").partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(401, "A verified identity token is required")
    token, expires = create_session(db, bearer, body.nonce)
    response.headers["Cache-Control"] = "no-store"
    return {"session_token": token, "expires_at": expires}


@router.get("/me")
def current_identity(
    response: Response,
    authorization: str | None = Header(default=None),
    x_organization_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = authenticate(db, authorization)
    response.headers["Cache-Control"] = "no-store"
    if user.kind == "service":
        principal = resolve_principal(db, user, x_organization_id)
        return {
            "id": user.id,
            "display_name": user.display_name,
            "kind": user.kind,
            "organizations": [{"id": principal.organization_id, "role": principal.role}],
            "scopes": sorted(principal.scopes),
        }
    return {
        "id": user.id,
        "display_name": user.display_name,
        "kind": user.kind,
        "organizations": [
            {"id": org.id, "name": org.name, "role": member.role}
            for member, org in memberships(db, user)
        ],
    }


@router.delete("/sessions/current", status_code=204)
def end_session(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authenticate(db, authorization)
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "session":
        raise HTTPException(400, "Only browser sessions can be revoked here")
    session = db.get(IdentitySession, token_hash(token))
    session.revoked = True
    db.commit()
