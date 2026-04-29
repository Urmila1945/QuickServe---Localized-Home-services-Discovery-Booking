from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from bson import ObjectId
from database.connection import get_db
from middleware.auth import get_current_user
import random
import uuid

router = APIRouter(tags=["Dashboards & Administration"])

# --- CUSTOMER DASHBOARD ---

@router.get("/dashboard/customer")
async def get_customer_dashboard(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["sub"]
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")

    # Support both user_id and customer_id fields in bookings for compatibility
    booking_query = {"$or": [{"user_id": user_id}, {"customer_id": user_id}]}
    total_bookings = await db.bookings.count_documents(booking_query)
    active_bookings = await db.bookings.count_documents({"$or": [{"user_id": user_id}, {"customer_id": user_id}], "status": {"$in": ["confirmed", "in_progress", "pending"]}})
    recent = await db.bookings.find(booking_query).sort("created_at", -1).limit(5).to_list(length=5)
    for b in recent:
        b["_id"] = str(b["_id"])

    # Loyalty points from both user credits and loyalty_points collection
    loyalty_data = await db.loyalty_points.find_one({"user_id": user_id})
    loyalty_points = user.get("quickserve_credits", 0) + (loyalty_data.get("points", 0) if loyalty_data else 0)

    # Total money saved (sum of discount_amount from payments)
    savings_pipe = await db.payments.aggregate([
        {"$match": {"user_id": user_id, "status": "completed"}},
        {"$group": {"_id": None, "saved": {"$sum": "$discount_amount"}}}
    ]).to_list(length=1)
    total_saved = round(savings_pipe[0]["saved"], 2) if savings_pipe else 0

    return {
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "loyalty_points": loyalty_points,
        "total_saved": total_saved,
        "recent_bookings": recent,
        "user_name": user.get("full_name", ""),
        "email": user.get("email", ""),
    }

# --- PROVIDER DASHBOARD ---

@router.get("/dashboard/provider")
async def get_provider_dashboard(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    user = await db.users.find_one({"_id": ObjectId(provider_id)})
    pending = await db.bookings.find({"provider_id": provider_id, "status": "pending"}).to_list(length=10)
    for p in pending: p["_id"] = str(p["_id"])
    return {"completed_bookings": await db.bookings.count_documents({"provider_id": provider_id, "status": "completed"}), "pending_bookings": len(pending), "average_rating": user.get("rating", 0), "total_earnings": user.get("balance", 0), "quickserve_score": user.get("quickserve_score", 0), "pending_requests": pending}

# --- ADMIN DASHBOARD ---

@router.get("/dashboard/admin")
async def get_admin_dashboard(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Admin only")
    db = get_db()
    return {"total_users": await db.users.count_documents({"role": "customer"}), "total_providers": await db.users.count_documents({"role": "provider"}), "total_revenue": sum([p.get("amount", 0) for p in await db.payments.find({"status": "completed"}).to_list(length=1000)]), "today_bookings": await db.bookings.count_documents({"created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)}}), "active_services": await db.services.count_documents({"is_available": True})}

@router.get("/dashboard/admin/users")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    db = get_db()
    users = await db.users.find({}).to_list(length=1000)
    for u in users:
        u["_id"] = str(u["_id"])
        u.pop("password", None)
    return users

# --- ANALYTICS & SUBSCRIPTIONS ---

@router.get("/dashboard/provider/analytics")
async def get_provider_analytics(current_user: dict = Depends(get_current_user)):
    return {"reach": random.randint(100, 500), "profile_views": random.randint(50, 200), "booking_rate": 0.15, "trendingScore": random.randint(70, 95)}

@router.get("/dashboard/provider/subscription")
async def get_subscription_status(current_user: dict = Depends(get_current_user)):
    return {"plan": "Premium Pro", "status": "active", "expires_at": (datetime.utcnow() + timedelta(days=25)).isoformat(), "features": ["Higher priority matching", "Unlimited skills", "Smart response bot"]}
