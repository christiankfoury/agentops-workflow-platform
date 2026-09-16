import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from src.database import get_db
from src.models.audit_event import AuditEvent
from src.models.webhook import WebhookDelivery, WebhookTrigger
from src.schemas.webhook import WebhookCreate, WebhookRotate, WebhookUpdate
from src.services import webhooks

router = APIRouter()
delivery_router = APIRouter()


@router.get("")
def list_triggers(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return [
        webhooks.public_trigger(item)
        for item in db.scalars(
            select(WebhookTrigger)
            .order_by(WebhookTrigger.created_at, WebhookTrigger.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("", status_code=201)
def create_trigger(body: WebhookCreate, db: Session = Depends(get_db)):
    return webhooks.public_trigger(webhooks.create(db, body))


@router.get("/{identity}")
def detail(identity: uuid.UUID, db: Session = Depends(get_db)):
    return webhooks.public_trigger(webhooks.get_trigger(db, identity))


@router.put("/{identity}")
def update_trigger(identity: uuid.UUID, body: WebhookUpdate, db: Session = Depends(get_db)):
    return webhooks.public_trigger(webhooks.update(db, identity, body))


@router.post("/{identity}/rotate-key")
def rotate_key(identity: uuid.UUID, body: WebhookRotate, db: Session = Depends(get_db)):
    return webhooks.public_trigger(webhooks.rotate(db, identity, body))


@router.get("/{identity}/deliveries")
def deliveries(
    identity: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    webhooks.get_trigger(db, identity)
    return db.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.trigger_id == identity)
        .order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id)
        .offset(offset)
        .limit(limit)
    ).all()


@router.get("/{identity}/deliveries/{delivery_id}/events")
def delivery_events(
    identity: uuid.UUID,
    delivery_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    webhooks.get_trigger(db, identity)
    delivery = db.scalar(
        select(WebhookDelivery).where(
            WebhookDelivery.id == delivery_id, WebhookDelivery.trigger_id == identity
        )
    )
    if delivery is None:
        raise HTTPException(404, "Webhook delivery not found")
    return db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.target_type == "webhook_delivery", AuditEvent.target_id == str(delivery.id)
        )
        .order_by(AuditEvent.created_at, AuditEvent.id)
        .offset(offset)
        .limit(limit)
    ).all()


@delivery_router.post("/{identity}", status_code=202)
async def deliver(identity: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
        raise HTTPException(415, "Webhook payload must be application/json")
    headers = []
    for name in ["x-agentops-timestamp", "x-agentops-event-id", "x-agentops-signature"]:
        values = request.headers.getlist(name)
        if len(values) != 1:
            raise HTTPException(401, "Webhook authentication headers are required exactly once")
        headers.append(values[0])
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 262144:
            raise HTTPException(413, "Webhook payload is too large")
        body.extend(chunk)
    return await run_in_threadpool(webhooks.receive, db, identity, *headers, bytes(body))
