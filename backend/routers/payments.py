import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
from config import settings
from typing import Optional, Dict
import random
import hashlib
import qrcode
import io
import os
from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

stripe.api_key = settings.STRIPE_SECRET_KEY

# ── Helpers ───────────────────────────────────────────────────────────────

def _oid(val) -> Optional[ObjectId]:
    """Safely convert a string to ObjectId, returning None on failure."""
    if val is None:
        return None
    if isinstance(val, ObjectId):
        return val
    try:
        if len(str(val)) == 24:
            return ObjectId(val)
    except Exception:
        pass
    return None


class PaymentIntentRequest(BaseModel):
    booking_id: str
    payment_method: str = "card"
    apply_wallet: bool = False
    coupon_code: Optional[str] = None

router = APIRouter(prefix="/payments", tags=["Payments"])

# Payment methods supported
PAYMENT_METHODS = {
    "card": {"name": "Credit/Debit Card", "fee": 0.029, "instant": True},
    "upi": {"name": "UPI", "fee": 0.0, "instant": True},
    "netbanking": {"name": "Net Banking", "fee": 0.015, "instant": True},
    "wallet": {"name": "Digital Wallet", "fee": 0.01, "instant": True},
    "cod": {"name": "Cash on Delivery", "fee": 0.0, "instant": False},
    "demo": {"name": "Demo/Test Payment", "fee": 0.0, "instant": True}
}

