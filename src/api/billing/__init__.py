"""
Stripe billing API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.auth.middleware import get_current_user
from src.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


class CreateCheckoutSession(BaseModel):
    price_id: str = "price_free_tier"
    success_url: str = "/dashboard?subscription=success"
    cancel_url: str = "/dashboard?subscription=cancelled"


class CreatePortalSession(BaseModel):
    return_url: str = "/dashboard"


@router.post("/create-checkout")
async def create_checkout_session(
    checkout: CreateCheckoutSession,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Create Stripe checkout session for subscription.
    
    Returns Stripe checkout URL for payment.
    """
    if not settings.STRIPE_SECRET_KEY:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"message": "Stripe not configured"}
        )
    
    try:
        import httpx
        from src.config import settings
        
        headers = {
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "mode": "subscription",
            "customer_email": current_user.get("email"),
            "line_items": [{"price": checkout.price_id, "quantity": 1}],
            "success_url": checkout.success_url,
            "cancel_url": checkout.cancel_url,
            "metadata": {"user_id": current_user.get("user_id")}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Stripe error: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to create checkout session")
            
            data = response.json()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"checkout_url": data.get("url"), "session_id": data.get("id")}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Checkout session error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/create-portal")
async def create_portal_session(
    portal: CreatePortalSession,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Create Stripe customer portal session.
    
    Returns Stripe portal URL for subscription management.
    """
    if not settings.STRIPE_SECRET_KEY:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"message": "Stripe not configured"}
        )
    
    try:
        import httpx
        from src.config import settings
        
        headers = {
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "return_url": portal.return_url,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stripe.com/v1/billing_portal/sessions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Stripe error: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to create portal session")
            
            data = response.json()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"portal_url": data.get("url")}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portal session error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/webhook")
async def stripe_webhook(request: Request) -> JSONResponse:
    """
    Handle Stripe webhook events.
    
    For production: verify webhook signature.
    """
    try:
        body = await request.body()
        from src.config import settings
        
        if settings.STRIPE_WEBHOOK_SECRET:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            sig_header = request.headers.get("stripe-signature")
            if sig_header:
                try:
                    event = stripe.Webhook.construct_event(
                        body, sig_header, settings.STRIPE_WEBHOOK_SECRET
                    )
                except stripe.error.SignatureVerificationError:
                    raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            import json
            event = json.loads(body)
        
        if event.get("type") == "checkout.session.completed":
            logger.info(f"Checkout completed: {event.get('data', {}).get('object', {}).get('id')}")
        elif event.get("type") == "customer.subscription.deleted":
            logger.info(f"Subscription deleted: {event.get('data', {}).get('object', {}).get('id')}")
        
        return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True})


@router.get("/status")
async def get_subscription_status(
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Get current user's subscription status.
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "tier": "free",
            "status": "active",
            "features": [
                "paper_trading",
                "basic_indicators",
                "news_classification",
                "multi_agent_simulation",
                "vectorized_backtesting"
            ]
        }
    )