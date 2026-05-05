"""
Webhook API endpoints - register, list, unregister, and test webhooks.
"""

import uuid
import logging
from typing import Dict, Any, List

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.core.time import utc_now

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# In-memory webhook registry
_webhooks: Dict[str, Dict[str, Any]] = {}


class RegisterWebhookRequest(BaseModel):
    url: str = Field(..., description="URL to receive webhook payloads")
    events: List[str] = Field(default=["*"], description="Event types to subscribe to")
    description: str = Field(default="", description="Optional description")


class WebhookResponse(BaseModel):
    webhook_id: str
    url: str
    events: List[str]
    description: str
    created_at: datetime
    active: bool


class TestWebhookResponse(BaseModel):
    webhook_id: str
    url: str
    status_code: int
    success: bool
    message: str


@router.post("/register", response_model=WebhookResponse)
async def register_webhook(request: RegisterWebhookRequest) -> WebhookResponse:
    """Register a new webhook endpoint."""
    webhook_id = str(uuid.uuid4())
    record = {
        "webhook_id": webhook_id,
        "url": request.url,
        "events": request.events,
        "description": request.description,
        "created_at": utc_now(),
        "active": True,
    }
    _webhooks[webhook_id] = record
    return WebhookResponse(**record)


@router.delete("/{webhook_id}")
async def unregister_webhook(webhook_id: str) -> Dict[str, str]:
    """Remove a registered webhook by ID."""
    if webhook_id not in _webhooks:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found")
    del _webhooks[webhook_id]
    return {"status": "deleted", "webhook_id": webhook_id}


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks() -> List[WebhookResponse]:
    """Return all currently registered webhooks."""
    return [WebhookResponse(**record) for record in _webhooks.values()]


@router.post("/test/{webhook_id}", response_model=TestWebhookResponse)
async def test_webhook(webhook_id: str) -> TestWebhookResponse:
    """Send a test payload to the registered webhook URL."""
    if webhook_id not in _webhooks:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found")
    record = _webhooks[webhook_id]
    payload = {
        "event": "test",
        "webhook_id": webhook_id,
            "timestamp": utc_now().isoformat(),
        "message": "This is a test payload from the trading platform.",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(record["url"], json=payload)
        success = 200 <= response.status_code < 300
        return TestWebhookResponse(
            webhook_id=webhook_id, url=record["url"],
            status_code=response.status_code, success=success,
            message="OK" if success else f"Received {response.status_code}",
        )
    except Exception as exc:
        return TestWebhookResponse(
            webhook_id=webhook_id, url=record["url"],
            status_code=0, success=False, message=str(exc),
        )


async def dispatch_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Dispatch an event to all subscribed webhooks."""
    full_payload = {"event": event_type, "timestamp": utc_now().isoformat(), **payload}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for webhook_id, record in list(_webhooks.items()):
            if not record["active"]:
                continue
            subscribed = record["events"]
            if "*" not in subscribed and event_type not in subscribed:
                continue
            try:
                await client.post(record["url"], json=full_payload)
            except Exception as exc:
                log.warning(f"Failed to dispatch '{event_type}' to webhook {webhook_id}: {exc}")