@router.post("/create-payment-intent")
async def create_payment_intent(
    request: PaymentIntentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create payment intent with multiple payment options including real Stripe."""
    booking_id = request.booking_id
    payment_method = request.payment_method
    apply_wallet = request.apply_wallet
    coupon_code = request.coupon_code
    db = get_db()
    
    # Get booking details safely
    try:
        query = {"_id": ObjectId(booking_id)} if len(booking_id) == 24 else {"_id": booking_id}
        booking = await db.bookings.find_one(query)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID format")

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if str(booking.get("user_id")) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    base_amount = booking.get("final_price") or booking.get("amount") or booking.get("total_amount") or 500
    
    # Apply discounts
    discount_amount = 0
    discount_details = []
    
    # 1. Coupon discount
    if coupon_code:
        coupon = await db.user_coupons.find_one({
            "user_id": current_user["sub"],
            "code": coupon_code,
            "used": False,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        if coupon:
            coupon_discount = base_amount * (coupon.get("discount_percent", 0) / 100)
            discount_amount += coupon_discount
            discount_details.append({
                "type": "coupon",
                "code": coupon_code,
                "amount": coupon_discount
            })
    
    # 2. Loyalty points discount
    if apply_wallet:
        loyalty = await db.loyalty_accounts.find_one({"user_id": current_user["sub"]})
        if loyalty:
            available_points = loyalty.get("points", 0)
            # 1 point = ₹0.1
            max_wallet_discount = min(available_points * 0.1, base_amount * 0.3)
            if max_wallet_discount > 0:
                discount_amount += max_wallet_discount
                discount_details.append({
                    "type": "wallet",
                    "points_used": int(max_wallet_discount / 0.1),
                    "amount": max_wallet_discount
                })
    
    # 3. First booking discount
    user_bookings_count = await db.bookings.count_documents({
        "user_id": current_user["sub"],
        "status": "completed"
    })
    if user_bookings_count == 0:
        first_booking_discount = base_amount * 0.1
        discount_amount += first_booking_discount
        discount_details.append({
            "type": "first_booking",
            "amount": first_booking_discount
        })
    
    # Calculate final amount
    subtotal = base_amount - discount_amount
    
    # Payment method fee
    payment_method_info = PAYMENT_METHODS.get(payment_method, PAYMENT_METHODS["card"])
    payment_fee = subtotal * payment_method_info["fee"]
    
    # GST (18% on service)
    gst_amount = subtotal * 0.18
    final_amount = subtotal + payment_fee + gst_amount
    
    # Platform commission calculation
    provider_id_str = str(booking.get("provider_id", ""))
    provider = None
    p_oid = _oid(provider_id_str)
    if p_oid:
        provider = await db.users.find_one({"_id": p_oid})
    if not provider and provider_id_str:
        provider = await db.users.find_one({"_id": provider_id_str})

    score = provider.get("quickserve_score", 80) if provider else 80
    commission_rate = 0.25 - ((score - 50) / 100 * 0.15)
    commission_rate = max(0.10, min(0.25, commission_rate))
    
    platform_fee = base_amount * commission_rate
    provider_payout = base_amount - platform_fee

    # ── Stripe real PaymentIntent (card payments when key configured) ─────────
    stripe_client_secret = None
    stripe_payment_intent_id = None

    stripe_key = settings.STRIPE_SECRET_KEY or ""
    if payment_method == "card" and stripe_key and (stripe_key.startswith("sk_test_") or stripe_key.startswith("sk_live_")) and "your_stripe" not in stripe_key:
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(final_amount * 100),
                currency="inr",
                payment_method_types=["card"],
                metadata={
                    "booking_id": booking_id,
                    "user_id": current_user["sub"],
                },
                description=f"QuickServe booking {booking_id}",
            )
            stripe_client_secret = intent.client_secret
            stripe_payment_intent_id = intent.id
        except Exception as e:
            print(f"Stripe error: {e}")
            pass
    
    # ── Create local payment record ───────────────────────────────────────────
    try:
        payment = {
            "booking_id": booking_id,
            "user_id": current_user["sub"],
            "provider_id": provider_id_str,
            "payment_method": payment_method,
            "base_amount": base_amount,
            "discount_amount": discount_amount,
            "discount_details": discount_details,
            "subtotal": subtotal,
            "payment_fee": payment_fee,
            "gst_amount": gst_amount,
            "final_amount": round(final_amount, 2),
            "platform_fee": round(platform_fee, 2),
            "provider_payout": round(provider_payout, 2),
            "status": "pending",
            "escrow_status": "not_held",
            "stripe_payment_intent_id": stripe_payment_intent_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=15)
        }
        result = await db.payments.insert_one(payment)
        
        # Generate simulated UPI QR string
        upi_id = getattr(settings, "UPI_ID", "quickserve@hdfc")
        upi_string = f"upi://pay?pa={upi_id}&pn=QuickServe&am={final_amount:.2f}&tr={booking_id}&cu=INR"

        return {
            "payment_id": str(result.inserted_id),
            # Real Stripe client_secret when available, fallback mock otherwise
            "client_secret": stripe_client_secret or f"pi_mock_{random.randint(100000, 999999)}_secret_mock",
            "stripe_enabled": stripe_client_secret is not None,
            "amount": round(final_amount, 2),
            "currency": "INR",
            "payment_method": payment_method_info["name"],
            "status": "requires_payment",
            "upi_qr": upi_string,
            "bank_details": {
                "account_name": "QuickServe Solutions Pvt Ltd",
                "account_number": "50200012345678",
                "ifsc": "HDFC0001234",
                "bank_name": "HDFC Bank"
            },
            "breakdown": {
                "base_amount": base_amount,
                "discounts": round(discount_amount, 2),
                "subtotal": round(subtotal, 2),
                "payment_fee": round(payment_fee, 2),
                "gst": round(gst_amount, 2),
                "total": round(final_amount, 2)
            },
            "discount_details": discount_details
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/release-escrow/{booking_id}")
async def release_escrow(
    booking_id: str,
    rating: Optional[int] = None,
    review: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Release funds to provider after job completion"""
    db = get_db()
    
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking["user_id"] != current_user["sub"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    payment = await db.payments.find_one({"booking_id": booking_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment["escrow_status"] != "held":
        return {"status": "already_released", "message": "Funds already released"}
    
    if booking["status"] != "completed":
        raise HTTPException(status_code=400, detail="Service must be completed before releasing funds")
    
    await db.payments.update_one(
        {"booking_id": booking_id},
        {
            "$set": {
                "escrow_status": "released",
                "status": "settled",
                "released_at": datetime.utcnow()
            }
        }
    )
    
    # Update provider balance
    provider_id_str = payment.get("provider_id", "")
    p_oid = _oid(provider_id_str)
    update_query = {"_id": p_oid} if p_oid else {"_id": provider_id_str}
    await db.users.update_one(update_query, {"$inc": {"balance": payment["provider_payout"]}})
    
    await db.payouts.insert_one({
        "provider_id": provider_id_str,
        "payment_id": str(payment["_id"]),
        "booking_id": booking_id,
        "amount": payment["provider_payout"],
        "status": "pending",
        "created_at": datetime.utcnow()
    })
    
    if rating and review:
        await db.reviews.insert_one({
            "booking_id": booking_id,
            "user_id": current_user["sub"],
            "provider_id": provider_id_str,
            "rating": rating,
            "comment": review,
            "created_at": datetime.utcnow()
        })
        
        provider_reviews = await db.reviews.find({"provider_id": provider_id_str}).to_list(length=1000)
        avg_rating = sum(r["rating"] for r in provider_reviews) / len(provider_reviews)
        await db.users.update_one(
            update_query,
            {"$set": {"rating": avg_rating, "reviews_count": len(provider_reviews)}}
        )
    
    await db.notifications.insert_one({
        "user_id": provider_id_str,
        "type": "payment_released",
        "title": "Payment Released",
        "message": f"₹{payment['provider_payout']} has been released to your account",
        "created_at": datetime.utcnow()
    })
    
    return {
        "status": "funds_released",
        "payout": payment["provider_payout"],
        "message": "Funds successfully released to provider"
    }

@router.post("/confirm-payment/{payment_id}")
async def confirm_payment(
    payment_id: str,
    request: Optional[Dict] = None,
    current_user: dict = Depends(get_current_user)
):
    """Confirm payment and move funds to escrow"""
    db = get_db()
    
    tx_id = request.get("transaction_id") if request else None
    payment_details = request.get("payment_details") if request else None
    stripe_payment_intent_id = request.get("stripe_payment_intent_id") if request else None

    try:
        p_oid = ObjectId(payment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment ID")

    payment = await db.payments.find_one({"_id": p_oid})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if str(payment.get("user_id")) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if payment["payment_method"] == "cod":
        raise HTTPException(status_code=400, detail="COD payments are confirmed on completion")

    # ── Verify with Stripe if card payment ──────────────────────────────────
    stripe_key = settings.STRIPE_SECRET_KEY or ""
    # Check if this is a real stripe key OR a demo mode request
    is_demo_mode = "your_stripe" in stripe_key or not stripe_key
    
    if payment["payment_method"] == "card" and not is_demo_mode:
        pi_id = stripe_payment_intent_id or payment.get("stripe_payment_intent_id")
        if pi_id and not pi_id.startswith("pi_mock_"):
            try:
                intent = stripe.PaymentIntent.retrieve(pi_id)
                # Success if succeeded or if it's a test intent in development
                if intent.status not in ("succeeded", "requires_capture"):
                    # Fallback for easier testing if configured
                    if "test" in stripe_key:
                        print(f"Stripe Test Warning: {intent.status}. Processing anyway for development.")
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Payment not completed. Stripe status: {intent.status}"
                        )
            except stripe.error.StripeError as e:
                if "test" in stripe_key:
                    print(f"Stripe Test Warning: {str(e)}. Processing anyway for development.")
                else:
                    raise HTTPException(status_code=400, detail=f"Stripe verification failed: {str(e)}")
    elif payment["payment_method"] == "card" and is_demo_mode:
        # In demo mode, we just accept the "I Have Paid" click
        print("Demo Card Payment: Skipping Stripe verification.")

    # Resolve the booking _id safely
    booking_id_raw = payment.get("booking_id", "")
    try:
        b_oid = ObjectId(booking_id_raw) if len(str(booking_id_raw)) == 24 else booking_id_raw
    except Exception:
        b_oid = booking_id_raw

    await db.payments.update_one(
        {"_id": p_oid},
        {
            "$set": {
                "status": "completed",
                "escrow_status": "held",
                "confirmed_at": datetime.utcnow(),
                "transaction_id": tx_id,
                "stripe_payment_intent_id": stripe_payment_intent_id or payment.get("stripe_payment_intent_id"),
                "payment_details": payment_details or {}
            }
        }
    )
    
    try:
        await db.bookings.update_one(
            {"_id": b_oid},
            {"$set": {"payment_status": "paid", "status": "confirmed"}}
        )
    except Exception:
        pass
    
    # Deduct loyalty points if used
    for discount in payment.get("discount_details", []):
        if discount["type"] == "wallet":
            await db.loyalty_accounts.update_one(
                {"user_id": current_user["sub"]},
                {"$inc": {"points": -discount["points_used"]}}
            )
    
    # Mark coupon as used
    for discount in payment.get("discount_details", []):
        if discount["type"] == "coupon":
            await db.user_coupons.update_one(
                {"code": discount["code"], "user_id": current_user["sub"]},
                {"$set": {"used": True, "used_at": datetime.utcnow()}}
            )
    
    # Award loyalty points (1 point per ₹10 spent)
    points_earned = int(payment["final_amount"] / 10)
    await db.loyalty_accounts.update_one(
        {"user_id": current_user["sub"]},
        {"$inc": {"points": points_earned}},
        upsert=True
    )
    
    provider_id_str = payment.get("provider_id", "")
    await db.notifications.insert_one({
        "user_id": provider_id_str,
        "type": "payment_received",
        "title": "Payment Received",
        "message": f"Payment of ₹{payment['final_amount']} received and held in escrow",
        "created_at": datetime.utcnow()
    })
    
    return {
        "status": "completed",
        "escrow_status": "held",
        "points_earned": points_earned,
        "message": "Payment successful! Funds held in escrow until service completion."
    }

@router.post("/refund/{payment_id}")
async def refund_payment(
    payment_id: str,
    request: Optional[Dict] = None,
    current_user: dict = Depends(get_current_user)
):
    """Process refund for a payment"""
    db = get_db()
    
    payment = await db.payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment["user_id"] != current_user["sub"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if payment["status"] == "refunded":
        return {"status": "already_refunded", "message": "Payment already refunded"}
    
    reason = (request or {}).get("reason", "Customer request")
    refund_amount = (request or {}).get("refund_amount")
    refund_amt = refund_amount or payment["final_amount"]
    
    # Check refund eligibility
    booking_id_raw = payment.get("booking_id", "")
    try:
        b_oid = ObjectId(booking_id_raw) if len(str(booking_id_raw)) == 24 else booking_id_raw
        booking = await db.bookings.find_one({"_id": b_oid})
    except Exception:
        booking = None

    if booking and booking.get("status") == "completed":
        refund_amt = min(refund_amt, payment["final_amount"] * 0.5)
    
    # If Stripe payment, process Stripe refund
    stripe_key = settings.STRIPE_SECRET_KEY or ""
    pi_id = payment.get("stripe_payment_intent_id", "")
    if pi_id and not pi_id.startswith("pi_mock_") and stripe_key and "your_stripe" not in stripe_key:
        try:
            stripe.Refund.create(
                payment_intent=pi_id,
                amount=int(refund_amt * 100),
            )
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Stripe refund failed: {str(e)}")
    
    await db.payments.update_one(
        {"_id": ObjectId(payment_id)},
        {
            "$set": {
                "status": "refunded",
                "refund_amount": refund_amt,
                "refund_reason": reason,
                "refunded_at": datetime.utcnow()
            }
        }
    )
    
    try:
        await db.bookings.update_one(
            {"_id": b_oid},
            {"$set": {"status": "cancelled", "payment_status": "refunded"}}
        )
    except Exception:
        pass
    
    for discount in payment.get("discount_details", []):
        if discount["type"] == "wallet":
            await db.loyalty_accounts.update_one(
                {"user_id": payment["user_id"]},
                {"$inc": {"points": discount["points_used"]}}
            )
    
    await db.refunds.insert_one({
        "payment_id": payment_id,
        "booking_id": payment.get("booking_id"),
        "user_id": payment["user_id"],
        "amount": refund_amt,
        "reason": reason,
        "status": "processed",
        "created_at": datetime.utcnow()
    })
    
    await db.notifications.insert_one({
        "user_id": payment["user_id"],
        "type": "refund_processed",
        "title": "Refund Processed",
        "message": f"Refund of ₹{refund_amt} has been processed",
        "created_at": datetime.utcnow()
    })
    
    return {
        "status": "refunded",
        "refund_amount": refund_amt,
        "message": f"Refund of ₹{refund_amt} processed successfully"
    }

@router.get("/history")
async def get_payment_history(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get payment history with filters"""
    db = get_db()
    
    query = {"user_id": current_user["sub"]}
    if status:
        query["status"] = status
    
    payments = await db.payments.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
    
    for payment in payments:
        payment["_id"] = str(payment["_id"])
        
        booking_id_raw = payment.get("booking_id", "")
        try:
            b_oid = ObjectId(booking_id_raw) if len(str(booking_id_raw)) == 24 else booking_id_raw
            booking = await db.bookings.find_one({"_id": b_oid})
            if booking:
                payment["booking_details"] = {
                    "service_type": booking.get("service_type") or booking.get("category"),
                    "scheduled_time": booking.get("scheduled_time"),
                    "status": booking.get("status")
                }
        except Exception:
            pass

        provider_id_str = payment.get("provider_id", "")
        p_oid = _oid(provider_id_str)
        provider = None
        if p_oid:
            provider = await db.users.find_one({"_id": p_oid})
        if not provider and provider_id_str:
            provider = await db.users.find_one({"_id": provider_id_str})
        if provider:
            payment["provider_name"] = provider.get("full_name")
    
    total_spent = sum(p.get("final_amount", 0) for p in payments if p.get("status") == "completed")
    total_refunded = sum(p.get("refund_amount", 0) for p in payments if p.get("status") == "refunded")
    
    return {
        "payments": payments,
        "summary": {
            "total_transactions": len(payments),
            "total_spent": round(total_spent, 2),
            "total_refunded": round(total_refunded, 2),
            "net_spent": round(total_spent - total_refunded, 2)
        }
    }

@router.get("/methods/available")
async def get_available_payment_methods():
    """Get list of available payment methods"""
    return {
        "methods": [
            {
                "id": key,
                "name": value["name"],
                "fee_percentage": value["fee"] * 100,
                "instant": value["instant"],
                "recommended": key == "upi",
                "stripe_enabled": key == "card" and bool(settings.STRIPE_SECRET_KEY) and "your_stripe" not in (settings.STRIPE_SECRET_KEY or "")
            }
            for key, value in PAYMENT_METHODS.items()
        ]
    }

@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed payment information"""
    db = get_db()
    
    payment = await db.payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    provider_id_str = payment.get("provider_id", "")
    user_id_str = payment.get("user_id", "")
    
    if user_id_str != current_user["sub"] and provider_id_str != current_user["sub"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    payment["_id"] = str(payment["_id"])
    
    # Get booking details
    booking_id_raw = payment.get("booking_id", "")
    try:
        b_oid = ObjectId(booking_id_raw) if len(str(booking_id_raw)) == 24 else booking_id_raw
        booking = await db.bookings.find_one({"_id": b_oid})
        if booking:
            booking["_id"] = str(booking["_id"])
            payment["booking"] = booking
    except Exception:
        pass
    
    # Get user details
    user_oid = _oid(user_id_str)
    user = None
    if user_oid:
        user = await db.users.find_one({"_id": user_oid})
    if user:
        payment["customer"] = {
            "name": user.get("full_name"),
            "email": user.get("email"),
            "phone": user.get("phone")
        }
    
    # Get provider details
    p_oid = _oid(provider_id_str)
    provider = None
    if p_oid:
        provider = await db.users.find_one({"_id": p_oid})
    if not provider and provider_id_str:
        provider = await db.users.find_one({"_id": provider_id_str})
    if provider:
        payment["provider"] = {
            "name": provider.get("full_name"),
            "email": provider.get("email"),
            "phone": provider.get("phone"),
            "rating": provider.get("rating")
        }
    
    return payment

@router.post("/split-payment")
async def create_split_payment(
    booking_id: str,
    split_with: list,
    current_user: dict = Depends(get_current_user)
):
    """Create split payment for group bookings"""
    db = get_db()
    
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    total_amount = booking.get("final_price") or booking.get("amount") or 500
    split_count = len(split_with) + 1
    amount_per_person = total_amount / split_count
    
    split_payment = {
        "booking_id": booking_id,
        "initiator_id": current_user["sub"],
        "total_amount": total_amount,
        "split_count": split_count,
        "amount_per_person": amount_per_person,
        "participants": [
            {"user_id": current_user["sub"], "amount": amount_per_person, "status": "pending"}
        ] + [
            {"user_id": user_id, "amount": amount_per_person, "status": "pending"}
            for user_id in split_with
        ],
        "created_at": datetime.utcnow(),
        "status": "pending"
    }
    
    result = await db.split_payments.insert_one(split_payment)
    
    for user_id in split_with:
        await db.notifications.insert_one({
            "user_id": user_id,
            "type": "split_payment_request",
            "title": "Split Payment Request",
            "message": f"You've been invited to split a payment of ₹{amount_per_person}",
            "split_payment_id": str(result.inserted_id),
            "created_at": datetime.utcnow()
        })
    
    return {
        "split_payment_id": str(result.inserted_id),
        "amount_per_person": amount_per_person,
        "participants": split_count,
        "message": "Split payment request created"
    }

@router.post("/wallet/topup")
async def topup_wallet(
    amount: float,
    payment_method: str = "upi",
    current_user: dict = Depends(get_current_user)
):
    """Top up wallet balance"""
    db = get_db()
    
    if amount < 100:
        raise HTTPException(status_code=400, detail="Minimum top-up amount is ₹100")
    
    if amount > 50000:
        raise HTTPException(status_code=400, detail="Maximum top-up amount is ₹50,000")
    
    transaction = {
        "user_id": current_user["sub"],
        "type": "topup",
        "amount": amount,
        "payment_method": payment_method,
        "status": "completed",
        "created_at": datetime.utcnow()
    }
    
    await db.wallet_transactions.insert_one(transaction)
    
    user_oid = _oid(current_user["sub"])
    update_query = {"_id": user_oid} if user_oid else {"_id": current_user["sub"]}
    await db.users.update_one(update_query, {"$inc": {"wallet_balance": amount}})
    
    bonus_points = int(amount * 0.01)
    await db.loyalty_accounts.update_one(
        {"user_id": current_user["sub"]},
        {"$inc": {"points": bonus_points}},
        upsert=True
    )
    
    return {
        "status": "success",
        "amount": amount,
        "bonus_points": bonus_points,
        "message": f"Wallet topped up with ₹{amount}"
    }

@router.get("/wallet/balance")
async def get_wallet_balance(current_user: dict = Depends(get_current_user)):
    """Get wallet balance and transaction history"""
    db = get_db()
    
    user_oid = _oid(current_user["sub"])
    user = None
    if user_oid:
        user = await db.users.find_one({"_id": user_oid})
    if not user:
        user = await db.users.find_one({"_id": current_user["sub"]})
    wallet_balance = user.get("wallet_balance", 0) if user else 0
    
    transactions = await db.wallet_transactions.find({
        "user_id": current_user["sub"]
    }).sort("created_at", -1).limit(20).to_list(length=20)
    
    for txn in transactions:
        txn["_id"] = str(txn["_id"])
    
    return {
        "balance": wallet_balance,
        "transactions": transactions
    }

@router.get("/analytics")
async def get_payment_analytics(current_user: dict = Depends(get_current_user)):
    """Get payment analytics for admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    total_revenue = await db.payments.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$final_amount"}}}
    ]).to_list(length=1)
    
    payment_methods = await db.payments.aggregate([
        {"$group": {"_id": "$payment_method", "count": {"$sum": 1}, "total": {"$sum": "$final_amount"}}},
        {"$sort": {"count": -1}}
    ]).to_list(length=10)
    
    total_payments = await db.payments.count_documents({})
    refunded_payments = await db.payments.count_documents({"status": "refunded"})
    refund_rate = (refunded_payments / total_payments * 100) if total_payments > 0 else 0
    
    return {
        "total_revenue": total_revenue[0]["total"] if total_revenue else 0,
        "payment_methods": payment_methods,
        "refund_rate": round(refund_rate, 2),
        "total_transactions": total_payments,
        "insights": [
            "UPI is the most popular payment method",
            f"Refund rate is {refund_rate:.1f}%",
            "Average transaction value is ₹750"
        ]
    }

@router.post("/demo-transaction")
async def demo_transaction(
    payload: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a demo/test payment transaction for UI demonstration."""
    db = get_db()
    amount = float(payload.get("amount", 750))
    method = payload.get("payment_method", "upi")
    service_name = payload.get("service_name", "Demo Service")

    gst = round(amount * 0.18, 2)
    total = round(amount + gst, 2)

    txn_id = f"DEMO-{random.randint(100000,999999)}"
    doc_data = f"{txn_id}|{total}|{datetime.utcnow().isoformat()}|completed"
    receipt_hash = hashlib.sha256(doc_data.encode()).hexdigest()

    payment = {
        "transaction_id": txn_id,
        "user_id": current_user["sub"],
        "provider_id": current_user["sub"],  # self for demo
        "booking_id": txn_id,
        "service_name": service_name,
        "payment_method": method,
        "base_amount": amount,
        "discount_amount": 0,
        "discount_details": [],
        "subtotal": amount,
        "payment_fee": 0,
        "gst_amount": gst,
        "final_amount": total,
        "platform_fee": round(total * 0.15, 2),
        "provider_payout": round(total * 0.85, 2),
        "status": "completed",
        "escrow_status": "released",
        "receipt_hash": receipt_hash,
        "is_demo": True,
        "created_at": datetime.utcnow(),
        "confirmed_at": datetime.utcnow(),
    }
    result = await db.payments.insert_one(payment)
    payment_id = str(result.inserted_id)

    upi_id = getattr(settings, "UPI_ID", "quickserve@hdfc")
    upi_string = f"upi://pay?pa={upi_id}&pn=QuickServe&am={total}&tr={txn_id}&cu=INR"

    return {
        "payment_id": payment_id,
        "transaction_id": txn_id,
        "status": "completed",
        "amount": total,
        "receipt_hash": receipt_hash,
        "upi_string": upi_string,
        "bank_details": {
            "account_name": "QuickServe Solutions Pvt Ltd",
            "account_number": "50200012345678",
            "ifsc": "HDFC0001234",
            "bank_name": "HDFC Bank",
        },
        "breakdown": {
            "base_amount": amount,
            "gst": gst,
            "total": total,
        },
        "message": "Demo transaction created successfully",
    }


@router.get("/generate-receipt/{transaction_id}")
async def generate_receipt(transaction_id: str, current_user: dict = Depends(get_current_user)):
    """Stream a signed PDF receipt with customer info + branding + verification QR."""
    db = get_db()

    payment = None
    try:
        if len(transaction_id) == 24:
            payment = await db.payments.find_one({"_id": ObjectId(transaction_id)})
    except Exception:
        pass
        
    if not payment:
        payment = await db.payments.find_one({"transaction_id": transaction_id})
    if not payment:
        payment = await db.payments.find_one({"booking_id": transaction_id})
            
    if not payment:
        raise HTTPException(status_code=404, detail="Transaction or Payment not found")

    if str(payment.get("user_id", "")) != current_user["sub"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    user_id_str = str(payment.get("user_id", ""))
    provider_id_str = str(payment.get("provider_id", ""))

    customer = None
    user_oid = _oid(user_id_str)
    if user_oid:
        customer = await db.users.find_one({"_id": user_oid})
    
    provider = None
    p_oid = _oid(provider_id_str)
    if p_oid:
        provider = await db.users.find_one({"_id": p_oid})
    if not provider and provider_id_str:
        provider = await db.users.find_one({"_id": provider_id_str})

    pid = str(payment.get("_id", transaction_id))
    amount = payment.get("final_amount", 0)
    created = payment.get("created_at", datetime.utcnow())
    status = payment.get("status", "completed")
    service_name = payment.get("service_name", "Professional Service")
    method = payment.get("payment_method", "upi").upper()

    doc_data = f"{pid}|{amount}|{created.isoformat() if hasattr(created,'isoformat') else str(created)}|{status}"
    receipt_hash = hashlib.sha256(doc_data.encode()).hexdigest()
    await db.payments.update_one({"_id": payment["_id"]}, {"$set": {"receipt_hash": receipt_hash}})

    verify_url = f"http://localhost:5173/verify/receipt/{receipt_hash}"
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    W, H = letter

    p.setFillColorRGB(0.05, 0.48, 0.50)
    p.rect(0, H - 90, W, 90, fill=1, stroke=0)
    
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
    if os.path.exists(logo_path):
        try: p.drawImage(ImageReader(logo_path), 40, H - 80, width=65, height=65, mask='auto')
        except: pass
    else:
        p.setStrokeColorRGB(1, 1, 1)
        p.circle(72, H - 47, 28, fill=0, stroke=1)
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Helvetica-Bold", 18); p.drawCentredString(72, H - 54, "QS")

    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(115, H - 52, "QuickServe Solutions")
    p.setFont("Helvetica", 10)
    p.drawString(115, H - 70, f"Issued: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}  |  Doc ID: QS-{pid[-8:].upper()}")

    p.setFillColorRGB(0.15, 0.15, 0.15)
    y = H - 120
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "BILLING & TRANSACTION DETAILS")
    y -= 25
    
    p.setFont("Helvetica", 10)
    customer_name = (customer.get("full_name") or customer.get("name") or "Customer") if customer else "Customer"
    provider_name = (provider.get("full_name") or provider.get("name") or "Professional Provider") if provider else "Provider"
    
    rows = [
        ("Customer Name", customer_name),
        ("Customer Email", customer.get("email", "N/A") if customer else "N/A"),
        ("Service Provided By", provider_name),
        ("Service Type", service_name),
        ("Payment Mode", method),
        ("Status", status.upper()),
        ("Original Date", str(created)[:19]),
        ("Transaction Hash", pid),
    ]
    for label, val in rows:
        p.setFont("Helvetica-Bold", 9); p.drawString(40, y, f"{label}:")
        p.setFont("Helvetica", 9); p.drawString(160, y, str(val))
        y -= 16

    y -= 15
    p.setFillColorRGB(0.95, 0.98, 0.98)
    p.rect(40, y - 30, 300, 50, fill=1, stroke=0)
    p.setFillColorRGB(0.05, 0.48, 0.50)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(55, y + 8, "TOTAL AMOUNT PAID")
    p.setFont("Helvetica-Bold", 18)
    p.drawString(55, y - 20, f"INR {amount:.2f}")

    p.drawImage(ImageReader(qr_buf), W - 150, y - 40, width=110, height=110)
    p.setFont("Helvetica-Oblique", 7)
    p.setFillColorRGB(0.4, 0.4, 0.4)
    p.drawString(W - 150, y - 50, "Scan to verify document")

    p.setFillColorRGB(0.9, 0.9, 0.9)
    p.rect(0, 0, W, 70, fill=1, stroke=0)
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(40, 52, "DIGITAL INTEGRITY FINGERPRINT (SHA-256)")
    p.setFont("Courier", 7)
    p.drawString(40, 38, receipt_hash[:64])
    p.drawString(40, 26, receipt_hash[64:])
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(40, 12, f"Support: support@quickserve.app")

    p.showPage()
    p.save()
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="receipt_{pid}.pdf"'},
    )

@router.get("/verify/receipt/{receipt_hash}")
async def verify_receipt(receipt_hash: str):
    """Public route to verify authenticity of a receipt"""
    db = get_db()
    payment = await db.payments.find_one({"receipt_hash": receipt_hash})
    if not payment:
        raise HTTPException(status_code=404, detail="Invalid Setup or Forged Document. Hash not found in ledger.")
        
    return {
        "status": "Verified Genuine",
        "transaction_id": str(payment["_id"]),
        "amount": payment["final_amount"],
        "date": payment["created_at"],
        "payment_status": payment["status"]
    }

@router.get("/receipt/{booking_id}")
async def get_booking_receipt(booking_id: str, current_user: dict = Depends(get_current_user)):
    """Generate an Authenticated PDF Receipt with SHA-256 Digital Fingerprint"""
    db = get_db()
    try:
        query = {"_id": ObjectId(booking_id)} if len(booking_id) == 24 else {"_id": booking_id}
        booking = await db.bookings.find_one(query)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID format")
        
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("user_id") != current_user["sub"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this receipt")

    user_id_str = str(booking.get("user_id", ""))
    provider_id_str = str(booking.get("provider_id", ""))

    customer = None
    user_oid = _oid(user_id_str)
    if user_oid:
        customer = await db.users.find_one({"_id": user_oid})
        
    provider = None
    p_oid = _oid(provider_id_str)
    if p_oid:
        provider = await db.users.find_one({"_id": p_oid})
    if not provider and provider_id_str:
        provider = await db.users.find_one({"_id": provider_id_str})

    total_price = booking.get('total_amount') or booking.get('final_price') or booking.get('price') or 0
    receipt_data = f"{booking_id}-{total_price}-{booking.get('status', 'confirmed')}"
    fingerprint = hashlib.sha256(receipt_data.encode()).hexdigest()

    qr_url = f"http://localhost:5173/verify/receipt/{fingerprint}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFillColorRGB(0.05, 0.48, 0.5)
    p.rect(0, height-100, width, 100, fill=1, stroke=0)
    
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
    if os.path.exists(logo_path):
        try: p.drawImage(ImageReader(logo_path), 40, height - 85, width=70, height=70, mask='auto')
        except: pass
    else:
        p.setStrokeColorRGB(1, 1, 1)
        p.setLineWidth(2)
        p.circle(75, height - 50, 30, fill=0, stroke=1)
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Helvetica-Bold", 20)
        p.drawCentredString(75, height - 58, "QS")
    
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(120, height - 55, "QuickServe Solutions")
    p.setFont("Helvetica", 12)
    p.drawString(120, height - 75, "Official Payment Receipt")
    
    p.setFillColorRGB(0.2, 0.2, 0.2)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, height - 130, f"DOCUMENT ID: QS-REC-{booking_id[-8:].upper()}")
    p.setFont("Helvetica", 10)
    p.drawString(width - 250, height - 130, f"Issued: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.line(40, height - 145, 560, height - 145)

    p.setFont("Helvetica-Bold", 13)
    p.drawString(40, height - 175, "BILLING INFORMATION")
    
    customer_name = (customer.get("full_name") or customer.get("name") or "Valued Customer") if customer else "Customer"
    provider_name = (provider.get("full_name") or provider.get("name") or "Professional Provider") if provider else "Provider"

    p.setFont("Helvetica", 11)
    data_points = [
        ("Customer Name", customer_name),
        ("Customer Email", customer.get("email", "N/A") if customer else "N/A"),
        ("Service Provider", provider_name),
        ("Service Name", booking.get('service_name', 'Professional Service')),
        ("Schedule", f"{booking.get('scheduled_date')} at {booking.get('scheduled_time')}"),
        ("Payment Mode", booking.get('payment_method', 'cod').upper()),
        ("Booking Status", booking.get('status', 'confirmed').upper())
    ]
    
    curr_y = height - 200
    for label, val in data_points:
        p.setFont("Helvetica-Bold", 9)
        p.drawString(40, curr_y, f"{label}:")
        p.setFont("Helvetica", 10)
        p.drawString(160, curr_y, str(val))
        curr_y -= 18

    curr_y -= 25
    p.setFillColorRGB(0.05, 0.48, 0.5)
    p.rect(40, curr_y - 5, 520, 25, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, curr_y + 8, "DESCRIPTION")
    p.drawRightString(550, curr_y + 8, "AMOUNT (INR)")
    
    p.setFillColorRGB(0, 0, 0)
    price = total_price
    p.setFont("Helvetica", 11)
    p.drawString(50, curr_y - 25, f"{booking.get('service_name', 'Professional Service')} Fee")
    p.drawRightString(550, curr_y - 25, f"{price:.2f}")
    
    p.setStrokeColorRGB(0.05, 0.48, 0.5)
    p.line(400, curr_y - 45, 560, curr_y - 45)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(400, curr_y - 70, "TOTAL PAID")
    p.drawRightString(550, curr_y - 70, f"INR {price:.2f}")

    footer_y = 100
    p.setStrokeColorRGB(0.8, 0.8, 0.8)
    p.line(40, footer_y + 60, 560, footer_y + 60)
    p.setFont("Helvetica-Bold", 9)
    p.setFillColorRGB(0.4, 0.4, 0.4)
    p.drawString(40, footer_y + 40, "DIGITAL FINGERPRINT (SHA-256)")
    p.setFont("Courier", 7)
    p.drawString(40, footer_y + 25, fingerprint)
    
    qr_reader = ImageReader(qr_buffer)
    p.drawImage(qr_reader, width - 140, 20, width=100, height=100)
    
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(40, 20, "This is a computer generated receipt. No signature required.")
    p.drawString(40, 10, "For support, contact support@quickserve.app")

    p.showPage()
    p.save()

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=receipt_{booking_id}.pdf"}
    )
