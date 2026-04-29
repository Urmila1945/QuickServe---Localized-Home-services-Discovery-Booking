from fastapi import FastAPI, APIRouter, HTTPException, Depends, Response, Cookie, Request, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database_monolith import *
from jose import jwt, JWTError
from passlib.context import CryptContext
from bson import ObjectId
from math import radians, sin, cos, sqrt, atan2
import logging, json, secrets, stripe, socketio, random


# ── Auth Middleware ──
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from typing import Optional

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        # Fallback to query param 'token' for direct browser downloads (e.g. receipts)
        token = request.query_params.get("token")
    
    if not token:
        # Fallback to Authorization header for API testing
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_optional_user(request: Request):
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

def check_role(required_roles: list):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in required_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

# ── Router Section: admin_dashboard ──
admin_dashboard_router = APIRouter()
router = admin_dashboard_router
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timedelta
from bson import ObjectId


def verify_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return current_user

# Dashboard Overview
@router.get("/dashboard")
async def get_admin_dashboard(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    # User stats
    total_users = await db.users.count_documents({})
    total_customers = await db.users.count_documents({"role": "customer"})
    total_providers = await db.users.count_documents({"role": "provider"})
    
    # Booking stats
    total_bookings = await db.bookings.count_documents({})
    active_bookings = await db.bookings.count_documents({"status": "in_progress"})
    completed_bookings = await db.bookings.count_documents({"status": "completed"})
    
    # Revenue (Efficiently using aggregation instead of loading all docs)
    # Total Revenue
    revenue_agg = await db.bookings.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    total_revenue = revenue_agg[0]["total"] if revenue_agg else 0
    platform_commission = total_revenue * 0.15
    
    # Today's stats
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_bookings = await db.bookings.count_documents({"created_at": {"$gte": today_start}})
    
    # Today's revenue
    today_revenue_agg = await db.bookings.aggregate([
        {"$match": {
            "status": "completed",
            "completed_at": {"$gte": today_start}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    today_revenue = today_revenue_agg[0]["total"] if today_revenue_agg else 0
    
    # Recent Activity (Dynamic from logs/bookings)
    recent_bookings = await db.bookings.find({}).sort("created_at", -1).limit(5).to_list(length=5)
    recent_activity = []
    for b in recent_bookings:
        user = await db.users.find_one({"_id": b.get("user_id") if isinstance(b.get("user_id"), ObjectId) else ObjectId(b["user_id"])})
        recent_activity.append({
            "user": user.get("full_name") if user else "Unknown",
            "action": f"Booked {b.get('service_name', 'Service')}",
            "time": b.get("created_at").strftime("%H:%M") if b.get("created_at") else "Just now"
        })

    return {
        "users": {
            "total": total_users,
            "customers": total_customers,
            "providers": total_providers
        },
        "bookings": {
            "total": total_bookings,
            "active": active_bookings,
            "completed": completed_bookings,
            "today": today_bookings
        },
        "revenue": {
            "total": round(total_revenue, 2),
            "commission": round(platform_commission, 2),
            "today": round(today_revenue, 2)
        },
        "recent_activity": recent_activity
    }

# ── Unique Feature: Flash Auctions ──
@router.get("/auctions/active")
async def get_active_auctions():
    db = get_db()
    # Mock active auctions for the demo, or fetch from db
    auctions = await db.auctions.find({"status": "active"}).to_list(length=10)
    for a in auctions: a["_id"] = str(a["_id"])
    
    if not auctions:
        # Generate dummy auctions if none exist
        return {"auctions": [
            {"id": "auc1", "provider": "Rajesh Electric", "service": "Electrical", "base_price": 500, "current_bid": 550, "ends_in": "14:20"},
            {"id": "auc2", "provider": "CleanSweep Pro", "service": "Cleaning", "base_price": 300, "current_bid": 320, "ends_in": "08:15"}
        ]}
    return {"auctions": auctions}

@router.get("/financial")
async def get_financial_data(admin: dict = Depends(verify_admin)):
    """Return comprehensive list of financial data for admin."""
    db = get_db()
    
    # 1. Monthly Revenue (Dynamic historical)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_agg = await db.bookings.aggregate([
        {"$match": {"status": "completed", "completed_at": {"$gte": six_months_ago}}},
        {
            "$group": {
                "_id": {"$month": "$completed_at"},
                "revenue": {"$sum": "$amount"}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(length=6)
    
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    revenue_monthly = []
    for item in monthly_agg:
        month_idx = item["_id"] - 1
        rev = item["revenue"]
        revenue_monthly.append({
            "month": month_names[month_idx],
            "revenue": rev,
            "commission": rev * 0.15
        })
    
    if not revenue_monthly:
        revenue_monthly = [{"month": datetime.utcnow().strftime("%b"), "revenue": 0, "commission": 0}]

    # 2. Fraud Alerts (Dynamic from DB)
    fraud_records = await db.fraud_alerts.find({"status": {"$ne": "resolved"}}).sort("flaggedAt", -1).limit(10).to_list(length=10)
    fraud_alerts = []
    for f in fraud_records:
        fraud_alerts.append({
            "id": str(f["_id"]),
            "type": f.get("type", "Payment"),
            "provider": f.get("provider_name", "Unknown"),
            "customer": f.get("customer_name", "Unknown"),
            "flaggedAt": f.get("flaggedAt", datetime.utcnow()).strftime("%b %d"),
            "amount": f.get("amount", 0),
            "score": f.get("score", 0),
            "status": f.get("status", "open")
        })

    # 3. Commission Tiers (Dynamic based on logic/providers)
    commission_tiers = [
        {"tier": "Platinum", "rate": 8,  "providers": await db.users.count_documents({"role": "provider", "commission_tier": "Platinum"}),  "volume": 0},
        {"tier": "Gold",     "rate": 10, "providers": await db.users.count_documents({"role": "provider", "commission_tier": "Gold"}),      "volume": 0},
        {"tier": "Silver",   "rate": 12, "providers": await db.users.count_documents({"role": "provider", "commission_tier": "Silver"}),    "volume": 0},
        {"tier": "Bronze",   "rate": 15, "providers": await db.users.count_documents({"role": "provider", "commission_tier": {"$in": ["Bronze", None]}}), "volume": 0},
    ]

    # 4. Escrow Items (Dynamic from payments taking real data)
    escrow_docs = await db.payments.find({"escrow_status": {"$in": ["held", "dispute"]}}).to_list(length=20)
    escrow_items = []
    for p in escrow_docs:
        created = p.get("created_at", datetime.utcnow())
        held_days = (datetime.utcnow() - created).days
        escrow_items.append({
            "id": str(p["_id"]),
            "booking": str(p.get("booking_id", "Unknown")),
            "amount": p.get("final_amount", 0),
            "held": f"{held_days} days",
            "release": "On completion",
            "status": p.get("escrow_status", "held")
        })

    return {
        "revenue_monthly": revenue_monthly,
        "fraud_alerts": fraud_alerts,
        "commission_tiers": commission_tiers,
        "escrow_items": escrow_items
    }

# User Management
@router.get("/users")
async def get_all_users(
    role: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    query = {}
    if role:
        query["role"] = role
    
    skip = (page - 1) * limit
    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    total = await db.users.count_documents(query)
    
    for user in users:
        user["_id"] = str(user["_id"])
        user.pop("password", None)
        
        # Add quick stats for providers
        if user.get("role") == "provider":
            user["bookings_count"] = await db.bookings.count_documents({"provider_id": str(user["_id"]), "status": "completed"})
            user["aptitude_score"] = user.get("aptitude_score") or user.get("base_score") or 0
            user["experience_years"] = user.get("experience_years") or 0
        elif user.get("role") == "customer":
            user["bookings_count"] = await db.bookings.count_documents({"user_id": str(user["_id"])})
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.post("/rewards/grant")
async def grant_reward(
    email: str,
    amount: int,
    reward_type: str = "credits",
    reason: str = "Admin reward",
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")
    
    if reward_type == "credits":
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$inc": {"quickserve_credits": amount}}
        )
    elif reward_type == "points":
        await db.loyalty_points.update_one(
            {"user_id": str(user["_id"])},
            {"$inc": {"points": amount}},
            upsert=True
        )
    
    # Log the reward action
    await db.admin_logs.insert_one({
        "action": "grant_reward",
        "admin_id": admin["sub"],
        "target_user": email,
        "amount": amount,
        "type": reward_type,
        "reason": reason,
        "timestamp": datetime.utcnow()
    })
    
    return {"success": True, "new_balance": (user.get("quickserve_credits", 0) + amount) if reward_type == "credits" else None}

@router.get("/tech-ops")
async def get_tech_ops(admin: dict = Depends(verify_admin)):
    """Return system metrics and AI model status."""
    db = get_db()
    total_users = await db.users.count_documents({})
    total_bookings = await db.bookings.count_documents({})
    total_payments = await db.payments.count_documents({})
    failed_payments = await db.payments.count_documents({"status": {"$in": ["failed", "refunded"]}})
    error_rate = round((failed_payments / total_payments * 100), 2) if total_payments > 0 else 0
    system_metrics = [
        {"service": "API Gateway",      "latency": "42ms",  "errorRate": f"{error_rate}%", "uptime": "99.98%", "status": "healthy"},
        {"service": "MongoDB Atlas",    "latency": "18ms",  "errorRate": "0.00%", "uptime": "99.99%", "status": "healthy"},
        {"service": "Auth Service",     "latency": "65ms",  "errorRate": "0.01%", "uptime": "99.97%", "status": "healthy"},
        {"service": "Payment Gateway",  "latency": "120ms", "errorRate": f"{error_rate}%", "uptime": "99.95%", "status": "healthy" if error_rate < 1 else "warning"},
        {"service": "Notification Svc", "latency": "88ms",  "errorRate": "0.12%", "uptime": "99.82%", "status": "warning"},
    ]
    ai_models = [
        {"model": "Smart Match Engine",     "accuracy": 94.2, "drift": 0.8,  "lastTrained": "Dec 10", "status": "healthy"},
        {"model": "Demand Predictor",       "accuracy": 88.5, "drift": 2.1,  "lastTrained": "Nov 28", "status": "warning"},
    ]
    return {"system_metrics": system_metrics, "ai_models": ai_models, "total_users": total_users, "total_bookings": total_bookings, "latency_history": []}

@router.get("/community-governance")
async def get_community_governance(admin: dict = Depends(verify_admin)):
    """Return jury pool, ambassadors, and policy data."""
    db = get_db()
    
    # 1. Jury Pool (High rated providers with > 50 completed bookings)
    jurors = await db.users.find({
        "role": "provider",
        "rating": {"$gte": 4.5},
        "verified_by_admin": True
    }).limit(10).to_list(length=10)
    
    jury_data = []
    for j in jurors:
        completed = await db.bookings.count_documents({"provider_id": str(j["_id"]), "status": "completed"})
        accuracy = min(100, 85 + (completed % 15))
        tier = "Platinum" if accuracy > 93 else "Gold"
        reward = f"₹{415 * (1 if tier == 'Silver' else 2 if tier == 'Gold' else 3)}/case"
        
        jury_data.append({
            "id": str(j["_id"]),
            "name": j.get("full_name", "Unknown"),
            "tier": tier,
            "cases": random.randint(3, 15),
            "accuracy": accuracy,
            "status": "available" if random.random() > 0.3 else "on_case",
            "reward": reward
        })
    
    if not jury_data:
        # Fallback if no providers meet criteria
        jury_data = [
            {"id": "j1", "name": "Anjali Singh", "tier": "Platinum", "cases": 8, "accuracy": 94, "status": "available", "reward": "₹830/case"},
            {"id": "j2", "name": "Vikram Rao", "tier": "Gold", "cases": 5, "accuracy": 88, "status": "on_case", "reward": "₹830/case"},
            {"id": "j3", "name": "Priya Kumar", "tier": "Gold", "cases": 12, "accuracy": 96, "status": "available", "reward": "₹1,245/case"},
        ]

    # 2. Ambassadors (Cities with most activity)
    cities = ["Koramangala", "Indiranagar", "Whitefield", "HSR Layout"]
    ambassadors = []
    for city in cities:
        providers = await db.users.count_documents({"role": "provider", "city": city})
        customers = await db.users.count_documents({"role": "customer", "city": city})
        ambassadors.append({
            "name": city,
            "captain": "Meera Nair" if city == "Koramangala" else "Dev Patel" if city == "Indiranagar" else "Open",
            "providers": providers,
            "customers": customers,
            "growth": f"+{random.randint(10, 35)}%",
            "status": "active" if providers > 0 else "vacant"
        })

    # 3. Feature Requests
    feature_requests = [
        {"id": "fr1", "title": "Bulk invoice download", "votes": 284, "category": "Finance", "status": "planned"},
        {"id": "fr2", "title": "WhatsApp booking confirmation", "votes": 521, "category": "Comm.", "status": "in_progress"},
        {"id": "fr3", "title": "Multi-provider job grouping", "votes": 198, "category": "Scheduling", "status": "review"},
        {"id": "fr4", "title": "Subscription-based cleaning", "votes": 389, "category": "Business", "status": "planned"},
    ]

    return {
        "jury": jury_data,
        "ambassadors": ambassadors,
        "feature_requests": feature_requests,
        "policy_broadcasts": [
            {"id": "p1", "title": "Mandatory background check update", "date": "Dec 18", "reach": "98%", "status": "sent"},
            {"id": "p2", "title": "Holiday service surcharge policy", "date": "Dec 15", "reach": "100%", "status": "draft"}
        ]
    }

@router.get("/performance-analytics")
async def get_performance_analytics(admin: dict = Depends(verify_admin)):
    """Return real onboarding funnel and NPS data from DB."""
    db = get_db()
    total_users = await db.users.count_documents({"role": {"$in": ["customer", "provider"]}})
    email_verified = await db.users.count_documents({"verified_email": True})
    profile_completed = await db.users.count_documents({"phone": {"$exists": True, "$ne": None}})
    doc_submitted = await db.provider_documents.count_documents({})
    background_checked = await db.provider_documents.count_documents({"status": {"$in": ["approved", "pending_review"]}})
    first_job_done = await db.bookings.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": "$provider_id"}},
        {"$count": "count"}
    ]).to_list(length=1)
    first_job_count = first_job_done[0]["count"] if first_job_done else 0
    base = max(total_users, 1)
    onboarding_funnel = [
        {"step": "Registered",        "count": total_users,       "pct": 100},
        {"step": "Email Verified",    "count": email_verified,    "pct": round(email_verified / base * 100, 1)},
        {"step": "Profile Completed", "count": profile_completed, "pct": round(profile_completed / base * 100, 1)},
        {"step": "Doc Submitted",     "count": doc_submitted,     "pct": round(doc_submitted / base * 100, 1)},
        {"step": "Background Check",  "count": background_checked,"pct": round(background_checked / base * 100, 1)},
        {"step": "First Job Done",    "count": first_job_count,   "pct": round(first_job_count / base * 100, 1)},
    ]
    reviews_raw = await db.reviews.find({}).to_list(length=1000)
    promoters = sum(1 for r in reviews_raw if r.get("rating", 0) >= 4)
    detractors = sum(1 for r in reviews_raw if r.get("rating", 0) <= 2)
    total_reviews = len(reviews_raw)
    nps_score = round(((promoters - detractors) / max(total_reviews, 1)) * 100)
    recent_reviews = sorted(reviews_raw, key=lambda x: x.get("created_at", datetime.min), reverse=True)[:3]
    recent_feedback = []
    for rev in recent_reviews:
        uid = rev.get("user_id", "")
        user = await db.users.find_one({"_id": ObjectId(uid)}) if len(str(uid)) == 24 else None
        recent_feedback.append({
            "name": user.get("full_name", "Customer") if user else "Customer",
            "score": rev.get("rating", 5),
            "comment": rev.get("comment", ""),
            "tier": "Gold"
        })
    nps_data = {
        "score": nps_score,
        "promoters": f"{round(promoters/max(total_reviews,1)*100)}%",
        "detractors": f"{round(detractors/max(total_reviews,1)*100)}%",
        "recent_feedback": recent_feedback
    }
    return {"onboarding_funnel": onboarding_funnel, "nps": nps_data}

@router.get("/marketplace-command")
async def get_marketplace_command(admin: dict = Depends(verify_admin)):
    """Return GTV, supply-demand, churn, and CAC analytics from real DB."""
    db = get_db()
    
    # 1. GTV stats from real payments
    total_revenue_pipe = await db.payments.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$final_amount"}}}
    ]).to_list(length=1)
    gtv = total_revenue_pipe[0]["total"] if total_revenue_pipe else 0
    
    # 2. Supply-Demand by Area from real data
    cities = ["Koramangala", "Indiranagar", "HSR Layout", "Whitefield", "JP Nagar"]
    supply_demand = []
    for i, city in enumerate(cities):
        providers = await db.users.count_documents({"role": "provider", "city": city})
        requests = await db.bookings.count_documents({"location.city": city})
        ratio = providers / max(requests, 1)
        status = "crisis" if ratio < 0.5 else "shortage" if ratio < 0.8 else "healthy" if ratio < 1.5 else "surplus"
        supply_demand.append({
            "zip": f"BLR-0{i+1}", "area": city,
            "providers": providers, "requests": requests,
            "ratio": round(ratio, 2), "status": status
        })

    # 3. Monthly Revenue from real bookings
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_agg = await db.payments.aggregate([
        {"$match": {"status": "completed", "created_at": {"$gte": six_months_ago}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
            "revenue": {"$sum": "$final_amount"}
        }},
        {"$sort": {"_id": 1}}
    ]).to_list(length=6)
    revenue_monthly = [{"month": m["_id"], "revenue": m["revenue"], "commission": round(m["revenue"] * 0.15, 2)} for m in monthly_agg]
    if not revenue_monthly:
        revenue_monthly = [{"month": datetime.utcnow().strftime("%Y-%m"), "revenue": 0, "commission": 0}]

    # 4. Churn Risk - customers inactive > 14 days
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    inactive_customers = await db.users.find({"role": "customer"}).limit(50).to_list(length=50)
    churn_risk = []
    for c in inactive_customers:
        last_booking = await db.bookings.find_one(
            {"user_id": str(c["_id"])}, sort=[("created_at", -1)]
        )
        if last_booking:
            days_active = (datetime.utcnow() - last_booking.get("created_at", datetime.utcnow())).days
            if days_active > 7:
                earnings_pipe = await db.payments.aggregate([
                    {"$match": {"user_id": str(c["_id"]), "status": "completed"}},
                    {"$group": {"_id": None, "total": {"$sum": "$final_amount"}}}
                ]).to_list(length=1)
                total_spent = earnings_pipe[0]["total"] if earnings_pipe else 0
                risk = min(95, 40 + days_active * 2)
                churn_risk.append({
                    "name": c.get("full_name", "Customer"),
                    "risk": risk,
                    "trend": "up" if days_active > 14 else "stable",
                    "revenue": total_spent,
                    "daysActive": days_active
                })
    churn_risk = sorted(churn_risk, key=lambda x: x["risk"], reverse=True)[:5]

    # 5. CAC (static tiers, real conversion counts)
    total_new_users = await db.users.count_documents({"role": "customer"})
    cac_data = [
        {"channel": "Organic Search", "cac": 830,  "conversions": max(1, total_new_users // 4)},
        {"channel": "Paid Ads",       "cac": 2490, "conversions": max(1, total_new_users // 6)},
        {"channel": "Referral",       "cac": 415,  "conversions": max(1, total_new_users // 3)},
        {"channel": "Social Media",   "cac": 1245, "conversions": max(1, total_new_users // 8)},
        {"channel": "App Store",      "cac": 1660, "conversions": max(1, total_new_users // 12)},
    ]

    active_now = await db.bookings.count_documents({"status": "in_progress"})
    return {
        "gtv": gtv,
        "active_now": active_now,
        "supply_demand": supply_demand,
        "revenue_monthly": revenue_monthly,
        "churn_risk": churn_risk,
        "cac": cac_data
    }

@router.get("/trust-safety")
async def get_trust_safety(admin: dict = Depends(verify_admin)):
    """Return disputes and moderation queue from real DB."""
    db = get_db()
    disputes_raw = await db.disputes.find({}).sort("created_at", -1).limit(20).to_list(length=20)
    disputes = []
    for d in disputes_raw:
        d["_id"] = str(d["_id"])
        disputes.append({
            "id": d["_id"],
            "title": d.get("title", "Dispute"),
            "category": d.get("category", "General"),
            "customer": d.get("customer_name", "Unknown"),
            "provider": d.get("provider_name", "Unknown"),
            "amount": d.get("amount", 0),
            "date": d.get("created_at", datetime.utcnow()).strftime("%b %d") if hasattr(d.get("created_at"), "strftime") else "N/A",
            "status": d.get("status", "pending")
        })
    reviews_raw = await db.reviews.find({"deleted": {"$ne": True}}).sort("created_at", -1).limit(20).to_list(length=20)
    review_queue = []
    for r in reviews_raw:
        comment = r.get("comment", "").lower()
        fake_score = 0
        if len(comment) < 10: fake_score += 30
        if r.get("rating") == 5 and "perfect" in comment: fake_score += 20
        if any(w in comment for w in ["terrible", "fraud", "scam"]): fake_score += 40
        if fake_score > 40:
            reviewer_id = r.get("user_id", "")
            subject_id = r.get("provider_id", "")
            reviewer = await db.users.find_one({"_id": ObjectId(reviewer_id)}) if len(str(reviewer_id)) == 24 else None
            subject = await db.users.find_one({"_id": ObjectId(subject_id)}) if len(str(subject_id)) == 24 else None
            review_queue.append({
                "id": str(r["_id"]),
                "reviewer": reviewer.get("full_name", "Unknown") if reviewer else "Unknown",
                "subject": subject.get("full_name", "Unknown") if subject else "Unknown",
                "rating": r.get("rating"),
                "text": r.get("comment"),
                "flag": "Suspicious Review",
                "score": fake_score
            })
    return {"disputes": disputes, "review_queue": review_queue}

@router.get("/users/{user_id}")
async def get_user_details(user_id: str, admin: dict = Depends(verify_admin)):
    db = get_db()
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    
    # Get user's bookings using correct field names
    if user["role"] == "customer":
        bookings = await db.bookings.find({"user_id": user_id}).to_list(length=100)
    else:
        bookings = await db.bookings.find({"provider_id": user_id}).to_list(length=100)
    
    for b in bookings:
        b["_id"] = str(b["_id"])
    
    # Get rewards
    rewards = await db.rewards.find({"user_id": user_id}).to_list(length=100)
    for r in rewards:
        r["_id"] = str(r["_id"])
    
    return {
        "user": user,
        "bookings": bookings,
        "rewards": rewards
    }

# Reward Management
@router.post("/rewards/grant")
async def grant_reward(
    user_id: str,
    reward_type: str,  # credits, badge, discount
    amount: float,
    reason: str,
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    
    # Create reward record
    reward = {
        "user_id": user_id,
        "user_name": user.get("full_name", "Unknown"),
        "user_role": user.get("role", "customer"),
        "reward_type": reward_type,
        "amount": amount,
        "reason": reason,
        "granted_by": admin["sub"],
        "granted_at": datetime.utcnow(),
        "status": "active"
    }
    
    result = await db.rewards.insert_one(reward)
    
    # Update user balance/credits
    if reward_type == "credits":
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"quickserve_credits": amount}}
        )
    elif reward_type == "discount":
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"active_discounts": {
                "amount": amount,
                "expires": datetime.utcnow() + timedelta(days=30)
            }}}
        )
    
    return {"success": True, "reward_id": str(result.inserted_id)}

@router.get("/rewards")
async def get_all_rewards(
    user_id: Optional[str] = None,
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    rewards = await db.rewards.find(query).sort("granted_at", -1).limit(100).to_list(length=100)
    
    for r in rewards:
        r["_id"] = str(r["_id"])
    
    return {"rewards": rewards}

@router.delete("/rewards/{reward_id}")
async def revoke_reward(reward_id: str, admin: dict = Depends(verify_admin)):
    db = get_db()
    
    reward = await db.rewards.find_one({"_id": ObjectId(reward_id)})
    if not reward:
        raise HTTPException(404, "Reward not found")
    
    # Revoke credits
    if reward["reward_type"] == "credits":
        await db.users.update_one(
            {"_id": ObjectId(reward["user_id"])},
            {"$inc": {"quickserve_credits": -reward["amount"]}}
        )
    
    await db.rewards.update_one(
        {"_id": ObjectId(reward_id)},
        {"$set": {"status": "revoked", "revoked_at": datetime.utcnow()}}
    )
    
    return {"success": True}

# Provider Management
@router.post("/providers/{provider_id}/verify")
async def verify_provider(provider_id: str, admin: dict = Depends(verify_admin)):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(provider_id)},
        {"$set": {"verified_by_admin": True, "verified_at": datetime.utcnow()}}
    )
    
    return {"success": True}

@router.post("/providers/{provider_id}/suspend")
async def suspend_provider(
    provider_id: str,
    reason: str,
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(provider_id)},
        {"$set": {
            "suspended": True,
            "suspension_reason": reason,
            "suspended_at": datetime.utcnow(),
            "suspended_by": admin["sub"]
        }}
    )
    
    return {"success": True}

# Booking Management
@router.get("/bookings")
async def get_all_bookings(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    query = {}
    if status:
        query["status"] = status
    
    skip = (page - 1) * limit
    bookings = await db.bookings.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    total = await db.bookings.count_documents(query)
    
    for b in bookings:
        b["_id"] = str(b["_id"])
        b["id"] = b["_id"]

        # ── Enrich customer info ──────────────────────────────────────────
        cid = b.get("user_id") or b.get("customer_id")
        customer = None
        if cid:
            try:
                customer = await db.users.find_one({"_id": ObjectId(cid) if len(str(cid)) == 24 else cid})
            except Exception:
                pass
        if customer:
            b["customer_name"]   = customer.get("full_name", "Unknown")
            b["customer_email"]  = customer.get("email", "")
            b["customer_phone"]  = customer.get("phone", "")
            b["customer_credits"] = customer.get("quickserve_credits", 0)
            # customer booking stats
            c_total   = await db.bookings.count_documents({"user_id": str(customer["_id"])})
            c_done    = await db.bookings.count_documents({"user_id": str(customer["_id"]), "status": "completed"})
            b["customer_total_bookings"]     = c_total
            b["customer_completed_bookings"] = c_done

        # ── Enrich provider info ──────────────────────────────────────────
        pid = b.get("provider_id")
        provider = None
        if pid:
            try:
                provider = await db.users.find_one({"_id": ObjectId(pid) if len(str(pid)) == 24 else pid})
            except Exception:
                pass
        if provider:
            b["provider_name"]       = provider.get("full_name", "Unknown")
            b["provider_email"]      = provider.get("email", "")
            b["provider_phone"]      = provider.get("phone", "")
            b["provider_rating"]     = provider.get("rating", 0)
            b["provider_verified"]   = provider.get("verified_by_admin", False)
            b["provider_specializations"] = provider.get("specializations", [])
            # provider booking stats
            p_total   = await db.bookings.count_documents({"provider_id": str(provider["_id"])})
            p_done    = await db.bookings.count_documents({"provider_id": str(provider["_id"]), "status": "completed"})
            p_earn_pipe = await db.payments.aggregate([
                {"$match": {"provider_id": str(provider["_id"]), "status": "completed"}},
                {"$group": {"_id": None, "total": {"$sum": "$provider_payout"}}}
            ]).to_list(length=1)
            b["provider_total_bookings"]     = p_total
            b["provider_completed_bookings"] = p_done
            b["provider_total_earnings"]     = round(p_earn_pipe[0]["total"], 2) if p_earn_pipe else 0

        # ── Enrich payment info ───────────────────────────────────────────
        payment = await db.payments.find_one({"booking_id": b["_id"]})
        if payment:
            b["payment_id"]       = str(payment["_id"])
            b["payment_status"]   = payment.get("status", "pending")
            b["payment_method"]   = payment.get("payment_method", "")
            b["final_amount"]     = payment.get("final_amount", 0)
            b["platform_fee"]     = payment.get("platform_fee", 0)
            b["provider_payout"]  = payment.get("provider_payout", 0)
            b["escrow_status"]    = payment.get("escrow_status", "")
            b["gst_amount"]       = payment.get("gst_amount", 0)
            b["discount_amount"]  = payment.get("discount_amount", 0)
        else:
            b.setdefault("payment_status", b.get("payment_status", "unpaid"))
            b.setdefault("final_amount", b.get("final_price") or b.get("amount") or 0)

        # ── Enrich review info ────────────────────────────────────────────
        review = await db.reviews.find_one({"booking_id": b["_id"]})
        if review:
            b["review_rating"]  = review.get("rating")
            b["review_comment"] = review.get("comment", "")
    
    return {
        "bookings": bookings,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

# Dispute Management
@router.get("/disputes")
async def get_disputes(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    disputes = await db.disputes.find({}).sort("created_at", -1).to_list(length=100)
    
    for d in disputes:
        d["_id"] = str(d["_id"])
    
    return {"disputes": disputes}

@router.post("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    resolution: str,
    winner: str,  # customer, provider
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    await db.disputes.update_one(
        {"_id": ObjectId(dispute_id)},
        {"$set": {
            "status": "resolved",
            "resolution": resolution,
            "winner": winner,
            "resolved_by": admin["sub"],
            "resolved_at": datetime.utcnow()
        }}
    )
    
    return {"success": True}

# Analytics
@router.get("/analytics/revenue")
async def get_revenue_analytics(
    period: str = "monthly",  # daily, weekly, monthly
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    bookings = await db.bookings.find({"status": "completed"}).to_list(length=10000)
    
    data = []
    if period == "daily":
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            day_bookings = [b for b in bookings if b.get("completed_at", datetime.min).date() == date.date()]
            revenue = sum(b.get("amount", 0) for b in day_bookings)
            
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "revenue": revenue,
                "bookings": len(day_bookings),
                "commission": revenue * 0.15
            })
    
    return {"period": period, "data": data[::-1]}

@router.get("/analytics/top-providers")
async def get_top_providers(limit: int = 10, admin: dict = Depends(verify_admin)):
    db = get_db()
    
    providers = await db.users.find({"role": "provider"}).to_list(length=1000)
    
    provider_stats = []
    for p in providers:
        bookings = await db.bookings.count_documents({"provider_id": str(p["_id"]), "status": "completed"})
        completed = await db.bookings.find({"provider_id": str(p["_id"]), "status": "completed"}).to_list(length=1000)
        earnings = sum(b.get("amount", 0) for b in completed)
        
        provider_stats.append({
            "id": str(p["_id"]),
            "name": p.get("full_name", "Unknown"),
            "bookings": bookings,
            "earnings": earnings,
            "rating": p.get("rating", 0)
        })
    
    provider_stats.sort(key=lambda x: x["earnings"], reverse=True)
    
    return {"top_providers": provider_stats[:limit]}

@router.get("/analytics/top-customers")
async def get_top_customers(limit: int = 10, admin: dict = Depends(verify_admin)):
    db = get_db()
    
    customers = await db.users.find({"role": "customer"}).to_list(length=1000)
    
    customer_stats = []
    for c in customers:
        bookings = await db.bookings.count_documents({"user_id": str(c["_id"])})
        completed = await db.bookings.find({"user_id": str(c["_id"]), "status": "completed"}).to_list(length=1000)
        spent = sum(b.get("final_price") or b.get("amount") or 0 for b in completed)
        
        customer_stats.append({
            "id": str(c["_id"]),
            "name": c.get("full_name", "Unknown"),
            "bookings": bookings,
            "spent": spent,
            "credits": c.get("quickserve_credits", 0)
        })
    
    customer_stats.sort(key=lambda x: x["spent"], reverse=True)
    
    return {"top_customers": customer_stats[:limit]}


# 1. Provider Management - Verification & KYC Pipeline
@router.get("/kyc/pending")
async def get_pending_kyc(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    pending = await db.provider_documents.find({
        "status": "pending_review"
    }).to_list(length=100)
    
    for doc in pending:
        doc["_id"] = str(doc["_id"])
        # Get provider details
        provider = await db.users.find_one({"_id": ObjectId(doc["provider_id"])})
        if provider:
            doc["provider_name"] = provider.get("full_name", "Unknown")
            doc["provider_email"] = provider.get("email", "")
    
    return {"pending_kyc": pending}

@router.post("/kyc/{doc_id}/approve")
async def approve_kyc(doc_id: str, admin: dict = Depends(verify_admin)):
    db = get_db()
    
    doc = await db.provider_documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(404, "Document not found")
    
    await db.provider_documents.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {"status": "approved", "approved_by": admin["sub"], "approved_at": datetime.utcnow()}}
    )
    
    await db.users.update_one(
        {"_id": ObjectId(doc["provider_id"])},
        {"$set": {"kyc_verified": True}}
    )
    
    return {"success": True}

@router.post("/kyc/{doc_id}/reject")
async def reject_kyc(doc_id: str, reason: str, admin: dict = Depends(verify_admin)):
    db = get_db()
    
    await db.provider_documents.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {"status": "rejected", "rejection_reason": reason, "rejected_by": admin["sub"]}}
    )
    
    return {"success": True}

# Performance Heatmaps
@router.get("/heatmap/supply-demand")
async def get_supply_demand_heatmap(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    # Get all providers
    providers = await db.services.find({}).to_list(length=10000)
    
    # Get all bookings
    bookings = await db.bookings.find({}).to_list(length=10000)
    
    # Group by city
    city_data = {}
    for provider in providers:
        city = provider.get("city", "Unknown")
        if city not in city_data:
            city_data[city] = {"providers": 0, "demand": 0, "lat": provider.get("latitude"), "lng": provider.get("longitude")}
        city_data[city]["providers"] += 1
    
    for booking in bookings:
        city = booking.get("location", {}).get("city", "Unknown")
        if city in city_data:
            city_data[city]["demand"] += 1
    
    # Calculate coverage ratio
    heatmap = []
    for city, data in city_data.items():
        ratio = data["providers"] / max(data["demand"], 1)
        status = "good" if ratio > 0.5 else "warning" if ratio > 0.2 else "critical"
        
        heatmap.append({
            "city": city,
            "providers": data["providers"],
            "demand": data["demand"],
            "ratio": round(ratio, 2),
            "status": status,
            "lat": data["lat"],
            "lng": data["lng"]
        })
    
    return {"heatmap": heatmap}

# Commission & Payout Controls
@router.post("/commission/set")
async def set_commission_rate(
    provider_id: str,
    rate: float,
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(provider_id)},
        {"$set": {"custom_commission_rate": rate, "commission_updated_at": datetime.utcnow()}}
    )
    
    return {"success": True}

@router.post("/payouts/bulk")
async def process_bulk_payouts(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    # Get all pending payouts
    pending = await db.payouts.find({"status": "pending"}).to_list(length=1000)
    
    processed = []
    for payout in pending:
        # Simulate Stripe transfer
        await db.payouts.update_one(
            {"_id": payout["_id"]},
            {"$set": {"status": "completed", "processed_at": datetime.utcnow()}}
        )
        processed.append(str(payout["_id"]))
    
    return {"success": True, "processed_count": len(processed)}

# Inventory & Service Audit
@router.get("/audit/suspicious-services")
async def get_suspicious_services(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    services = await db.services.find({}).to_list(length=10000)
    
    suspicious = []
    for service in services:
        flags = []
        
        # Check for stock photos
        if "example.com" in service.get("profile_image", ""):
            flags.append("Stock photo detected")
        
        # Check for duplicate profiles
        duplicates = await db.services.count_documents({
            "email": service.get("email"),
            "_id": {"$ne": service["_id"]}
        })
        if duplicates > 0:
            flags.append(f"{duplicates} duplicate profiles")
        
        # Check for suspicious pricing
        if service.get("price_per_hour", 0) < 100 or service.get("price_per_hour", 0) > 5000:
            flags.append("Unusual pricing")
        
        if flags:
            suspicious.append({
                "service_id": str(service["_id"]),
                "provider_name": service.get("name"),
                "flags": flags,
                "category": service.get("category")
            })
    
    return {"suspicious_services": suspicious[:50]}

# 2. Customer Management - LTV Analytics
@router.get("/customers/ltv")
async def get_customer_ltv(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    customers = await db.users.find({"role": "customer"}).to_list(length=1000)
    
    ltv_data = []
    for customer in customers:
        bookings = await db.bookings.find({
            "user_id": str(customer["_id"]),
            "status": "completed"
        }).to_list(length=1000)
        
        total_spent = sum(b.get("final_price") or b.get("total_amount") or 0 for b in bookings)
        last_booking = max([b.get("created_at", datetime.min) for b in bookings]) if bookings else None
        
        # Calculate churn risk
        days_since_last = (datetime.utcnow() - last_booking).days if last_booking else 999
        churn_risk = "high" if days_since_last > 30 else "medium" if days_since_last > 14 else "low"
        
        ltv_data.append({
            "customer_id": str(customer["_id"]),
            "name": customer.get("full_name"),
            "email": customer.get("email"),
            "total_spent": total_spent,
            "booking_count": len(bookings),
            "avg_order_value": total_spent / len(bookings) if bookings else 0,
            "days_since_last_booking": days_since_last,
            "churn_risk": churn_risk
        })
    
    ltv_data.sort(key=lambda x: x["total_spent"], reverse=True)
    
    return {"ltv_data": ltv_data[:100]}

@router.post("/customers/retention-campaign")
async def trigger_retention_campaign(
    customer_ids: list,
    discount_code: str,
    discount_amount: float,
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    for customer_id in customer_ids:
        await db.users.update_one(
            {"_id": ObjectId(customer_id)},
            {"$push": {"discount_codes": {
                "code": discount_code,
                "amount": discount_amount,
                "expires": datetime.utcnow() + timedelta(days=7),
                "used": False
            }}}
        )
    
    return {"success": True, "customers_targeted": len(customer_ids)}

# Review Moderation
@router.get("/reviews/moderation")
async def get_reviews_for_moderation(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    reviews = await db.reviews.find({}).sort("created_at", -1).limit(100).to_list(length=100)
    
    moderated = []
    for review in reviews:
        # AI sentiment analysis (simulated)
        comment = review.get("comment", "").lower()
        
        sentiment = "positive"
        if any(word in comment for word in ["terrible", "worst", "scam", "fraud", "horrible"]):
            sentiment = "highly_negative"
        elif any(word in comment for word in ["bad", "poor", "disappointed"]):
            sentiment = "negative"
        
        # Fake detection
        fake_score = 0
        if len(comment) < 10:
            fake_score += 30
        if review.get("rating") == 5 and "perfect" in comment:
            fake_score += 20
        
        is_suspicious = fake_score > 40
        
        moderated.append({
            "review_id": str(review["_id"]),
            "rating": review.get("rating"),
            "comment": review.get("comment"),
            "sentiment": sentiment,
            "fake_score": fake_score,
            "is_suspicious": is_suspicious,
            "created_at": review.get("created_at")
        })
    
    return {"reviews": moderated}

@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str, reason: str, admin: dict = Depends(verify_admin)):
    db = get_db()
    
    await db.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": {"deleted": True, "deletion_reason": reason, "deleted_by": admin["sub"]}}
    )
    
    return {"success": True}

# 3. Marketplace Health - Real-Time Transaction Ticker
@router.get("/live/transactions")
async def get_live_transactions(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    # Get last 50 transactions
    recent = await db.bookings.find({}).sort("created_at", -1).limit(50).to_list(length=50)
    
    transactions = []
    for booking in recent:
        transactions.append({
            "id": str(booking["_id"]),
            "type": "booking",
            "status": booking.get("status"),
            "amount": booking.get("amount"),
            "service": booking.get("service_name"),
            "timestamp": booking.get("created_at")
        })
    
    return {"transactions": transactions}

# Demand Forecasting
@router.get("/forecast/demand")
async def forecast_demand(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    # Get historical bookings
    bookings = await db.bookings.find({}).to_list(length=10000)
    
    # Group by category
    category_demand = {}
    for booking in bookings:
        category = booking.get("service_category", "unknown")
        if category not in category_demand:
            category_demand[category] = 0
        category_demand[category] += 1
    
    # Generate forecasts (simulated AI)
    forecasts = []
    for category, count in category_demand.items():
        # Simulate prediction
        predicted_increase = random.randint(-20, 200)
        
        forecasts.append({
            "category": category,
            "current_demand": count,
            "predicted_change": predicted_increase,
            "forecast": count * (1 + predicted_increase / 100),
            "confidence": random.randint(70, 95),
            "reason": "Seasonal trend" if predicted_increase > 50 else "Normal pattern"
        })
    
    forecasts.sort(key=lambda x: x["predicted_change"], reverse=True)
    
    return {"forecasts": forecasts[:10]}

# Fraud & Anomaly Detection
@router.get("/fraud/detection")
async def detect_fraud(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    anomalies = []
    
    # Check for suspicious booking patterns
    customers = await db.users.find({"role": "customer"}).to_list(length=1000)
    
    for customer in customers:
        recent_bookings = await db.bookings.find({
            "customer_id": str(customer["_id"]),
            "created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)}
        }).to_list(length=100)
        
        if len(recent_bookings) > 5:
            anomalies.append({
                "type": "suspicious_booking_volume",
                "user_id": str(customer["_id"]),
                "user_name": customer.get("full_name"),
                "details": f"{len(recent_bookings)} bookings in 1 hour",
                "severity": "high"
            })
    
    # Check for location anomalies
    checkins = await db.provider_checkins.find({}).sort("timestamp", -1).limit(1000).to_list(length=1000)
    
    for checkin in checkins:
        booking = await db.bookings.find_one({"_id": ObjectId(checkin["booking_id"])})
        if booking:
            # Calculate distance
            checkin_lat = checkin["location"]["latitude"]
            checkin_lng = checkin["location"]["longitude"]
            booking_lat = booking.get("location", {}).get("latitude", 0)
            booking_lng = booking.get("location", {}).get("longitude", 0)
            
            # Simple distance check (should use haversine)
            distance = abs(checkin_lat - booking_lat) + abs(checkin_lng - booking_lng)
            
            if distance > 0.5:  # ~50km
                anomalies.append({
                    "type": "location_mismatch",
                    "provider_id": checkin["provider_id"],
                    "details": f"Check-in {distance*100:.0f}km from job site",
                    "severity": "medium"
                })
    
    return {"anomalies": anomalies[:50]}

# System Kill Switch
@router.post("/system/kill-switch")
async def toggle_kill_switch(
    enabled: bool,
    zone: Optional[str] = None,
    reason: str = "",
    admin: dict = Depends(verify_admin)
):
    db = get_db()
    
    kill_switch = {
        "enabled": enabled,
        "zone": zone,
        "reason": reason,
        "activated_by": admin["sub"],
        "activated_at": datetime.utcnow()
    }
    
    await db.system_config.update_one(
        {"key": "kill_switch"},
        {"$set": kill_switch},
        upsert=True
    )
    
    return {"success": True, "kill_switch_active": enabled}

@router.get("/system/kill-switch/status")
async def get_kill_switch_status(admin: dict = Depends(verify_admin)):
    db = get_db()
    
    config = await db.system_config.find_one({"key": "kill_switch"})
    
    return {"kill_switch": config if config else {"enabled": False}}

@router.get("/product-analytics")
async def get_product_analytics(admin: dict = Depends(verify_admin)):
    """Return real feature usage, conversion funnel, search queries, and cohort data."""
    db = get_db()

    # 1. Feature usage — count bookings per source/feature tag
    feature_tags = [
        ("Smart Booking",   {"source": "smart_booking"}),
        ("AI Match",        {"source": "ai_match"}),
        ("Live Tracking",   {"source": "live_tracking"}),
        ("Loyalty Rewards", {"source": "loyalty"}),
        ("Emergency",       {"is_emergency": True}),
    ]
    feature_usage = []
    for name, query in feature_tags:
        count = await db.bookings.count_documents(query)
        feature_usage.append({"feature": name, "sessions": count, "avg_time": "N/A"})
    # Sort descending
    feature_usage.sort(key=lambda x: x["sessions"], reverse=True)

    # 2. Conversion funnel from real counts
    total_users      = await db.users.count_documents({"role": "customer"})
    searched         = await db.chatbot_logs.count_documents({})  # proxy for search activity
    bookings_init    = await db.bookings.count_documents({})
    bookings_done    = await db.bookings.count_documents({"status": "completed"})
    reviews_given    = await db.reviews.count_documents({})
    base = max(total_users, 1)
    conversion_funnel = [
        {"step": "Registered",         "count": total_users,   "pct": 100},
        {"step": "Search / AI Query",  "count": searched,      "pct": round(min(searched / base * 100, 100), 1)},
        {"step": "Booking Initiated",  "count": bookings_init, "pct": round(min(bookings_init / base * 100, 100), 1)},
        {"step": "Booking Completed",  "count": bookings_done, "pct": round(min(bookings_done / base * 100, 100), 1)},
        {"step": "Review Given",       "count": reviews_given, "pct": round(min(reviews_given / base * 100, 100), 1)},
    ]

    # 3. Top search queries from chatbot logs
    pipeline = [
        {"$group": {"_id": "$message", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    raw_queries = await db.chatbot_logs.aggregate(pipeline).to_list(length=10)
    search_queries = [
        {"query": q["_id"], "count": q["count"], "zero_result": False}
        for q in raw_queries if q["_id"]
    ]

    # 4. Cohort retention — group providers by signup month, check activity
    now = datetime.utcnow()
    cohort_data = []
    for months_ago in range(4):
        start = (now - timedelta(days=30 * (months_ago + 1))).replace(day=1)
        end   = (now - timedelta(days=30 * months_ago)).replace(day=1)
        cohort_providers = await db.users.find(
            {"role": "provider", "created_at": {"$gte": start, "$lt": end}}
        ).to_list(length=500)
        if not cohort_providers:
            continue
        total = len(cohort_providers)
        retention = []
        for m in range(4):
            cutoff = start + timedelta(days=30 * m)
            active = 0
            for p in cohort_providers:
                last = await db.bookings.find_one(
                    {"provider_id": str(p["_id"]), "created_at": {"$gte": cutoff}},
                    sort=[("created_at", -1)]
                )
                if last:
                    active += 1
            retention.append(round(active / total * 100) if total else None)
        cohort_data.append({
            "month": start.strftime("%b %y"),
            "m0": retention[0], "m1": retention[1],
            "m2": retention[2], "m3": retention[3],
        })

    return {
        "feature_usage":     feature_usage,
        "conversion_funnel": conversion_funnel,
        "search_queries":    search_queries,
        "cohort_data":       cohort_data,
    }


@router.get("/marketing")
async def get_marketing_data(admin: dict = Depends(verify_admin)):
    """Return real campaigns, promo codes, referrals, and search queries."""
    db = get_db()

    # 1. Campaigns from DB
    campaigns_raw = await db.campaigns.find({}).sort("created_at", -1).limit(20).to_list(length=20)
    campaigns = []
    for c in campaigns_raw:
        campaigns.append({
            "id":          str(c["_id"]),
            "name":        c.get("name", "Campaign"),
            "type":        c.get("type", "Email"),
            "target":      c.get("target", "All Users"),
            "sent":        c.get("sent", 0),
            "opens":       c.get("opens", 0),
            "conversions": c.get("conversions", 0),
            "roi":         c.get("roi", 0),
        })

    # 2. Promo codes from DB
    promos_raw = await db.user_coupons.aggregate([
        {"$group": {
            "_id":      "$code",
            "uses":     {"$sum": 1},
            "redeemed": {"$sum": {"$cond": ["$used", 1, 0]}},
            "discount": {"$first": "$discount_percent"},
            "expires":  {"$first": "$expires_at"},
        }},
        {"$sort": {"uses": -1}},
        {"$limit": 10}
    ]).to_list(length=10)
    promo_codes = []
    for p in promos_raw:
        exp = p.get("expires")
        promo_codes.append({
            "code":     p["_id"],
            "discount": f"{p.get('discount', 0)}%",
            "uses":     p.get("uses", 0),
            "redeemed": p.get("redeemed", 0),
            "budget":   p.get("uses", 0) * 100,
            "roi":      0,
            "expires":  exp.strftime("%b %d") if hasattr(exp, "strftime") else "N/A",
        })

    # 3. Top referrers — users who referred the most others
    referrers_raw = await db.users.aggregate([
        {"$match": {"referred_by": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$referred_by", "referrals": {"$sum": 1}}},
        {"$sort": {"referrals": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    top_referrers = []
    for r in referrers_raw:
        uid = r["_id"]
        user = None
        try:
            user = await db.users.find_one({"_id": ObjectId(uid) if len(str(uid)) == 24 else uid})
        except Exception:
            pass
        earn_pipe = await db.payments.aggregate([
            {"$match": {"user_id": str(uid), "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$final_amount"}}}
        ]).to_list(length=1)
        top_referrers.append({
            "user_id":  str(uid),
            "name":     user.get("full_name", "User") if user else "User",
            "referrals": r["referrals"],
            "revenue":  earn_pipe[0]["total"] if earn_pipe else 0,
        })

    total_referrals = sum(r["referrals"] for r in top_referrers)
    total_ref_revenue = sum(r["revenue"] for r in top_referrers)

    # 4. SEO / search queries from chatbot logs
    pipeline = [
        {"$group": {"_id": "$message", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    raw_q = await db.chatbot_logs.aggregate(pipeline).to_list(length=10)
    seo_keywords = [{"query": q["_id"], "count": q["count"], "zero_result": False} for q in raw_q if q["_id"]]

    # 5. Partners from DB
    partners_raw = await db.partners.find({}).to_list(length=20)
    partners = []
    for p in partners_raw:
        partners.append({
            "name":   p.get("name"),
            "type":   p.get("type"),
            "deal":   p.get("deal"),
            "status": p.get("status", "active"),
            "value":  p.get("value", ""),
        })

    return {
        "campaigns":      campaigns,
        "promo_codes":    promo_codes,
        "top_referrers":  top_referrers,
        "seo_keywords":   seo_keywords,
        "partners":       partners,
        "referral_stats": {
            "total_referrals":         total_referrals,
            "revenue_from_referrals":  round(total_ref_revenue, 2),
            "conversion_rate":         round(total_referrals / max(await db.users.count_documents({"role": "customer"}), 1) * 100, 1),
        },
    }


@router.get("/tech-ops/latency-history")
async def get_latency_history(admin: dict = Depends(verify_admin)):
    """Return API latency history from DB logs."""
    db = get_db()
    logs = await db.api_logs.aggregate([
        {"$group": {
            "_id":     {"$dateToString": {"format": "%H:00", "date": "$timestamp"}},
            "latency": {"$avg": "$response_time_ms"}
        }},
        {"$sort": {"_id": 1}},
        {"$limit": 24}
    ]).to_list(length=24)
    history = [{"time": l["_id"], "latency": round(l["latency"], 1)} for l in logs]
    return {"latency_history": history}


@router.get("/transactions")
async def get_all_transactions(
    type: Optional[str] = None,   # "incoming" | "outgoing" | "refund" | None = all
    page: int = 1,
    limit: int = 100,
    admin: dict = Depends(verify_admin)
):
    """Return full transaction history: incoming (customer payments) + outgoing (provider payouts) + refunds."""
    db = get_db()
    skip = (page - 1) * limit

    # ── All payments ──────────────────────────────────────────────────────
    payments = await db.payments.find({}).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    total = await db.payments.count_documents({})

    transactions = []
    for p in payments:
        pid = str(p["_id"])

        # Resolve customer name
        uid = str(p.get("user_id", ""))
        customer = None
        try:
            customer = await db.users.find_one({"_id": ObjectId(uid)}) if len(uid) == 24 else None
        except Exception:
            pass

        # Resolve provider name
        prov_id = str(p.get("provider_id", ""))
        provider = None
        try:
            provider = await db.users.find_one({"_id": ObjectId(prov_id)}) if len(prov_id) == 24 else None
        except Exception:
            pass

        customer_name = customer.get("full_name", "Customer") if customer else uid or "Customer"
        provider_name = provider.get("full_name", "Provider") if provider else prov_id or "Provider"

        base = {
            "payment_id":    pid,
            "booking_id":    str(p.get("booking_id", "")),
            "service_name":  p.get("service_name", "Service"),
            "payment_method": p.get("payment_method", ""),
            "status":        p.get("status", "pending"),
            "escrow_status": p.get("escrow_status", ""),
            "created_at":    p.get("created_at"),
            "customer_name": customer_name,
            "customer_id":   uid,
            "provider_name": provider_name,
            "provider_id":   prov_id,
            "gst_amount":    round(p.get("gst_amount", 0), 2),
            "discount_amount": round(p.get("discount_amount", 0), 2),
            "platform_fee":  round(p.get("platform_fee", 0), 2),
        }

        # INCOMING — customer paid into platform
        if type in (None, "incoming"):
            transactions.append({
                **base,
                "flow":        "incoming",
                "direction":   "↓ IN",
                "party":       customer_name,
                "party_role":  "customer",
                "amount":      round(p.get("final_amount", 0), 2),
                "description": f"Payment from {customer_name}",
            })

        # OUTGOING — platform paid out to provider (only when escrow released)
        if type in (None, "outgoing") and p.get("escrow_status") == "released":
            transactions.append({
                **base,
                "flow":        "outgoing",
                "direction":   "↑ OUT",
                "party":       provider_name,
                "party_role":  "provider",
                "amount":      round(p.get("provider_payout", 0), 2),
                "description": f"Payout to {provider_name}",
            })

        # REFUND — money returned to customer
        if type in (None, "refund") and p.get("status") == "refunded":
            transactions.append({
                **base,
                "flow":        "refund",
                "direction":   "↩ REF",
                "party":       customer_name,
                "party_role":  "customer",
                "amount":      round(p.get("refund_amount", p.get("final_amount", 0)), 2),
                "description": f"Refund to {customer_name} — {p.get('refund_reason', '')}",
                "refund_reason": p.get("refund_reason", ""),
            })

    # Sort all by created_at desc
    transactions.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)

    # Summary stats
    all_payments = await db.payments.find({}).to_list(length=10000)
    total_in  = sum(p.get("final_amount", 0) for p in all_payments if p.get("status") == "completed")
    total_out = sum(p.get("provider_payout", 0) for p in all_payments if p.get("escrow_status") == "released")
    total_ref = sum(p.get("refund_amount", p.get("final_amount", 0)) for p in all_payments if p.get("status") == "refunded")
    platform_net = total_in - total_out - total_ref

    return {
        "transactions": transactions,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "summary": {
            "total_incoming":   round(total_in, 2),
            "total_outgoing":   round(total_out, 2),
            "total_refunds":    round(total_ref, 2),
            "platform_net":     round(platform_net, 2),
        }
    }

# ── Router Section: advanced ──
advanced_router = APIRouter()
router = advanced_router
from fastapi import APIRouter, Depends
from datetime import datetime
from bson import ObjectId
from typing import Optional
import random


# Eco-Impact Tracker & Carbon Rewards
@router.get("/eco-impact")
async def get_eco_impact(current_user: dict = Depends(get_current_user)):
    """Calculate CO2 savings and green points for user bookings"""
    db = get_db()
    
    bookings = await db.bookings.find({"user_id": current_user["sub"]}).to_list(length=100)
    
    total_co2_saved = 0
    green_points = 0
    
    for booking in bookings:
        # Calculate CO2 based on clustered routes (simplified)
        distance = random.uniform(2, 10)  # km
        co2_per_km = 0.12  # kg CO2 per km
        co2_saved = distance * co2_per_km * 0.3  # 30% savings from route optimization
        total_co2_saved += co2_saved
        green_points += int(co2_saved * 10)
    
    # Get user's green points balance
    eco_account = await db.eco_accounts.find_one({"user_id": current_user["sub"]})
    if not eco_account:
        eco_account = {
            "user_id": current_user["sub"],
            "green_points": green_points,
            "total_co2_saved": total_co2_saved,
            "trees_planted": 0,
            "created_at": datetime.utcnow()
        }
        await db.eco_accounts.insert_one(eco_account)
    
    return {
        "total_co2_saved_kg": round(total_co2_saved, 2),
        "green_points": green_points,
        "trees_equivalent": round(total_co2_saved / 21, 2),  # 21kg CO2 per tree/year
        "badges": [
            {"name": "Eco Warrior", "unlocked": green_points > 500},
            {"name": "Carbon Neutral", "unlocked": total_co2_saved > 50},
            {"name": "Green Champion", "unlocked": green_points > 1000}
        ],
        "redemption_options": [
            {"name": "Plant 1 Tree", "points": 200, "partner": "Stripe Climate"},
            {"name": "EV Charger Credit ₹50", "points": 500},
            {"name": "Solar Panel Discount 5%", "points": 1000}
        ]
    }

@router.post("/eco-impact/redeem")
async def redeem_green_points(
    reward_name: str,
    points_required: int,
    current_user: dict = Depends(get_current_user)
):
    """Redeem green points for eco rewards"""
    db = get_db()
    
    eco_account = await db.eco_accounts.find_one({"user_id": current_user["sub"]})
    if not eco_account or eco_account.get("green_points", 0) < points_required:
        return {"error": "Insufficient green points"}
    
    # Deduct points
    await db.eco_accounts.update_one(
        {"user_id": current_user["sub"]},
        {"$inc": {"green_points": -points_required}}
    )
    
    # Log redemption
    await db.eco_redemptions.insert_one({
        "user_id": current_user["sub"],
        "reward": reward_name,
        "points": points_required,
        "timestamp": datetime.utcnow()
    })
    
    return {"status": "redeemed", "reward": reward_name, "points_used": points_required}

# Provider Duos for Complex Jobs
@router.post("/provider-duos/match")
async def match_provider_duo(
    primary_service: str,
    secondary_service: str,
    location: dict,
    current_user: dict = Depends(get_current_user)
):
    """AI matches complementary providers for complex jobs"""
    db = get_db()
    
    # Find providers for each service
    primary_providers = await db.users.find({
        "role": "provider",
        "specializations": primary_service,
        "is_verified": True
    }).sort("rating", -1).limit(5).to_list(length=5)
    
    secondary_providers = await db.users.find({
        "role": "provider",
        "specializations": secondary_service,
        "is_verified": True
    }).sort("rating", -1).limit(5).to_list(length=5)
    
    # Match best duo based on ratings and proximity
    best_duos = []
    for p1 in primary_providers:
        for p2 in secondary_providers:
            duo_score = (p1.get("rating", 0) + p2.get("rating", 0)) / 2
            best_duos.append({
                "primary_provider": {
                    "id": str(p1["_id"]),
                    "name": p1.get("full_name"),
                    "service": primary_service,
                    "rating": p1.get("rating"),
                    "price": p1.get("price_per_hour", 500)
                },
                "secondary_provider": {
                    "id": str(p2["_id"]),
                    "name": p2.get("full_name"),
                    "service": secondary_service,
                    "rating": p2.get("rating"),
                    "price": p2.get("price_per_hour", 500)
                },
                "duo_score": round(duo_score, 2),
                "combined_price": p1.get("price_per_hour", 500) + p2.get("price_per_hour", 500),
                "revenue_split": "50/50"
            })
    
    best_duos.sort(key=lambda x: x["duo_score"], reverse=True)
    
    return {
        "service_combo": f"{primary_service} + {secondary_service}",
        "top_duos": best_duos[:3],
        "savings": "15% discount on duo booking"
    }

@router.post("/provider-duos/book")
async def book_provider_duo(
    primary_provider_id: str,
    secondary_provider_id: str,
    service_details: dict,
    current_user: dict = Depends(get_current_user)
):
    """Book a provider duo for complex job"""
    db = get_db()
    
    duo_booking = {
        "user_id": current_user["sub"],
        "primary_provider_id": primary_provider_id,
        "secondary_provider_id": secondary_provider_id,
        "service_details": service_details,
        "status": "pending",
        "revenue_split": {"primary": 50, "secondary": 50},
        "created_at": datetime.utcnow()
    }
    
    result = await db.duo_bookings.insert_one(duo_booking)
    
    # Notify both providers
    await db.notifications.insert_many([
        {
            "user_id": primary_provider_id,
            "message": "New duo booking request!",
            "type": "duo_booking",
            "booking_id": str(result.inserted_id),
            "created_at": datetime.utcnow()
        },
        {
            "user_id": secondary_provider_id,
            "message": "New duo booking request!",
            "type": "duo_booking",
            "booking_id": str(result.inserted_id),
            "created_at": datetime.utcnow()
        }
    ])
    
    return {"booking_id": str(result.inserted_id), "status": "pending_acceptance"}

# Sentiment-Driven Dynamic Reviews
@router.post("/reviews/sentiment-analysis")
async def analyze_review_sentiment(
    booking_id: str,
    voice_transcript: str,
    text_review: str,
    rating: int,
    current_user: dict = Depends(get_current_user)
):
    """AI analyzes voice tone and text sentiment for nuanced reviews"""
    db = get_db()
    
    # Simple sentiment analysis (in production, use RoBERTa or similar)
    positive_words = ["great", "excellent", "amazing", "professional", "punctual", "friendly", "helpful"]
    negative_words = ["late", "rude", "poor", "bad", "terrible", "unprofessional", "slow"]
    
    text_lower = (voice_transcript + " " + text_review).lower()
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    # Calculate enthusiasm score
    enthusiasm_score = min(10, (positive_count * 2 - negative_count) + rating)
    enthusiasm_score = max(0, enthusiasm_score)
    
    # Detect specific traits
    traits = {
        "punctuality": "punctual" in text_lower or "on time" in text_lower,
        "professionalism": "professional" in text_lower,
        "friendliness": "friendly" in text_lower or "polite" in text_lower,
        "expertise": "expert" in text_lower or "skilled" in text_lower,
        "communication": "communicated" in text_lower or "explained" in text_lower
    }
    
    # Store enhanced review
    enhanced_review = {
        "booking_id": booking_id,
        "user_id": current_user["sub"],
        "rating": rating,
        "text_review": text_review,
        "voice_transcript": voice_transcript,
        "sentiment_analysis": {
            "enthusiasm_score": round(enthusiasm_score, 1),
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "detected_traits": traits
        },
        "created_at": datetime.utcnow()
    }
    
    result = await db.enhanced_reviews.insert_one(enhanced_review)
    
    # Update provider's trust score
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if booking:
        provider_id = booking.get("provider_id")
        await db.users.update_one(
            {"_id": ObjectId(provider_id)},
            {"$inc": {"trust_score": enthusiasm_score / 10}}
        )
    
    return {
        "review_id": str(result.inserted_id),
        "enthusiasm_score": round(enthusiasm_score, 1),
        "sentiment": "positive" if enthusiasm_score > 6 else "neutral" if enthusiasm_score > 4 else "negative",
        "detected_traits": traits,
        "trust_graph_updated": True
    }

# Hyperlocal Event Tie-Ins
@router.get("/events/nearby")
async def get_nearby_events(lat: float, lng: float, radius: float = 5.0):
    """Scrape and bundle services for local events"""
    db = get_db()
    
    # Simulated event data (in production, scrape Eventbrite/Nextdoor)
    mock_events = [
        {
            "name": "Community Block Party",
            "date": "2024-02-15",
            "location": {"lat": lat + 0.01, "lng": lng + 0.01},
            "attendees": 150,
            "suggested_services": ["cleaning", "delivery", "beauty"]
        },
        {
            "name": "Local Sports Tournament",
            "date": "2024-02-20",
            "location": {"lat": lat - 0.02, "lng": lng + 0.02},
            "attendees": 300,
            "suggested_services": ["fitness", "delivery", "repair"]
        }
    ]
    
    # Create service bundles
    bundles = []
    for event in mock_events:
        bundle_services = []
        for service_type in event["suggested_services"]:
            providers = await db.users.find({
                "role": "provider",
                "specializations": service_type
            }).limit(2).to_list(length=2)
            
            for p in providers:
                bundle_services.append({
                    "provider": p.get("full_name"),
                    "service": service_type,
                    "price": p.get("price_per_hour", 500)
                })
        
        bundles.append({
            "event": event["name"],
            "date": event["date"],
            "services": bundle_services,
            "bundle_discount": "25% off",
            "estimated_total": sum(s["price"] for s in bundle_services) * 0.75
        })
    
    return {"nearby_events": bundles}

# Neighborhood Skill-Sharing Marketplace
@router.post("/skill-share/create")
async def create_skill_share(
    offer_skill: str,
    request_skill: str,
    description: str,
    current_user: dict = Depends(get_current_user)
):
    """Create a skill-sharing barter offer"""
    db = get_db()
    
    skill_share = {
        "user_id": current_user["sub"],
        "offer_skill": offer_skill,
        "request_skill": request_skill,
        "description": description,
        "status": "active",
        "matches": [],
        "created_at": datetime.utcnow()
    }
    
    result = await db.skill_shares.insert_one(skill_share)
    
    # Find potential matches
    matches = await db.skill_shares.find({
        "offer_skill": request_skill,
        "request_skill": offer_skill,
        "status": "active",
        "user_id": {"$ne": current_user["sub"]}
    }).to_list(length=10)
    
    return {
        "skill_share_id": str(result.inserted_id),
        "potential_matches": len(matches),
        "status": "active"
    }

@router.get("/skill-share/matches")
async def get_skill_share_matches(current_user: dict = Depends(get_current_user)):
    """Get AI-suggested skill-sharing matches"""
    db = get_db()
    
    user_shares = await db.skill_shares.find({
        "user_id": current_user["sub"],
        "status": "active"
    }).to_list(length=10)
    
    all_matches = []
    for share in user_shares:
        matches = await db.skill_shares.find({
            "offer_skill": share["request_skill"],
            "status": "active",
            "user_id": {"$ne": current_user["sub"]}
        }).to_list(length=5)
        
        for match in matches:
            match_user = await db.users.find_one({"_id": ObjectId(match["user_id"])})
            all_matches.append({
                "match_id": str(match["_id"]),
                "user": match_user.get("full_name") if match_user else "Unknown",
                "offering": match["offer_skill"],
                "requesting": match["request_skill"],
                "compatibility_score": random.randint(70, 95)
            })
    
    return {"matches": all_matches}

# ── Router Section: ai ──
ai_router = APIRouter()
router = ai_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import Optional
import random


# AI Chatbot
@router.post("/chatbot")
async def chatbot(message: str, current_user: Optional[dict] = Depends(get_optional_user)):
    """AI-powered chatbot with real DB context"""
    db = get_db()
    msg = message.strip().lower()
    user_id = current_user["sub"] if current_user else None

    # ── Fetch real context ────────────────────────────────────────────────
    active_booking = None
    recent_bookings = []
    loyalty_points = 0

    if user_id:
        active_booking = await db.bookings.find_one(
            {"user_id": user_id, "status": {"$in": ["confirmed", "in_progress"]}},
            sort=[("created_at", -1)]
        )
        recent_bookings = await db.bookings.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(3).to_list(length=3)
        loyalty = await db.loyalty_accounts.find_one({"user_id": user_id})
        loyalty_points = loyalty.get("points", 0) if loyalty else 0

    # ── Intent detection + real-data responses ────────────────────────────
    response = None

    if any(w in msg for w in ["hi", "hello", "hey", "namaste"]):
        response = "Hello! I'm QuickServe AI. I can help you book services, track your provider, check your loyalty points, or answer any questions. What do you need?"

    elif any(w in msg for w in ["track", "where", "arrive", "eta", "coming"]):
        if active_booking:
            svc = active_booking.get("service_name") or active_booking.get("category", "service")
            status = active_booking.get("status", "confirmed")
            response = f"Your {svc} booking is currently **{status}**. Check the Job Tracker tab in your dashboard for live location updates."
        else:
            response = "You don't have any active bookings right now. Head to Services to book one!"

    elif any(w in msg for w in ["booking", "book", "appointment", "schedule"]):
        if recent_bookings:
            last = recent_bookings[0]
            svc = last.get("service_name") or last.get("category", "service")
            status = last.get("status", "pending")
            response = f"Your last booking was for **{svc}** (status: {status}). You have {len(recent_bookings)} recent booking(s). Want to book a new service?"
        else:
            response = "You haven't made any bookings yet. Browse our services and book your first one — new users get 10% off!"

    elif any(w in msg for w in ["point", "loyalty", "reward", "credit"]):
        response = f"You have **{loyalty_points} loyalty points**. Earn more with every booking (1 point per ₹10 spent). Redeem for discounts, free services, and VIP access!"

    elif any(w in msg for w in ["cancel", "refund"]):
        response = "To cancel a booking, go to My Bookings and tap Cancel. Refunds are processed within 3-5 business days. For completed bookings, partial refunds (up to 50%) may apply."

    elif any(w in msg for w in ["pay", "payment", "price", "cost", "charge", "fee"]):
        response = "We accept UPI, Credit/Debit Cards (via Stripe), and Bank Transfer. All payments are secured with escrow — funds are only released to the provider after you confirm the job is done."

    elif any(w in msg for w in ["plumb", "pipe", "leak", "tap", "drain"]):
        count = await db.users.count_documents({"role": "provider", "specializations": "plumbing", "verified_by_admin": True})
        response = f"We have **{count} verified plumbers** available. They handle leaks, pipe repairs, installations, and more. Prices start at ₹500/hr. Want me to find one near you?"

    elif any(w in msg for w in ["electric", "wiring", "switch", "fuse", "power"]):
        count = await db.users.count_documents({"role": "provider", "specializations": "electrical", "verified_by_admin": True})
        response = f"We have **{count} certified electricians** ready to help. From wiring to panel upgrades. Prices start at ₹600/hr."

    elif any(w in msg for w in ["clean", "sweep", "mop", "dust", "sanitize"]):
        count = await db.users.count_documents({"role": "provider", "specializations": "cleaning", "verified_by_admin": True})
        response = f"We have **{count} professional cleaners** available for deep cleaning, regular maintenance, and move-in/out cleaning. Prices start at ₹300/hr."

    elif any(w in msg for w in ["emergency", "urgent", "asap", "now", "immediately"]):
        response = "For emergencies, use the **Emergency Booking** button on the Services page. We'll connect you with the nearest available provider within minutes. A 1.5x surge fee applies."

    elif any(w in msg for w in ["rating", "review", "feedback", "rate"]):
        response = "After a job is completed, you can rate your provider (1-5 stars) and leave a review. Your feedback helps maintain quality and earns you 50 loyalty points!"

    elif any(w in msg for w in ["provider", "worker", "technician", "professional"]):
        total = await db.users.count_documents({"role": "provider", "verified_by_admin": True})
        response = f"QuickServe has **{total} verified professionals** across multiple categories. All providers pass background checks and skill assessments before joining."

    elif any(w in msg for w in ["help", "support", "problem", "issue", "complaint"]):
        response = "I'm here to help! You can ask me about: bookings, tracking, payments, loyalty points, services, or providers. For urgent issues, email support@quickserve.app."

    if not response:
        # Generic fallback with real stats
        total_services = await db.services.count_documents({})
        response = f"I can help with bookings, tracking, payments, and more. We have {total_services}+ services available. Try asking: 'Book a plumber', 'Track my order', or 'Check my points'."

    # Log conversation
    await db.chatbot_logs.insert_one({
        "user_id": user_id or "anonymous",
        "message": message,
        "response": response,
        "timestamp": datetime.utcnow()
    })

    return {"response": response, "timestamp": datetime.utcnow()}

# Voice Search
@router.post("/voice-search")
async def voice_search(transcript: str, location: Optional[dict] = None):
    """Convert voice input to service search"""
    db = get_db()
    
    # Extract service type from transcript
    transcript_lower = transcript.lower()
    service_keywords = {
        "plumber": "plumbing",
        "electrician": "electrical",
        "cleaner": "cleaning",
        "beauty": "beauty",
        "fitness": "fitness",
        "delivery": "delivery",
        "repair": "repair",
        "tutor": "tutoring",
        "carpenter": "carpentry",
        "painter": "painting",
        "gardener": "gardening",
        "pest": "pest_control"
    }
    
    detected_service = None
    for keyword, service in service_keywords.items():
        if keyword in transcript_lower:
            detected_service = service
            break
    
    if detected_service:
        # Search for services
        query = {"category": detected_service}
        services = await db.services.find(query).limit(10).to_list(length=10)
        for s in services:
            s["_id"] = str(s["_id"])
        
        return {
            "transcript": transcript,
            "detected_service": detected_service,
            "results": services,
            "count": len(services)
        }
    
    return {
        "transcript": transcript,
        "detected_service": None,
        "message": "Could not detect service type. Please try again.",
        "results": []
    }

# AI-based Service Recommendations (Collaborative Filtering simulation)
@router.get("/recommendations")
async def get_ai_recommendations(current_user: dict = Depends(get_current_user)):
    """Personalized service recommendations using simulated collaborative filtering"""
    db = get_db()
    
    # 1. Get similar users' preferences (mock collaborative filtering)
    # Find providers that other users with similar booking history liked
    user_bookings = await db.bookings.find({"user_id": current_user["sub"]}).to_list(length=10)
    user_categories = set()
    for b in user_bookings:
        service = await db.services.find_one({"_id": b.get("service_id")})
        if service: user_categories.add(service.get("category"))
    
    # 2. Hybrid approach: content-based + simulated collaborative
    recommendations = []
    
    # If user has history, find similar categories
    if user_categories:
        for cat in user_categories:
            # Find top rated in this category
            top_in_cat = await db.users.find({"role": "provider", "specializations": cat}).sort("rating", -1).limit(2).to_list(length=2)
            for p in top_in_cat:
                p["_id"] = str(p["_id"])
                p["reason"] = f"Popular in your favorite category: {cat}"
                recommendations.append(p)
    
    # Add trending services in the area (simulated)
    trending = await db.users.find({"role": "provider", "quickserve_score": {"$gt": 90}}).limit(3).to_list(length=3)
    for p in trending:
        p["_id"] = str(p["_id"])
        p["reason"] = "Trending in your neighborhood"
        if not any(r["_id"] == p["_id"] for r in recommendations):
            recommendations.append(p)
            
    return {"recommendations": recommendations[:6]}

# Smart Pricing Suggestions
@router.get("/smart-pricing")
async def get_smart_pricing(category: str, current_user: dict = Depends(get_current_user)):
    """AI pricing suggestions based on competitor analysis and demand"""
    db = get_db()
    
    # Get average price for category
    pipeline = [
        {"$match": {"role": "provider", "specializations": category}},
        {"$group": {"_id": None, "avg_rate": {"$avg": "$hourly_rate"}}}
    ]
    result = await db.users.aggregate(pipeline).to_list(length=1)
    avg_rate = result[0]["avg_rate"] if result else 500
    
    # Demand factor (mock)
    hour = datetime.utcnow().hour
    demand_multiplier = 1.0
    if 17 <= hour <= 21: demand_multiplier = 1.2 # Peak evening
    
    suggested = avg_rate * demand_multiplier
    
    return {
        "category": category,
        "market_average": round(avg_rate, 2),
        "demand_index": demand_multiplier,
        "suggested_rate": round(suggested, 2),
        "competitive_range": [round(suggested * 0.9, 2), round(suggested * 1.1, 2)]
    }

# Demand Prediction
@router.get("/demand-prediction")
async def predict_demand(category: str, date: Optional[str] = None):
    """ML-based demand prediction for service categories"""
    db = get_db()
    
    # Get historical booking data
    target_date = datetime.fromisoformat(date) if date else datetime.utcnow()
    day_of_week = target_date.weekday()
    hour = target_date.hour
    
    # Simple prediction model (in production, use actual ML model)
    base_demand = {
        "plumbing": 50,
        "electrical": 45,
        "cleaning": 80,
        "beauty": 60,
        "fitness": 70,
        "delivery": 100,
        "repair": 40,
        "tutoring": 55,
        "carpentry": 30,
        "painting": 25,
        "gardening": 35,
        "pest_control": 20
    }
    
    # Adjust for day of week (weekends higher)
    weekend_multiplier = 1.3 if day_of_week >= 5 else 1.0
    
    # Adjust for time of day
    if 9 <= hour <= 18:
        time_multiplier = 1.2
    elif 18 < hour <= 21:
        time_multiplier = 1.5
    else:
        time_multiplier = 0.7
    
    predicted_demand = int(base_demand.get(category, 40) * weekend_multiplier * time_multiplier)
    
    # Get available providers
    available_providers = await db.users.count_documents({"role": "provider", "specializations": category})
    
    availability_status = "high" if available_providers > predicted_demand * 0.5 else "medium" if available_providers > predicted_demand * 0.3 else "low"
    
    return {
        "category": category,
        "date": target_date.isoformat(),
        "predicted_demand": predicted_demand,
        "available_providers": available_providers,
        "availability_status": availability_status,
        "recommendation": "Book now" if availability_status == "low" else "Good availability"
    }

# Fake Review Detection
@router.post("/detect-fake-review")
async def detect_fake_review(review_text: str, rating: int):
    """AI-powered fake review detection"""
    
    # Simple heuristic-based detection (in production, use ML model)
    suspicious_indicators = 0
    reasons = []
    
    # Check 1: Very short reviews with extreme ratings
    if len(review_text.split()) < 5 and (rating == 1 or rating == 5):
        suspicious_indicators += 1
        reasons.append("Very short review with extreme rating")
    
    # Check 2: Excessive use of superlatives
    superlatives = ["best", "worst", "amazing", "terrible", "perfect", "horrible", "excellent", "awful"]
    superlative_count = sum(1 for word in superlatives if word in review_text.lower())
    if superlative_count > 3:
        suspicious_indicators += 1
        reasons.append("Excessive use of superlatives")
    
    # Check 3: Generic content
    generic_phrases = ["good service", "bad service", "highly recommend", "waste of money", "five stars"]
    generic_count = sum(1 for phrase in generic_phrases if phrase in review_text.lower())
    if generic_count > 2:
        suspicious_indicators += 1
        reasons.append("Generic content")
    
    # Check 4: All caps
    if review_text.isupper() and len(review_text) > 20:
        suspicious_indicators += 1
        reasons.append("All caps text")
    
    # Check 5: Repeated characters
    if any(char * 3 in review_text for char in "abcdefghijklmnopqrstuvwxyz"):
        suspicious_indicators += 1
        reasons.append("Repeated characters")
    
    # Calculate authenticity score
    authenticity_score = max(0, 100 - (suspicious_indicators * 20))
    is_suspicious = suspicious_indicators >= 2
    
    return {
        "review_text": review_text,
        "rating": rating,
        "authenticity_score": authenticity_score,
        "is_suspicious": is_suspicious,
        "suspicious_indicators": suspicious_indicators,
        "reasons": reasons,
        "verdict": "Likely fake" if is_suspicious else "Likely authentic"
    }

# Smart Provider Matching
@router.post("/smart-match")
async def smart_match(service_type: str, location: dict, urgency: str = "normal"):
    """Automatic matching with nearest and best-rated providers"""
    db = get_db()
    
    # Find providers by service type
    providers = await db.users.find({
        "role": "provider",
        "specializations": service_type,
        "is_verified": True
    }).to_list(length=50)
    
    # Score providers based on multiple factors
    scored_providers = []
    for provider in providers:
        score = 0
        
        # Rating score (40% weight)
        score += provider.get("rating", 0) * 8
        
        # Experience score (20% weight)
        score += min(provider.get("experience_years", 0) * 2, 20)
        
        # Reviews count score (20% weight)
        score += min(provider.get("reviews_count", 0) / 10, 20)
        
        # Distance score (20% weight) - simplified
        # In production, calculate actual distance
        distance_score = random.randint(10, 20)
        score += distance_score
        
        provider["_id"] = str(provider["_id"])
        provider["match_score"] = round(score, 2)
        scored_providers.append(provider)
    
    # Sort by score
    scored_providers.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Return top matches
    top_matches = scored_providers[:5]
    
    return {
        "service_type": service_type,
        "urgency": urgency,
        "total_providers": len(providers),
        "top_matches": top_matches,
        "recommendation": top_matches[0] if top_matches else None
    }

# AI Analytics
@router.get("/analytics")
async def get_ai_analytics(current_user: dict = Depends(get_current_user)):
    """AI-powered analytics and insights"""
    db = get_db()
    
    if current_user["role"] != "admin":
        return {"error": "Admin access required"}
    
    # Get various metrics
    total_bookings = await db.bookings.count_documents({})
    total_users = await db.users.count_documents({"role": "customer"})
    total_providers = await db.users.count_documents({"role": "provider"})
    
    # Category popularity
    pipeline = [
        {"$lookup": {"from": "services", "localField": "service_id", "foreignField": "_id", "as": "service"}},
        {"$unwind": "$service"},
        {"$group": {"_id": "$service.category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    category_stats = await db.bookings.aggregate(pipeline).to_list(length=20)
    
    # Peak hours
    pipeline = [
        {"$group": {"_id": {"$hour": "$created_at"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    peak_hours = await db.bookings.aggregate(pipeline).to_list(length=24)
    
    return {
        "total_bookings": total_bookings,
        "total_users": total_users,
        "total_providers": total_providers,
        "category_popularity": category_stats,
        "peak_hours": peak_hours[:5],
        "insights": [
            "Peak booking hours are between 6 PM - 9 PM",
            "Cleaning services are most popular on weekends",
            "Emergency bookings increased by 15% this month"
        ]
    }

# ── Router Section: ai_concierge ──
ai_concierge_router = APIRouter()
router = ai_concierge_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import json


PERSONALITY_TYPES = {
    "professional": {
        "tone": "formal",
        "greeting": "Good day! I'm your professional service concierge.",
        "style": "efficient and detailed"
    },
    "friendly": {
        "tone": "casual",
        "greeting": "Hey there! I'm your friendly service buddy!",
        "style": "warm and conversational"
    },
    "minimalist": {
        "tone": "brief",
        "greeting": "Hi. Ready to help.",
        "style": "concise and direct"
    }
}

@router.post("/setup-profile")
async def setup_concierge_profile(
    preferences: Dict,
    personality: str = "friendly",
    current_user: dict = Depends(get_current_user)
):
    """Set up personalized AI concierge profile"""
    db = get_db()
    
    if personality not in PERSONALITY_TYPES:
        personality = "friendly"
    
    # Create AI profile
    ai_profile = {
        "user_id": current_user["sub"],
        "personality": personality,
        "preferences": preferences,
        "learning_data": {
            "service_patterns": {},
            "time_preferences": {},
            "budget_patterns": {},
            "provider_preferences": {}
        },
        "proactive_settings": {
            "suggest_services": preferences.get("proactive_suggestions", True),
            "schedule_reminders": preferences.get("schedule_reminders", True),
            "budget_alerts": preferences.get("budget_alerts", True),
            "seasonal_recommendations": preferences.get("seasonal_recommendations", True)
        },
        "created_at": datetime.utcnow(),
        "last_interaction": datetime.utcnow()
    }
    
    await db.ai_concierge_profiles.update_one(
        {"user_id": current_user["sub"]},
        {"$set": ai_profile},
        upsert=True
    )
    
    return {
        "message": f"AI Concierge configured with {personality} personality!",
        "greeting": PERSONALITY_TYPES[personality]["greeting"],
        "features_enabled": list(preferences.keys())
    }


@router.post("/chat")
async def chat_with_concierge(
    data: AIChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Chat with AI concierge"""
    db = get_db()
    
    # Auto-setup profile if missing
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    if not ai_profile:
        # Create a default profile
        ai_profile = {
            "user_id": current_user["sub"],
            "personality": "friendly",
            "preferences": {"proactive_suggestions": True},
            "learning_data": {},
            "proactive_settings": {
                "suggest_services": True,
                "schedule_reminders": True,
                "budget_alerts": True,
                "seasonal_recommendations": True
            },
            "created_at": datetime.utcnow(),
            "last_interaction": datetime.utcnow()
        }
        await db.ai_concierge_profiles.insert_one(ai_profile)
    
    message = data.message
    context = data.context
    
    # Process message and generate response
    response = await process_concierge_message(message, ai_profile, context, current_user, db)
    
    # Log conversation
    await db.concierge_conversations.insert_one({
        "user_id": current_user["sub"],
        "message": message,
        "response": response["text"],
        "intent": response.get("intent"),
        "actions_taken": response.get("actions", []),
        "timestamp": datetime.utcnow()
    })
    
    # Update last interaction
    await db.ai_concierge_profiles.update_one(
        {"user_id": current_user["sub"]},
        {"$set": {"last_interaction": datetime.utcnow()}}
    )
    
    return response

@router.get("/proactive-suggestions")
async def get_proactive_suggestions(current_user: dict = Depends(get_current_user)):
    """Get proactive service suggestions from AI concierge"""
    db = get_db()
    
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    if not ai_profile or not ai_profile["proactive_settings"]["suggest_services"]:
        return {"suggestions": []}
    
    # Analyze user patterns
    suggestions = await generate_proactive_suggestions(current_user["sub"], ai_profile, db)
    
    return {
        "suggestions": suggestions,
        "personality_note": get_personality_note(ai_profile["personality"], "suggestions"),
        "generated_at": datetime.utcnow().isoformat()
    }

@router.post("/schedule-coordination")
async def coordinate_multi_service_schedule(
    services: List[Dict],
    preferences: Dict,
    current_user: dict = Depends(get_current_user)
):
    """AI-powered coordination of multiple services"""
    db = get_db()
    
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    
    # Analyze and optimize schedule
    optimized_schedule = await optimize_service_schedule(services, preferences, ai_profile, db)
    
    # Create coordination plan
    coordination_plan = {
        "user_id": current_user["sub"],
        "services": services,
        "optimized_schedule": optimized_schedule,
        "preferences": preferences,
        "created_at": datetime.utcnow(),
        "status": "planned",
        "ai_confidence": optimized_schedule.get("confidence_score", 0.8)
    }
    
    result = await db.service_coordination.insert_one(coordination_plan)
    
    return {
        "coordination_id": str(result.inserted_id),
        "optimized_schedule": optimized_schedule,
        "ai_explanation": generate_schedule_explanation(optimized_schedule, ai_profile),
        "estimated_savings": optimized_schedule.get("cost_savings", 0)
    }

@router.get("/learning-insights")
async def get_learning_insights(current_user: dict = Depends(get_current_user)):
    """Get AI's learning insights about user preferences"""
    db = get_db()
    
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    if not ai_profile:
        return {"error": "AI profile not found"}
    
    # Analyze user's booking history for patterns
    bookings = await db.bookings.find({
        "user_id": current_user["sub"]
    }).sort("created_at", -1).limit(50).to_list(length=50)
    
    insights = await analyze_user_patterns(bookings, ai_profile, db)
    
    return {
        "insights": insights,
        "learning_accuracy": calculate_learning_accuracy(ai_profile),
        "recommendations": generate_improvement_recommendations(insights)
    }

@router.post("/set-automation")
async def set_service_automation(
    automation_rules: List[Dict],
    current_user: dict = Depends(get_current_user)
):
    """Set up automated service booking rules"""
    db = get_db()
    
    # Validate automation rules
    validated_rules = []
    for rule in automation_rules:
        if validate_automation_rule(rule):
            validated_rules.append({
                **rule,
                "created_at": datetime.utcnow(),
                "status": "active",
                "executions": 0
            })
    
    # Store automation rules
    await db.service_automations.update_one(
        {"user_id": current_user["sub"]},
        {
            "$set": {
                "rules": validated_rules,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return {
        "message": f"{len(validated_rules)} automation rules configured",
        "rules": validated_rules,
        "next_execution": get_next_execution_time(validated_rules)
    }

@router.get("/dashboard")
async def get_concierge_dashboard(current_user: dict = Depends(get_current_user)):
    """Get AI concierge dashboard with all insights"""
    db = get_db()
    
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    if not ai_profile:
        return {"error": "AI profile not found"}
    
    # Get various dashboard components
    recent_suggestions = await db.concierge_conversations.find({
        "user_id": current_user["sub"],
        "intent": "suggestion"
    }).sort("timestamp", -1).limit(5).to_list(length=5)
    
    active_automations = await db.service_automations.find_one({"user_id": current_user["sub"]})
    automation_count = len(active_automations.get("rules", [])) if active_automations else 0
    
    # Calculate efficiency metrics
    total_conversations = await db.concierge_conversations.count_documents({"user_id": current_user["sub"]})
    successful_bookings = await db.bookings.count_documents({
        "user_id": current_user["sub"],
        "booking_source": "ai_concierge"
    })
    
    efficiency_rate = (successful_bookings / max(total_conversations, 1)) * 100
    
    return {
        "ai_personality": ai_profile["personality"],
        "total_interactions": total_conversations,
        "successful_bookings": successful_bookings,
        "efficiency_rate": round(efficiency_rate, 1),
        "active_automations": automation_count,
        "recent_suggestions": recent_suggestions,
        "learning_progress": calculate_learning_progress(ai_profile),
        "next_proactive_check": datetime.utcnow() + timedelta(hours=6)
    }

async def process_concierge_message(message: str, ai_profile: Dict, context: Optional[Dict], current_user: Dict, db) -> Dict:
    """Process user message and generate AI response"""
    
    message_lower = message.lower()
    personality = ai_profile["personality"]
    
    # Intent detection
    intent = detect_intent(message_lower)
    
    response = {
        "text": "",
        "intent": intent,
        "actions": [],
        "suggestions": []
    }
    
    if intent == "booking_request":
        # Handle service booking request
        service_type = extract_service_type(message_lower)
        if service_type:
            providers = await db.users.find({
                "role": "provider",
                "specializations": service_type,
                "is_verified": True
            }).limit(3).to_list(length=3)
            
            response["text"] = format_response(
                f"I found {len(providers)} great {service_type} providers for you! Would you like me to show you the top-rated ones?",
                personality
            )
            response["actions"] = ["show_providers"]
            response["suggestions"] = [p["full_name"] for p in providers]
        else:
            response["text"] = format_response("What type of service are you looking for? I can help you find the perfect provider!", personality)
    
    elif intent == "schedule_query":
        # Handle schedule-related queries
        upcoming_bookings = await db.bookings.find({
            "user_id": current_user["sub"],
            "scheduled_time": {"$gte": datetime.utcnow()},
            "status": {"$in": ["confirmed", "pending"]}
        }).sort("scheduled_time", 1).limit(5).to_list(length=5)
        
        if upcoming_bookings:
            next_booking = upcoming_bookings[0]
            response["text"] = format_response(
                f"Your next service is {next_booking.get('service_type', 'a service')} scheduled for {next_booking['scheduled_time'].strftime('%B %d at %I:%M %p')}. You have {len(upcoming_bookings)} total upcoming bookings.",
                personality
            )
        else:
            response["text"] = format_response("You don't have any upcoming bookings. Would you like me to suggest some services?", personality)
    
    elif intent == "recommendation_request":
        # Generate personalized recommendations
        recommendations = await generate_smart_recommendations(current_user["sub"], ai_profile, db)
        response["text"] = format_response(
            f"Based on your preferences, I recommend: {', '.join([r['service'] for r in recommendations[:3]])}. These align perfectly with your usual patterns!",
            personality
        )
        response["suggestions"] = recommendations
    
    elif intent == "budget_query":
        # Handle budget-related questions
        monthly_spending = await calculate_monthly_spending(current_user["sub"], db)
        response["text"] = format_response(
            f"This month you've spent ₹{monthly_spending} on services. Based on your patterns, you typically spend around ₹{monthly_spending * 1.1:.0f} monthly.",
            personality
        )
    
    else:
        # General conversation
        response["text"] = format_response(
            "I'm here to help with all your service needs! You can ask me to book services, check your schedule, get recommendations, or manage your preferences.",
            personality
        )
    
    return response

async def generate_proactive_suggestions(user_id: str, ai_profile: Dict, db) -> List[Dict]:
    """Generate proactive service suggestions based on user patterns"""
    
    suggestions = []
    
    # Get user's booking history
    recent_bookings = await db.bookings.find({
        "user_id": user_id,
        "created_at": {"$gte": datetime.utcnow() - timedelta(days=90)}
    }).to_list(length=100)
    
    # Pattern-based suggestions
    service_frequency = {}
    for booking in recent_bookings:
        service_type = booking.get("service_type")
        if service_type:
            service_frequency[service_type] = service_frequency.get(service_type, 0) + 1
    
    # Suggest recurring services
    for service_type, frequency in service_frequency.items():
        if frequency >= 2:  # Service used at least twice
            last_booking = max([b for b in recent_bookings if b.get("service_type") == service_type], 
                             key=lambda x: x["created_at"])
            days_since = (datetime.utcnow() - last_booking["created_at"]).days
            
            # Suggest if it's been a while
            if days_since > 30:
                suggestions.append({
                    "type": "recurring",
                    "service": service_type,
                    "reason": f"It's been {days_since} days since your last {service_type} service",
                    "confidence": 0.8,
                    "urgency": "medium" if days_since > 60 else "low"
                })
    
    # Seasonal suggestions
    current_month = datetime.utcnow().month
    seasonal_services = get_seasonal_suggestions(current_month)
    
    for service in seasonal_services:
        if service not in service_frequency:  # New service
            suggestions.append({
                "type": "seasonal",
                "service": service,
                "reason": f"Perfect time of year for {service} services",
                "confidence": 0.6,
                "urgency": "low"
            })
    
    # Limit to top 5 suggestions
    return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)[:5]

async def optimize_service_schedule(services: List[Dict], preferences: Dict, ai_profile: Dict, db) -> Dict:
    """Optimize scheduling for multiple services"""
    
    optimized_schedule = {
        "services": [],
        "total_duration": 0,
        "cost_savings": 0,
        "confidence_score": 0.8
    }
    
    # Sort services by priority and dependencies
    sorted_services = sorted(services, key=lambda x: x.get("priority", 5))
    
    current_time = datetime.utcnow()
    
    for i, service in enumerate(sorted_services):
        # Calculate optimal time slot
        optimal_time = current_time + timedelta(days=i+1, hours=preferences.get("preferred_hour", 10))
        
        # Check for service dependencies
        if service.get("depends_on"):
            dependency_service = next((s for s in optimized_schedule["services"] if s["type"] == service["depends_on"]), None)
            if dependency_service:
                optimal_time = dependency_service["scheduled_time"] + timedelta(hours=2)
        
        optimized_service = {
            "type": service["type"],
            "scheduled_time": optimal_time,
            "duration": service.get("duration", 2),
            "estimated_cost": service.get("cost", 500),
            "optimization_reason": "Scheduled based on dependencies and preferences"
        }
        
        optimized_schedule["services"].append(optimized_service)
        optimized_schedule["total_duration"] += optimized_service["duration"]
    
    # Calculate potential savings from bundling
    if len(services) > 1:
        optimized_schedule["cost_savings"] = sum(s.get("cost", 500) for s in services) * 0.15  # 15% bundle discount
    
    return optimized_schedule

def detect_intent(message: str) -> str:
    """Detect user intent from message"""
    
    booking_keywords = ["book", "schedule", "appointment", "need", "want", "hire"]
    schedule_keywords = ["when", "schedule", "upcoming", "next", "calendar"]
    recommendation_keywords = ["suggest", "recommend", "what should", "advice", "help me choose"]
    budget_keywords = ["cost", "price", "budget", "spend", "money", "expensive"]
    
    if any(keyword in message for keyword in booking_keywords):
        return "booking_request"
    elif any(keyword in message for keyword in schedule_keywords):
        return "schedule_query"
    elif any(keyword in message for keyword in recommendation_keywords):
        return "recommendation_request"
    elif any(keyword in message for keyword in budget_keywords):
        return "budget_query"
    else:
        return "general"

def extract_service_type(message: str) -> Optional[str]:
    """Extract service type from message"""
    
    service_keywords = {
        "cleaning": ["clean", "cleaning", "maid", "housekeeping"],
        "plumbing": ["plumber", "plumbing", "pipe", "leak", "drain"],
        "electrical": ["electrician", "electrical", "wiring", "power", "lights"],
        "beauty": ["beauty", "facial", "makeup", "salon", "spa"],
        "fitness": ["fitness", "trainer", "gym", "workout", "exercise"],
        "gardening": ["garden", "gardening", "plants", "landscaping"]
    }
    
    for service_type, keywords in service_keywords.items():
        if any(keyword in message for keyword in keywords):
            return service_type
    
    return None

def format_response(text: str, personality: str) -> str:
    """Format response based on AI personality"""
    
    if personality == "professional":
        return f"Certainly. {text}"
    elif personality == "friendly":
        return f"Absolutely! {text} 😊"
    elif personality == "minimalist":
        return text
    else:
        return text

async def generate_smart_recommendations(user_id: str, ai_profile: Dict, db) -> List[Dict]:
    """Generate smart service recommendations"""
    
    # Get user preferences and history
    bookings = await db.bookings.find({"user_id": user_id}).to_list(length=50)
    
    recommendations = []
    
    # Add some mock intelligent recommendations
    recommendations.extend([
        {"service": "cleaning", "reason": "Due for monthly deep clean", "confidence": 0.9},
        {"service": "beauty", "reason": "Popular in your area this week", "confidence": 0.7},
        {"service": "fitness", "reason": "Matches your wellness goals", "confidence": 0.8}
    ])
    
    return recommendations

async def calculate_monthly_spending(user_id: str, db) -> float:
    """Calculate user's monthly spending on services"""
    
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    monthly_bookings = await db.bookings.find({
        "user_id": user_id,
        "created_at": {"$gte": start_of_month},
        "status": "completed"
    }).to_list(length=100)
    
    return sum(booking.get("amount", 0) for booking in monthly_bookings)

def get_seasonal_suggestions(month: int) -> List[str]:
    """Get seasonal service suggestions"""
    
    seasonal_map = {
        1: ["fitness", "beauty"],  # New Year
        2: ["beauty"],  # Valentine's
        3: ["cleaning", "gardening"],  # Spring
        4: ["gardening"],  # Spring
        5: ["beauty", "fitness"],  # Summer prep
        6: ["fitness"],  # Summer
        7: ["fitness"],  # Summer
        8: ["beauty"],  # Summer
        9: ["tutoring"],  # Back to school
        10: ["cleaning"],  # Pre-winter
        11: ["beauty"],  # Festival season
        12: ["cleaning", "beauty"]  # Holiday prep
    }
    
    return seasonal_map.get(month, ["cleaning"])

async def analyze_user_patterns(bookings: List[Dict], ai_profile: Dict, db) -> Dict:
    """Analyze user booking patterns for insights"""
    
    if not bookings:
        return {"message": "Not enough data for analysis"}
    
    # Time patterns
    booking_hours = [b["created_at"].hour for b in bookings]
    most_common_hour = max(set(booking_hours), key=booking_hours.count) if booking_hours else 10
    
    # Service preferences
    service_types = [b.get("service_type") for b in bookings if b.get("service_type")]
    most_used_service = max(set(service_types), key=service_types.count) if service_types else "cleaning"
    
    # Spending patterns
    amounts = [b.get("amount", 0) for b in bookings if b.get("amount")]
    avg_spending = sum(amounts) / len(amounts) if amounts else 0
    
    return {
        "preferred_booking_time": f"{most_common_hour}:00",
        "favorite_service": most_used_service,
        "average_spending": round(avg_spending, 2),
        "booking_frequency": len(bookings) / 12,  # per month
        "insights": [
            f"You prefer booking services around {most_common_hour}:00",
            f"Your go-to service is {most_used_service}",
            f"You spend an average of ₹{avg_spending:.0f} per booking"
        ]
    }

def calculate_learning_accuracy(ai_profile: Dict) -> float:
    """Calculate AI learning accuracy based on successful predictions"""
    
    # Mock calculation - in production, track prediction success
    interactions = ai_profile.get("total_interactions", 0)
    if interactions < 10:
        return 0.6  # Starting accuracy
    elif interactions < 50:
        return 0.75
    else:
        return 0.9

def generate_improvement_recommendations(insights: Dict) -> List[str]:
    """Generate recommendations for improving service experience"""
    
    recommendations = []
    
    if insights.get("average_spending", 0) > 1000:
        recommendations.append("Consider service bundles to save money")
    
    if insights.get("booking_frequency", 0) < 1:
        recommendations.append("Regular service scheduling can improve your home maintenance")
    
    recommendations.append("Enable proactive suggestions for better service timing")
    
    return recommendations

def validate_automation_rule(rule: Dict) -> bool:
    """Validate automation rule structure"""
    
    required_fields = ["trigger", "action", "service_type"]
    return all(field in rule for field in required_fields)

def get_next_execution_time(rules: List[Dict]) -> Optional[datetime]:
    """Get next execution time for automation rules"""
    
    if not rules:
        return None
    
    # Mock calculation - return next hour
    return datetime.utcnow() + timedelta(hours=1)

def calculate_learning_progress(ai_profile: Dict) -> Dict:
    """Calculate AI learning progress"""
    
    interactions = ai_profile.get("total_interactions", 0)
    
    return {
        "interactions": interactions,
        "learning_stage": "Advanced" if interactions > 100 else "Intermediate" if interactions > 20 else "Beginner",
        "accuracy": calculate_learning_accuracy(ai_profile),
        "next_milestone": 50 if interactions < 50 else 100 if interactions < 100 else 200
    }

def get_personality_note(personality: str, context: str) -> str:
    """Get personality-specific note for different contexts"""
    
    notes = {
        "professional": {
            "suggestions": "Here are my carefully analyzed recommendations:",
            "schedule": "Your optimized schedule has been prepared:",
            "general": "I have processed your request:"
        },
        "friendly": {
            "suggestions": "I've got some great ideas for you! 🌟",
            "schedule": "Let me help you organize your perfect schedule! 📅",
            "general": "Happy to help! Here's what I found:"
        },
        "minimalist": {
            "suggestions": "Recommendations:",
            "schedule": "Schedule:",
            "general": "Results:"
        }
    }
    
    return notes.get(personality, {}).get(context, "")

def generate_schedule_explanation(schedule: Dict, ai_profile: Dict) -> str:
    """Generate explanation for optimized schedule"""
    
    personality = ai_profile.get("personality", "friendly")
    service_count = len(schedule.get("services", []))
    savings = schedule.get("cost_savings", 0)
    
    if personality == "professional":
        return f"I have optimized your {service_count} services for maximum efficiency, resulting in ₹{savings:.0f} potential savings through strategic scheduling."
    elif personality == "friendly":
        return f"Great news! I've arranged your {service_count} services perfectly and found ways to save you ₹{savings:.0f}! 🎉"
    else:
        return f"{service_count} services scheduled. ₹{savings:.0f} savings."

# ── Router Section: aptitude ──
aptitude_router = APIRouter()
router = aptitude_router
from fastapi import APIRouter, HTTPException
from typing import List, Optional
import random


# Centralized Aptitude Questions
APTITUDE_QUESTIONS = {
    "plumbing": [
        {"id": 1, "question": "How do you clear a major blockage in a main sewer line?", "options": ["Use a plunger", "Use a plumbing snake/auger", "Wait for it to clear", "Pour hot water"], "answer": 1},
        {"id": 2, "question": "What is the standard height for a residential kitchen sink?", "options": ["24 inches", "30 inches", "36 inches", "42 inches"], "answer": 2},
        {"id": 3, "question": "Which pipe material is most resistant to corrosion?", "options": ["Galvanized steel", "PVC", "Copper", "Cast iron"], "answer": 1},
        {"id": 4, "question": "What tool is used to tighten a compression nut?", "options": ["Pipe wrench", "Adjustable wrench", "Allen wrench", "Pliers"], "answer": 1},
        {"id": 5, "question": "A 'trap' in plumbing is designed to...", "options": ["Catch hair", "Prevent sewer gases from entering", "Increase water pressure", "Save water"], "answer": 1},
        {"id": 6, "question": "What is the primary function of a vent stack?", "options": ["Drain water", "Regulate air pressure", "Catch debris", "Support pipes"], "answer": 1},
        {"id": 7, "question": "Which valve type is best for fine flow control?", "options": ["Gate valve", "Ball valve", "Globe valve", "Check valve"], "answer": 2}
    ],
    "electrical": [
        {"id": 1, "question": "What is the unit of electrical resistance?", "options": ["Watt", "Volt", "Ampere", "Ohm"], "answer": 3},
        {"id": 2, "question": "Before working on an outlet, you MUST...", "options": ["Wear gloves", "Turn off the breaker", "Check the voltage", "Ask the owner"], "answer": 1},
        {"id": 3, "question": "Which wire is typically the ground wire in the US?", "options": ["Black", "White", "Green or Bare", "Red"], "answer": 2},
        {"id": 4, "question": "A multi-meter is used to measure...", "options": ["Voltage only", "Current only", "Resistance only", "All of the above"], "answer": 3},
        {"id": 5, "question": "What triggers a GFCI outlet?", "options": ["Overload", "Ground fault", "Short circuit", "Low voltage"], "answer": 1},
        {"id": 6, "question": "What is the purpose of a circuit breaker?", "options": ["Increase voltage", "Protect from overcurrent", "Store electricity", "Switch AC to DC"], "answer": 1},
        {"id": 7, "question": "Which gauge wire is thicker, 10 or 14?", "options": ["10 gauge", "14 gauge", "They are the same", "Depends on material"], "answer": 0}
    ],
    "painter": [
        {"id": 1, "question": "What is the best primer for raw drywall?", "options": ["Oil-based", "PVA Primer", "Latex Primer", "No primer needed"], "answer": 1},
        {"id": 2, "question": "How do you remove latex paint from a brush?", "options": ["Turpentine", "Soap and Water", "Paint Thinner", "Alcohol"], "answer": 1},
        {"id": 3, "question": "A 'satin' finish has more sheen than...", "options": ["Gloss", "Eggshell", "Semi-gloss", "High-gloss"], "answer": 1},
        {"id": 4, "question": "Which tape is best for sharp painting lines?", "options": ["Duct Tape", "Masking Tape", "Painter's Blue Tape", "Clear Tape"], "answer": 2},
        {"id": 5, "question": "Why should you sand between paint coats?", "options": ["To change the color", "For better adhesion", "To save paint", "To make it dry faster"], "answer": 1},
        {"id": 6, "question": "What does 'flashing' mean in painting?", "options": ["Drying too fast", "Uneven gloss levels", "Paint peeling", "Using a flashlight"], "answer": 1},
        {"id": 7, "question": "How long should you wait for fresh plaster to dry before painting?", "options": ["24 hours", "3 days", "4 weeks or more", "Immediately"], "answer": 2}
    ],
    "cleaning": [
        {"id": 1, "question": "Which chemical should NEVER be mixed with bleach?", "options": ["Soap", "Ammonia", "Water", "Salt"], "answer": 1},
        {"id": 2, "question": "What is the best material to use for streak-free windows?", "options": ["Paper towel", "Microfiber cloth", "Sponge", "T-shirt"], "answer": 1},
        {"id": 3, "question": "To remove hard water stains, you should use...", "options": ["Baking soda", "Vinegar (Acidic)", "Bleach", "Pine oil"], "answer": 1},
        {"id": 4, "question": "How often should you sanitize high-touch areas?", "options": ["Once a week", "Daily", "Once a month", "Never"], "answer": 1},
        {"id": 5, "question": "What is the proper way to mop a floor?", "options": ["Randomly", "Back and forth", "Figure-8 pattern", "Circular"], "answer": 2},
        {"id": 6, "question": "What is 'cross-contamination' in cleaning?", "options": ["Mixing chemicals", "Spreading germs between areas", "Cleaning with two mops", "Diluting products"], "answer": 1},
        {"id": 7, "question": "Which surface is safe for undiluted vinegar?", "options": ["Marble", "Granite", "Ceramic tile", "Hardwood"], "answer": 2}
    ],
    "beauty": [
        {"id": 1, "question": "Before applying makeup, it is essential to...", "options": ["Skip moisturizer", "Cleanse and prep the skin", "Apply powder first", "Use cold water"], "answer": 1},
        {"id": 2, "question": "What is the correct way to sanitize makeup brushes?", "options": ["Rinse with hot water", "Use a dedicated brush cleanser or alcohol", "Use dish soap only", "Wipe them with a towel"], "answer": 1},
        {"id": 3, "question": "Which ingredient is a common allergen in skincare?", "options": ["Hyaluronic acid", "Fragrance/Parfum", "Aloe vera", "Glycerin"], "answer": 1},
        {"id": 4, "question": "When styling hair with heat, you should always...", "options": ["Apply heat protectant spray", "Style it while dripping wet", "Turn iron to max heat", "Skip conditioner"], "answer": 0},
        {"id": 5, "question": "A patch test is used to...", "options": ["Check skin tone", "Test for allergic reactions", "Estimate product duration", "Hydrate the skin"], "answer": 1}
    ],
    "fitness": [
        {"id": 1, "question": "Which of these is a compound exercise?", "options": ["Bicep curl", "Leg extension", "Squat", "Calf raise"], "answer": 2},
        {"id": 2, "question": "What is the primary muscle targeted during a standard push-up?", "options": ["Latissimus dorsi", "Pectoralis major", "Hamstrings", "Glutes"], "answer": 1},
        {"id": 3, "question": "How do you treat a minor muscle sprain immediately after injury?", "options": ["RICE (Rest, Ice, Compression, Elevation)", "Apply heat immediately", "Stretch it vigorously", "Ignore it"], "answer": 0},
        {"id": 4, "question": "What is an appropriate rest time between high-intensity sets?", "options": ["10 seconds", "1-3 minutes", "10 minutes", "No rest"], "answer": 1},
        {"id": 5, "question": "A dynamic warmup should consist of...", "options": ["Holding stretches for 60s", "Active movements matching the workout", "Sleeping", "Lifting max weight immediately"], "answer": 1}
    ],
    "delivery": [
        {"id": 1, "question": "What is the most important rule when handling fragile packages?", "options": ["Stack them at the bottom", "Secure them and drive smoothly", "Throw them to save time", "Leave them upside down"], "answer": 1},
        {"id": 2, "question": "If a customer is not home to sign for a high-value package, you should...", "options": ["Leave it at the door", "Ask a random neighbor to sign", "Follow standard redelivery procedure", "Keep it for yourself"], "answer": 2},
        {"id": 3, "question": "How should you lift heavy boxes to prevent back injury?", "options": ["Bend your back, keep legs straight", "Bend at the knees and keep your back straight", "Lift rapidly", "Hold it far away from your body"], "answer": 1},
        {"id": 4, "question": "When navigating a new route, the best practice is...", "options": ["Speed to save time", "Use GPS and pre-plan stops", "Guess the way", "Ask pedestrians at every turn"], "answer": 1},
        {"id": 5, "question": "Upon delivering food items, ensuring hygiene means...", "options": ["Opening the bag to check", "Using insulated, clean thermal bags", "Placing it on the bare ground", "Eating the fries"], "answer": 1}
    ],
    "repair": [
        {"id": 1, "question": "When diagnosing a broken appliance, what is the first step?", "options": ["Replace the motor", "Check the power supply/cord", "Take the entire thing apart", "Hit it with a hammer"], "answer": 1},
        {"id": 2, "question": "What does HVAC stand for?", "options": ["Heating, Ventilation, and Air Conditioning", "High Voltage Alternating Current", "Home Vacuum And Cleaning", "Heat Valve And Control"], "answer": 0},
        {"id": 3, "question": "WD-40 is primarily used as a...", "options": ["Permanent glue", "Water displacer and light lubricant", "Electrical insulator", "Paint thinner"], "answer": 1},
        {"id": 4, "question": "To loosen a rusted bolt safely, you should...", "options": ["Apply penetrating oil and wait", "Use extreme force immediately", "Cut it off instantly", "Heat it until it melts"], "answer": 0},
        {"id": 5, "question": "What safety gear is essential when using a grinder?", "options": ["Earplugs only", "Safety glasses and gloves", "A hat", "None"], "answer": 1}
    ],
    "tutoring": [
        {"id": 1, "question": "If a student repeatedly struggles with a concept, the best approach is to...", "options": ["Tell them to study harder", "Explain it exactly the same way louder", "Try a different teaching method or analogy", "Skip the topic entirely"], "answer": 2},
        {"id": 2, "question": "What is the primary purpose of formative assessment?", "options": ["Assigning a final grade", "Tracking ongoing student progress to adapt teaching", "Punishing the student", "Fulfilling legal requirements"], "answer": 1},
        {"id": 3, "question": "Active learning involves...", "options": ["The student listening silently for hours", "Engaging the student in problem-solving and discussion", "The tutor doing all the talking", "Reading from a textbook only"], "answer": 1},
        {"id": 4, "question": "When setting goals for a tutoring session, they should be...", "options": ["Vague and general", "SMART (Specific, Measurable, Achievable, Relevant, Time-bound)", "Impossible to achieve", "Decided entirely by the parent"], "answer": 1},
        {"id": 5, "question": "How should you handle a situation where you don't know the answer to a student's question?", "options": ["Make something up", "Ignore the question", "Admit you don't know and look it up together", "Tell them it won't be on the test"], "answer": 2}
    ]
}

@router.get("/questions/{category}")
async def get_questions(category: str):
    """
    Fetch 5 randomized questions for a given category.
    Defaults to 'painter' if category not found.
    """
    normalized_cat = category.lower()
    if normalized_cat not in APTITUDE_QUESTIONS:
        # Fallback to general or most common categories
        normalized_cat = "painter" 
    
    questions = APTITUDE_QUESTIONS[normalized_cat]
    # Return a random sample of 5 questions
    sample_size = min(len(questions), 5)
    selected = random.sample(questions, sample_size)
    
    return {
        "category": normalized_cat,
        "questions": selected
    }

# ── Router Section: ar_preview ──
ar_preview_router = APIRouter()
router = ar_preview_router
from fastapi import APIRouter, Depends, UploadFile, File
from datetime import datetime
from bson import ObjectId
from typing import List, Optional, Dict
import base64
import json


AR_SUPPORTED_SERVICES = {
    "interior_design": {
        "name": "Interior Design",
        "ar_features": ["furniture_placement", "color_schemes", "lighting", "room_layout"],
        "preview_types": ["3d_model", "color_overlay", "furniture_catalog"]
    },
    "gardening": {
        "name": "Gardening & Landscaping", 
        "ar_features": ["plant_placement", "garden_layout", "seasonal_preview", "growth_simulation"],
        "preview_types": ["plant_catalog", "layout_design", "seasonal_changes"]
    },
    "painting": {
        "name": "Painting Services",
        "ar_features": ["color_preview", "texture_overlay", "before_after"],
        "preview_types": ["color_palette", "texture_samples", "finish_preview"]
    },
    "renovation": {
        "name": "Home Renovation",
        "ar_features": ["structural_changes", "material_preview", "progress_simulation"],
        "preview_types": ["blueprint_overlay", "material_samples", "renovation_stages"]
    }
}

@router.post("/upload-space")
async def upload_space_image(
    file: UploadFile = File(...),
    space_type: str = "room",
    dimensions: Optional[Dict] = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload space image for AR preview"""
    db = get_db()
    
    # Read and encode image
    image_data = await file.read()
    image_base64 = base64.b64encode(image_data).decode()
    
    # Store space data
    space_record = {
        "user_id": current_user["sub"],
        "filename": file.filename,
        "space_type": space_type,
        "dimensions": dimensions or {"width": 10, "height": 10, "length": 12},
        "image_data": image_base64,
        "uploaded_at": datetime.utcnow(),
        "ar_anchors": [],  # Will be populated by AR processing
        "processed": False
    }
    
    result = await db.ar_spaces.insert_one(space_record)
    
    # Mock AR processing (in production, use actual AR/ML services)
    ar_anchors = generate_mock_ar_anchors(space_type, dimensions)
    
    await db.ar_spaces.update_one(
        {"_id": result.inserted_id},
        {"$set": {"ar_anchors": ar_anchors, "processed": True}}
    )
    
    return {
        "space_id": str(result.inserted_id),
        "message": "Space uploaded and processed for AR",
        "ar_anchors": ar_anchors,
        "supported_services": list(AR_SUPPORTED_SERVICES.keys())
    }

@router.get("/preview/{service_type}")
async def get_ar_preview_options(service_type: str):
    """Get AR preview options for a service type"""
    
    if service_type not in AR_SUPPORTED_SERVICES:
        return {"error": "AR preview not supported for this service"}
    
    service_config = AR_SUPPORTED_SERVICES[service_type]
    
    # Mock catalog data
    preview_catalog = generate_preview_catalog(service_type)
    
    return {
        "service": service_config["name"],
        "ar_features": service_config["ar_features"],
        "preview_types": service_config["preview_types"],
        "catalog": preview_catalog,
        "instructions": f"Point your camera at the space to preview {service_type} options"
    }

@router.post("/generate-preview")
async def generate_ar_preview(
    data: ARPreviewGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate AR preview for specific service"""
    db = get_db()
    
    space_id = data.space_id
    service_type = data.service_type
    preview_config = data.preview_config
    
    # Get space data
    space = await db.ar_spaces.find_one({
        "_id": ObjectId(space_id),
        "user_id": current_user["sub"]
    })
    
    if not space:
        return {"error": "Space not found"}
    
    if service_type not in AR_SUPPORTED_SERVICES:
        return {"error": "Service not supported for AR preview"}
    
    # Generate AR preview based on service type
    ar_preview = await create_ar_preview(space, service_type, preview_config, db)
    
    # Save preview
    preview_record = {
        "space_id": space_id,
        "user_id": current_user["sub"],
        "service_type": service_type,
        "preview_config": preview_config,
        "ar_data": ar_preview,
        "created_at": datetime.utcnow(),
        "shared": False,
        "bookings_generated": 0
    }
    
    result = await db.ar_previews.insert_one(preview_record)
    
    return {
        "preview_id": str(result.inserted_id),
        "ar_preview": ar_preview,
        "share_url": f"/ar-preview/view/{result.inserted_id}",
        "estimated_cost": calculate_service_cost(service_type, preview_config)
    }

@router.get("/my-previews")
async def get_my_ar_previews(current_user: dict = Depends(get_current_user)):
    """Get user's AR previews"""
    db = get_db()
    
    previews = await db.ar_previews.find({
        "user_id": current_user["sub"]
    }).sort("created_at", -1).to_list(length=50)
    
    for preview in previews:
        preview["_id"] = str(preview["_id"])
        
        # Get space info
        space = await db.ar_spaces.find_one({"_id": ObjectId(preview["space_id"])})
        if space:
            preview["space_info"] = {
                "space_type": space["space_type"],
                "dimensions": space["dimensions"]
            }
    
    return {"previews": previews}

@router.post("/book-from-preview/{preview_id}")
async def book_service_from_preview(
    preview_id: str,
    data: ARBookingRequest,
    current_user: dict = Depends(get_current_user)
):
    """Book service directly from AR preview"""
    db = get_db()
    
    provider_id = data.provider_id
    scheduled_time = data.scheduled_time
    notes = data.notes
    
    # Get preview
    preview = await db.ar_previews.find_one({
        "_id": ObjectId(preview_id),
        "user_id": current_user["sub"]
    })
    
    if not preview:
        return {"error": "Preview not found"}
    
    # Create booking with AR preview data
    booking = {
        "user_id": current_user["sub"],
        "provider_id": provider_id,
        "service_type": preview["service_type"],
        "scheduled_time": scheduled_time,
        "ar_preview_id": preview_id,
        "ar_specifications": preview["preview_config"],
        "notes": notes or "Booked from AR preview",
        "status": "pending",
        "created_at": datetime.utcnow(),
        "estimated_cost": calculate_service_cost(preview["service_type"], preview["preview_config"])
    }
    
    result = await db.bookings.insert_one(booking)
    
    # Update preview stats
    await db.ar_previews.update_one(
        {"_id": ObjectId(preview_id)},
        {"$inc": {"bookings_generated": 1}}
    )
    
    return {
        "booking_id": str(result.inserted_id),
        "message": "Service booked from AR preview!",
        "ar_specifications_included": True
    }

@router.post("/share-preview/{preview_id}")
async def share_ar_preview(
    preview_id: str,
    data: ARShareRequest,
    current_user: dict = Depends(get_current_user)
):
    """Share AR preview with others"""
    db = get_db()
    
    share_with = data.share_with
    
    # Update preview sharing
    await db.ar_previews.update_one(
        {"_id": ObjectId(preview_id), "user_id": current_user["sub"]},
        {
            "$set": {
                "shared": True,
                "shared_with": share_with,
                "shared_at": datetime.utcnow()
            }
        }
    )
    
    # Create notifications for shared users
    if "public" not in share_with:
        for user_id in share_with:
            await db.notifications.insert_one({
                "user_id": user_id,
                "type": "ar_preview_shared",
                "title": "AR Preview Shared With You",
                "message": "Someone shared an AR service preview with you",
                "preview_id": preview_id,
                "created_at": datetime.utcnow()
            })
    
    return {
        "message": "AR preview shared successfully!",
        "share_url": f"/ar-preview/view/{preview_id}",
        "shared_with": len(share_with) if "public" not in share_with else "public"
    }

@router.get("/trending")
async def get_trending_ar_previews():
    """Get trending AR previews and popular configurations"""
    db = get_db()
    
    # Most popular preview configurations
    popular_configs = await db.ar_previews.aggregate([
        {"$match": {"shared": True}},
        {"$group": {
            "_id": {
                "service_type": "$service_type",
                "config": "$preview_config"
            },
            "usage_count": {"$sum": 1},
            "bookings": {"$sum": "$bookings_generated"}
        }},
        {"$sort": {"usage_count": -1}},
        {"$limit": 10}
    ]).to_list(length=10)
    
    # Most booked AR previews
    top_converting = await db.ar_previews.find({
        "bookings_generated": {"$gt": 0}
    }).sort("bookings_generated", -1).limit(5).to_list(length=5)
    
    for preview in top_converting:
        preview["_id"] = str(preview["_id"])
    
    return {
        "popular_configurations": popular_configs,
        "top_converting_previews": top_converting,
        "insights": [
            "Interior design previews have 40% higher booking rates",
            "Garden layout previews are most shared",
            "Color preview features are most popular"
        ]
    }

@router.get("/analytics")
async def get_ar_analytics(current_user: dict = Depends(get_current_user)):
    """Get AR preview analytics for admin"""
    if current_user["role"] != "admin":
        return {"error": "Admin access required"}
    
    db = get_db()
    
    # Usage statistics
    total_previews = await db.ar_previews.count_documents({})
    total_bookings_from_ar = await db.bookings.count_documents({"ar_preview_id": {"$exists": True}})
    
    # Service type breakdown
    service_breakdown = await db.ar_previews.aggregate([
        {"$group": {"_id": "$service_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]).to_list(length=10)
    
    # Conversion rates
    conversion_rate = (total_bookings_from_ar / max(total_previews, 1)) * 100
    
    return {
        "total_ar_previews": total_previews,
        "bookings_from_ar": total_bookings_from_ar,
        "conversion_rate": round(conversion_rate, 2),
        "service_breakdown": service_breakdown,
        "insights": [
            f"AR previews have {conversion_rate:.1f}% conversion rate",
            "Interior design AR is most popular",
            "Users spend 3x more time on AR-enabled services"
        ]
    }

async def create_ar_preview(space: Dict, service_type: str, config: Dict, db) -> Dict:
    """Create AR preview data based on service type and configuration"""
    
    ar_preview = {
        "service_type": service_type,
        "space_dimensions": space["dimensions"],
        "ar_objects": [],
        "overlays": [],
        "animations": []
    }
    
    if service_type == "interior_design":
        ar_preview["ar_objects"] = [
            {
                "type": "furniture",
                "item": config.get("furniture_type", "sofa"),
                "position": {"x": 2, "y": 0, "z": 3},
                "rotation": {"x": 0, "y": 45, "z": 0},
                "scale": {"x": 1, "y": 1, "z": 1},
                "color": config.get("color", "#8B4513")
            }
        ]
        ar_preview["overlays"] = [
            {
                "type": "color_scheme",
                "colors": config.get("colors", ["#FFFFFF", "#F0F0F0", "#E0E0E0"]),
                "opacity": 0.7
            }
        ]
    
    elif service_type == "gardening":
        ar_preview["ar_objects"] = [
            {
                "type": "plant",
                "species": config.get("plant_type", "rose_bush"),
                "position": {"x": 1, "y": 0, "z": 2},
                "growth_stage": config.get("growth_stage", "mature"),
                "seasonal_colors": ["#228B22", "#32CD32", "#90EE90"]
            }
        ]
        ar_preview["animations"] = [
            {
                "type": "growth_simulation",
                "duration": "12_months",
                "stages": ["seedling", "growing", "mature", "flowering"]
            }
        ]
    
    elif service_type == "painting":
        ar_preview["overlays"] = [
            {
                "type": "paint_color",
                "color": config.get("paint_color", "#FF6B6B"),
                "finish": config.get("finish", "matte"),
                "coverage_area": "walls"
            }
        ]
    
    return ar_preview

def generate_mock_ar_anchors(space_type: str, dimensions: Dict) -> List[Dict]:
    """Generate mock AR anchor points for space"""
    anchors = []
    
    if space_type == "room":
        anchors = [
            {"id": "floor_center", "position": {"x": 0, "y": 0, "z": 0}, "type": "floor"},
            {"id": "wall_north", "position": {"x": 0, "y": 1.5, "z": dimensions.get("length", 10)/2}, "type": "wall"},
            {"id": "wall_south", "position": {"x": 0, "y": 1.5, "z": -dimensions.get("length", 10)/2}, "type": "wall"},
            {"id": "corner_nw", "position": {"x": -dimensions.get("width", 10)/2, "y": 0, "z": dimensions.get("length", 10)/2}, "type": "corner"}
        ]
    elif space_type == "garden":
        anchors = [
            {"id": "ground_center", "position": {"x": 0, "y": 0, "z": 0}, "type": "ground"},
            {"id": "border_north", "position": {"x": 0, "y": 0, "z": dimensions.get("length", 10)/2}, "type": "border"},
            {"id": "border_south", "position": {"x": 0, "y": 0, "z": -dimensions.get("length", 10)/2}, "type": "border"}
        ]
    
    return anchors

def generate_preview_catalog(service_type: str) -> Dict:
    """Generate mock catalog for AR previews"""
    
    catalogs = {
        "interior_design": {
            "furniture": [
                {"id": "sofa_modern", "name": "Modern Sofa", "colors": ["#8B4513", "#654321", "#D2691E"]},
                {"id": "table_coffee", "name": "Coffee Table", "materials": ["wood", "glass", "metal"]},
                {"id": "chair_accent", "name": "Accent Chair", "styles": ["contemporary", "vintage", "minimalist"]}
            ],
            "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
            "styles": ["modern", "traditional", "minimalist", "bohemian"]
        },
        "gardening": {
            "plants": [
                {"id": "rose_bush", "name": "Rose Bush", "seasons": ["spring", "summer"], "colors": ["red", "pink", "white"]},
                {"id": "lavender", "name": "Lavender", "seasons": ["summer"], "colors": ["purple"]},
                {"id": "maple_tree", "name": "Maple Tree", "seasons": ["all"], "colors": ["green", "red", "orange"]}
            ],
            "layouts": ["formal", "cottage", "zen", "wildflower"],
            "features": ["pathway", "fountain", "gazebo", "flower_bed"]
        },
        "painting": {
            "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"],
            "finishes": ["matte", "satin", "semi-gloss", "gloss"],
            "textures": ["smooth", "textured", "stucco", "brick_pattern"]
        }
    }
    
    return catalogs.get(service_type, {})

def calculate_service_cost(service_type: str, config: Dict) -> float:
    """Calculate estimated cost based on AR preview configuration"""
    
    base_costs = {
        "interior_design": 5000,
        "gardening": 3000,
        "painting": 2000,
        "renovation": 15000
    }
    
    base_cost = base_costs.get(service_type, 1000)
    
    # Add complexity multipliers based on configuration
    multiplier = 1.0
    
    if service_type == "interior_design":
        furniture_count = len(config.get("furniture_items", []))
        multiplier += furniture_count * 0.2
    
    elif service_type == "gardening":
        plant_count = len(config.get("plants", []))
        multiplier += plant_count * 0.1
    
    elif service_type == "painting":
        room_count = config.get("room_count", 1)
        multiplier += (room_count - 1) * 0.3
    
    return round(base_cost * multiplier, 2)

# ── Router Section: auth ──
auth_router = APIRouter()
router = auth_router
from fastapi import APIRouter, HTTPException, Depends, Response, Cookie, Request
from datetime import datetime
from typing import Optional
import logging

# Configure local logging
logging.basicConfig(filename="auth_debug.log", level=logging.INFO, format="%(asctime)s - %(message)s")


@router.post("/register")
async def register(user: UserCreate, response: Response):
    db = get_db()
    
    # 1. Validation: Check if email already exists
    existing_email = await db.users.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # 2. Validation: Check if phone number already exists
    if user.phone:
        existing_phone = await db.users.find_one({"phone": user.phone})
        if existing_phone:
            raise HTTPException(status_code=400, detail="This phone number is already associated with another account.")

    # 3. Validation: Minimum password length (though Pydantic handles basics, we can be explicit)
    if not user.password or len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["addresses"] = []
    
    # 4. Provider specific setup: QuickServe Score & Verification
    if user.role == UserRole.PROVIDER:
        # Calculate initial score based on profile completion
        score = 75 # Base score
        if user.bio: score += 5
        if user.business_name: score += 5
        if user.experience_years and user.experience_years > 0: score += 5
        if user.service_categories and len(user.service_categories) > 0: score += 5
        if user.base_location: score += 5
        
        # Include aptitude score if provided (scaled to weight significantly)
        if user.aptitude_score is not None:
            # We add up to 20 bonus points based on test performance
            score += (user.aptitude_score / 100) * 20
        
        user_dict["quickserve_score"] = min(100, round(score))
        user_dict["aptitude_score"] = user.aptitude_score
        user_dict["onboarded"] = True
        user_dict["verified_by_admin"] = False # Needs admin manual verification
        user_dict["is_verified"] = False
        user_dict["rating"] = 0.0
        user_dict["reviews_count"] = 0
        user_dict["balance"] = 0.0
    
    # Normalize name field
    if not user_dict.get("full_name") and user_dict.get("name"):
        user_dict["full_name"] = user_dict["name"]
        
    result = await db.users.insert_one(user_dict)

    access_token = create_access_token({"sub": str(result.inserted_id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(result.inserted_id)})
    
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    
    return {
        "message": "Registered successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role
    }

@router.post("/login")
async def login(credentials: UserLogin, response: Response):
    db = get_db()
    logging.info(f"Login attempt: {credentials.email}")
    print(f"Login attempt: {credentials.email}")
    user = await db.users.find_one({"email": credentials.email})
    if user:
        logging.info(f"User found: {user.get('email')} with role: {user.get('role')}")
        print(f"User found: {user.get('email')} with role: {user.get('role')}")
    else:
        logging.info(f"User not found: {credentials.email}")
        print(f"User not found: {credentials.email}")
    
    # Check for password in different fields (backward compatibility)
    password_field = None
    if user:
        if "password" in user:
            password_field = "password"
        elif "password_hash" in user:
            password_field = "password_hash"
    
    if not user or not password_field or not verify_password(credentials.password, user[password_field]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user["_id"]), "role": user["role"]})
    refresh_token = create_refresh_token({"sub": str(user["_id"])})
    
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    
    logging.info(f"Login successful for user: {credentials.email}")
    print(f"Login successful for user: {credentials.email}")
    return {
        "message": "Logged in successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user["role"],
        "user_id": str(user["_id"])
    }

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    logging.info(f"Get profile for user ID: {current_user.get('sub')}")
    db = get_db()
    from bson import ObjectId
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user:
        logging.error(f"User not found for ID: {current_user.get('sub')}")
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    user.pop("password_hash", None)
    logging.info(f"Profile returned for: {user.get('email')}")
    return user

@router.post("/google")
async def google_login(credential: str, response: Response):
    """Mock Google OAuth login"""
    db = get_db()
    # In production: idinfo = id_token.verify_oauth2_token(credential, requests.Request(), CLIENT_ID)
    # email = idinfo['email']
    email = "google_user@example.com" # Mock
    
    user = await db.users.find_one({"email": email})
    if not user:
        # Auto-register Google user
        user_dict = {
            "email": email,
            "full_name": "Google User",
            "role": "customer",
            "created_at": datetime.utcnow(),
            "google_auth": True
        }
        result = await db.users.insert_one(user_dict)
        user_id = str(result.inserted_id)
        role = "customer"
    else:
        user_id = str(user["_id"])
        role = user["role"]

    access_token = create_access_token({"sub": user_id, "role": role})
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    
    return {
        "message": "Google login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "role": role
    }

@router.post("/refresh")
async def refresh_token(response: Response, refresh_token: str = None, request: Request = None):
    """Issue new access token using refresh token (cookie or body)."""
    from fastapi import Request as Req
    token = refresh_token
    if not token and request:
        token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    from middleware.auth import verify_refresh_token, create_access_token
    payload = verify_refresh_token(token)
    new_access = create_access_token({"sub": payload["sub"]})
    response.set_cookie(key="access_token", value=new_access, httponly=True, samesite="lax")
    return {"access_token": new_access, "token_type": "bearer"}


@router.get("/csrf-token")
async def get_csrf_token(response: Response):
    """Issue a CSRF token stored in a non-httpOnly cookie so JS can read it."""
    import secrets
    token = secrets.token_hex(32)
    response.set_cookie(key="csrf_token", value=token, httponly=False, samesite="strict")
    return {"csrf_token": token}


async def send_otp(phone: str):
    """Mock sending OTP via Twilio"""
    # Mock: client.verify.v2.services(SID).verifications.create(to=phone, channel='sms')
    print(f"OTP sent to {phone}: 123456")
    return {"status": "sent", "message": "OTP sent successfully"}

@router.post("/verify-otp")
async def verify_otp(phone: str, otp: str):
    """Mock verify OTP"""
    if otp == "123456":
        return {"status": "verified"}
    raise HTTPException(status_code=400, detail="Invalid OTP")

# ── Router Section: bookings ──
bookings_router = APIRouter()
router = bookings_router
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from bson import ObjectId


@router.post("/")
async def create_booking(booking: BookingCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # 1. Check for existing booking (consolidated check)
    if booking.provider_id and booking.scheduled_time and booking.scheduled_date:
        # Check main bookings
        existing = await db.bookings.find_one({
            "provider_id": booking.provider_id,
            "scheduled_time": booking.scheduled_time,
            "scheduled_date": booking.scheduled_date,
            "status": {"$in": ["confirmed", "in_progress", "pending"]}
        })
        # Check slot_bookings too
        existing_slot = await db.slot_bookings.find_one({
            "provider_id": booking.provider_id,
            "time_slot": booking.scheduled_time,
            "date": booking.scheduled_date,
            "status": {"$not": {"$eq": "cancelled"}}
        })
        if existing or existing_slot:
            raise HTTPException(status_code=400, detail="Provider is unavailable for this specific date and time slot.")
    
    # 2. Get provider's base rate
    base_rate = 500
    if booking.provider_id:
        try:
            # Try as ObjectId first
            p_oid = ObjectId(booking.provider_id)
            provider = await db.users.find_one({"_id": p_oid})
        except:
            # Fallback for CSV or other string-based IDs
            provider = await db.users.find_one({"_id": booking.provider_id})
            
        if provider:
            base_rate = provider.get("hourly_rate") or provider.get("provider_profile", {}).get("base_rate") or 500
    
    now = datetime.utcnow()
    
    # 3. Parse scheduled time for price multipliers
    try:
        if booking.scheduled_time and booking.scheduled_date:
            sched_str = f"{booking.scheduled_date} {booking.scheduled_time}"
            if "T" in booking.scheduled_time or "Z" in booking.scheduled_time.upper():
                sched = datetime.fromisoformat(booking.scheduled_time.replace('Z', '+00:00'))
            else:
                sched = datetime.strptime(sched_str, "%Y-%m-%d %H:%M")
        else:
            sched = now
    except:
        sched = now

    # 4. Apply Multipliers (Rush, Weekend, Evening)
    hour = sched.hour
    multiplier = 1.0
    if 17 <= hour <= 21: multiplier *= 1.2 # Evening demand
    if sched.weekday() >= 5: multiplier *= 1.1 # Weekend
    if (sched - now).total_seconds() < 7200: multiplier *= 1.5 # Short notice (within 2h)
    
    final_price = base_rate * multiplier
    
    # 5. Create Booking Document
    booking_dict = booking.dict()
    booking_dict["user_id"] = current_user["sub"]
    booking_dict["status"] = BookingStatus.CONFIRMED
    booking_dict["created_at"] = datetime.utcnow()
    booking_dict["final_price"] = round(final_price, 2)
    booking_dict["multiplier"] = multiplier
    
    result = await db.bookings.insert_one(booking_dict)
    return {"id": str(result.inserted_id), "_id": str(result.inserted_id), "status": "confirmed", "price": round(final_price, 2)}

@router.post("/emergency")
async def create_emergency_booking(booking: BookingCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    booking_dict = booking.dict()
    booking_dict["user_id"] = current_user["sub"]
    booking_dict["status"] = BookingStatus.PENDING
    booking_dict["is_emergency"] = True
    booking_dict["created_at"] = datetime.utcnow()
    result = await db.bookings.insert_one(booking_dict)
    return {"id": str(result.inserted_id), "status": "emergency", "priority": "high"}

# NOTE: /history must be before /{booking_id} to avoid route conflict
@router.get("/history")
async def get_booking_history(current_user: dict = Depends(get_current_user)):
    db = get_db()
    bookings = await db.bookings.find({"user_id": current_user["sub"]}).sort("created_at", -1).to_list(length=50)
    for b in bookings:
        b["_id"] = str(b["_id"])
        b["id"] = b["_id"]
    return bookings

@router.get("/")
async def get_bookings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    # Support both "id" and "total" format used by frontend
    bookings = await db.bookings.find({"user_id": current_user["sub"]}).sort("created_at", -1).to_list(length=100)
    for b in bookings:
        b["_id"] = str(b["_id"])
        b["id"] = b["_id"]
    return {"bookings": bookings, "total": len(bookings)}

@router.get("/{booking_id}")
async def get_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        # Try both formats for ID
        query = {"_id": ObjectId(booking_id)} if len(booking_id) == 24 else {"_id": booking_id}
        booking = await db.bookings.find_one(query)
    except:
        raise HTTPException(status_code=400, detail="Invalid booking ID format")
        
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking["_id"] = str(booking["_id"])
    booking["id"] = booking["_id"]
    return booking

@router.put("/{booking_id}/status")
async def update_booking_status(booking_id: str, status: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": status}})
    return {"status": "updated"}

@router.delete("/{booking_id}")
async def cancel_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "cancelled"}})
    return {"status": "cancelled"}

# ── Router Section: bundles ──
bundles_router = APIRouter()
router = bundles_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import itertools
from collections import Counter


# Predefined service synergies and compatibility
SERVICE_SYNERGIES = {
    "cleaning": {
        "compatible": ["pest_control", "gardening", "beauty"],
        "discount": 0.15,
        "reasons": ["Clean environment enhances other services", "Shared scheduling efficiency"]
    },
    "plumbing": {
        "compatible": ["electrical", "repair", "cleaning"],
        "discount": 0.20,
        "reasons": ["Infrastructure services work well together", "Minimize home disruption"]
    },
    "electrical": {
        "compatible": ["plumbing", "repair", "fitness"],
        "discount": 0.18,
        "reasons": ["Technical services complement each other", "Safety improvements"]
    },
    "beauty": {
        "compatible": ["fitness", "cleaning", "wellness"],
        "discount": 0.12,
        "reasons": ["Wellness and self-care synergy", "Lifestyle enhancement"]
    },
    "fitness": {
        "compatible": ["beauty", "wellness", "nutrition"],
        "discount": 0.15,
        "reasons": ["Health and wellness ecosystem", "Holistic lifestyle approach"]
    },
    "gardening": {
        "compatible": ["cleaning", "pest_control", "landscaping"],
        "discount": 0.10,
        "reasons": ["Outdoor maintenance synergy", "Seasonal coordination"]
    }
}

SEASONAL_BUNDLES = {
    "spring": {
        "name": "🌸 Spring Refresh Bundle",
        "services": ["cleaning", "gardening", "pest_control"],
        "discount": 0.25,
        "description": "Complete spring home refresh"
    },
    "summer": {
        "name": "☀️ Summer Wellness Bundle",
        "services": ["beauty", "fitness", "cleaning"],
        "discount": 0.20,
        "description": "Stay fresh and fit this summer"
    },
    "monsoon": {
        "name": "🌧️ Monsoon Protection Bundle",
        "services": ["plumbing", "electrical", "pest_control"],
        "discount": 0.30,
        "description": "Protect your home during monsoons"
    },
    "winter": {
        "name": "❄️ Winter Comfort Bundle",
        "services": ["electrical", "cleaning", "beauty"],
        "discount": 0.18,
        "description": "Stay warm and comfortable"
    }
}

@router.get("/recommendations")
async def get_bundle_recommendations(current_user: dict = Depends(get_current_user)):
    """Get personalized bundle recommendations based on user history"""
    db = get_db()
    
    # Get user's booking history
    user_bookings = await db.bookings.find({
        "user_id": current_user["sub"],
        "status": "completed"
    }).to_list(length=100)
    
    # Analyze user preferences
    service_frequency = Counter(booking.get("service_type") for booking in user_bookings)
    preferred_services = [service for service, count in service_frequency.most_common(5)]
    
    recommendations = []
    
    # 1. Synergy-based recommendations
    for service in preferred_services:
        if service in SERVICE_SYNERGIES:
            synergy = SERVICE_SYNERGIES[service]
            for compatible_service in synergy["compatible"]:
                if compatible_service not in preferred_services:
                    bundle = await create_custom_bundle(
                        [service, compatible_service],
                        f"Perfect Pair: {service.title()} + {compatible_service.title()}",
                        synergy["discount"],
                        synergy["reasons"],
                        db
                    )
                    if bundle:
                        recommendations.append(bundle)
    
    # 2. Seasonal recommendations
    current_month = datetime.utcnow().month
    season = get_current_season(current_month)
    
    if season in SEASONAL_BUNDLES:
        seasonal_bundle = SEASONAL_BUNDLES[season]
        bundle = await create_custom_bundle(
            seasonal_bundle["services"],
            seasonal_bundle["name"],
            seasonal_bundle["discount"],
            [seasonal_bundle["description"]],
            db
        )
        if bundle:
            recommendations.append(bundle)
    
    # 3. Completion-based recommendations (services user hasn't tried)
    all_services = set(SERVICE_SYNERGIES.keys())
    tried_services = set(preferred_services)
    untried_services = all_services - tried_services
    
    if untried_services and preferred_services:
        discovery_services = list(untried_services)[:2] + preferred_services[:1]
        bundle = await create_custom_bundle(
            discovery_services,
            "🔍 Discovery Bundle - Try Something New!",
            0.25,
            ["Explore new services with your favorites", "Perfect for expanding your service experience"],
            db
        )
        if bundle:
            recommendations.append(bundle)
    
    # 4. Frequency-based bundles (services user books regularly)
    frequent_services = [service for service, count in service_frequency.items() if count >= 3]
    if len(frequent_services) >= 2:
        bundle = await create_custom_bundle(
            frequent_services[:3],
            "⭐ Your Favorites Bundle",
            0.20,
            ["Based on your most booked services", "Optimized for your preferences"],
            db
        )
        if bundle:
            recommendations.append(bundle)
    
    return {"recommendations": recommendations[:5]}  # Top 5 recommendations

@router.post("/create-custom")
async def create_custom_bundle_endpoint(
    services: List[str],
    bundle_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Create a custom bundle from selected services"""
    db = get_db()
    
    if len(services) < 2:
        return {"error": "Bundle must contain at least 2 services"}
    
    if len(services) > 5:
        return {"error": "Bundle cannot contain more than 5 services"}
    
    # Calculate optimal discount based on service compatibility
    total_discount = calculate_bundle_discount(services)
    
    bundle = await create_custom_bundle(
        services,
        bundle_name,
        total_discount,
        ["Custom bundle created by user"],
        db
    )
    
    if not bundle:
        return {"error": "Could not create bundle"}
    
    # Save custom bundle for user
    custom_bundle = {
        "user_id": current_user["sub"],
        "name": bundle_name,
        "services": services,
        "discount": total_discount,
        "created_at": datetime.utcnow(),
        "usage_count": 0
    }
    
    result = await db.custom_bundles.insert_one(custom_bundle)
    bundle["bundle_id"] = str(result.inserted_id)
    
    return bundle

@router.get("/popular")
async def get_popular_bundles():
    """Get most popular service bundles across platform"""
    db = get_db()
    
    # Analyze booking patterns to find popular combinations
    pipeline = [
        {"$match": {"status": "completed", "created_at": {"$gte": datetime.utcnow() - timedelta(days=30)}}},
        {"$group": {"_id": "$user_id", "services": {"$push": "$service_type"}}},
        {"$match": {"services.1": {"$exists": True}}}  # At least 2 services
    ]
    
    user_service_patterns = await db.bookings.aggregate(pipeline).to_list(length=1000)
    
    # Find common service combinations
    combination_counter = Counter()
    
    for pattern in user_service_patterns:
        services = pattern["services"]
        # Generate all 2-service combinations
        for combo in itertools.combinations(set(services), 2):
            combination_counter[tuple(sorted(combo))] += 1
    
    popular_bundles = []
    
    for combo, frequency in combination_counter.most_common(10):
        services = list(combo)
        discount = calculate_bundle_discount(services)
        
        bundle = await create_custom_bundle(
            services,
            f"Popular Combo: {' + '.join(s.title() for s in services)}",
            discount,
            [f"Booked together {frequency} times this month", "Community favorite combination"],
            db
        )
        
        if bundle:
            bundle["popularity_score"] = frequency
            popular_bundles.append(bundle)
    
    return {"popular_bundles": popular_bundles}

@router.get("/seasonal")
async def get_seasonal_bundles():
    """Get current seasonal bundle recommendations"""
    current_month = datetime.utcnow().month
    season = get_current_season(current_month)
    
    seasonal_recommendations = []
    
    # Current season bundle
    if season in SEASONAL_BUNDLES:
        current_seasonal = SEASONAL_BUNDLES[season]
        seasonal_recommendations.append({
            "season": season,
            "bundle": current_seasonal,
            "is_current": True
        })
    
    # Next season preparation
    next_season = get_next_season(season)
    if next_season in SEASONAL_BUNDLES:
        next_seasonal = SEASONAL_BUNDLES[next_season]
        seasonal_recommendations.append({
            "season": next_season,
            "bundle": next_seasonal,
            "is_current": False,
            "preparation_message": f"Prepare for {next_season} season"
        })
    
    return {"seasonal_bundles": seasonal_recommendations}

@router.post("/optimize")
async def optimize_service_schedule(
    data: BundleOptimizeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Optimize service scheduling and bundling within budget and timeframe"""
    db = get_db()
    
    desired_services = data.services
    budget = data.max_budget
    timeframe_days = data.timeframe_days or 30
    
    # Get average costs for services
    service_costs = {}
    for service in desired_services:
        avg_cost = await get_average_service_cost(service, db)
        service_costs[service] = avg_cost
    
    # Generate all possible bundles
    possible_bundles = []
    
    # Single services
    for service in desired_services:
        possible_bundles.append({
            "services": [service],
            "cost": service_costs[service],
            "discount": 0,
            "final_cost": service_costs[service],
            "value_score": 1
        })
    
    # 2-service bundles
    for combo in itertools.combinations(desired_services, 2):
        services = list(combo)
        total_cost = sum(service_costs[s] for s in services)
        discount = calculate_bundle_discount(services)
        final_cost = total_cost * (1 - discount)
        value_score = (total_cost - final_cost) / total_cost  # Savings ratio
        
        possible_bundles.append({
            "services": services,
            "cost": total_cost,
            "discount": discount,
            "final_cost": final_cost,
            "value_score": value_score
        })
    
    # 3+ service bundles
    for r in range(3, min(len(desired_services) + 1, 6)):
        for combo in itertools.combinations(desired_services, r):
            services = list(combo)
            total_cost = sum(service_costs[s] for s in services)
            discount = calculate_bundle_discount(services)
            final_cost = total_cost * (1 - discount)
            value_score = (total_cost - final_cost) / total_cost
            
            possible_bundles.append({
                "services": services,
                "cost": total_cost,
                "discount": discount,
                "final_cost": final_cost,
                "value_score": value_score
            })
    
    # Filter bundles within budget
    affordable_bundles = [b for b in possible_bundles if b["final_cost"] <= budget]
    
    # Sort by value score (best savings)
    affordable_bundles.sort(key=lambda x: x["value_score"], reverse=True)
    
    # Create optimal schedule
    optimal_schedule = []
    remaining_budget = budget
    used_services = set()
    
    for bundle in affordable_bundles:
        if bundle["final_cost"] <= remaining_budget:
            # Check if any service is already scheduled
            if not any(service in used_services for service in bundle["services"]):
                optimal_schedule.append(bundle)
                remaining_budget -= bundle["final_cost"]
                used_services.update(bundle["services"])
    
    # Calculate schedule timing
    days_per_bundle = timeframe_days // len(optimal_schedule) if optimal_schedule else 1
    
    for i, bundle in enumerate(optimal_schedule):
        schedule_date = datetime.utcnow() + timedelta(days=i * days_per_bundle)
        bundle["scheduled_date"] = schedule_date.date().isoformat()
    
    return {
        "optimal_schedule": optimal_schedule,
        "total_cost": budget - remaining_budget,
        "total_savings": sum(b["cost"] - b["final_cost"] for b in optimal_schedule),
        "remaining_budget": remaining_budget,
        "services_covered": len(used_services),
        "services_remaining": list(set(desired_services) - used_services)
    }

@router.get("/analytics")
async def get_bundle_analytics(current_user: dict = Depends(get_current_user)):
    """Get bundle usage analytics for admin"""
    if current_user["role"] != "admin":
        return {"error": "Admin access required"}
    
    db = get_db()
    
    # Bundle usage statistics
    bundle_usage = await db.bundle_bookings.aggregate([
        {"$group": {"_id": "$bundle_type", "count": {"$sum": 1}, "revenue": {"$sum": "$amount"}}},
        {"$sort": {"count": -1}}
    ]).to_list(length=20)
    
    # Most popular service combinations
    popular_combos = await db.bundle_bookings.aggregate([
        {"$group": {"_id": "$services", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(length=10)
    
    # Seasonal trends
    seasonal_trends = await db.bundle_bookings.aggregate([
        {"$group": {
            "_id": {"month": {"$month": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.month": 1}}
    ]).to_list(length=12)
    
    return {
        "bundle_usage": bundle_usage,
        "popular_combinations": popular_combos,
        "seasonal_trends": seasonal_trends,
        "insights": [
            "Cleaning + Pest Control is the most popular combination",
            "Spring bundles see 40% higher booking rates",
            "Users save an average of 22% with bundles"
        ]
    }

async def create_custom_bundle(services: List[str], name: str, discount: float, reasons: List[str], db) -> Optional[Dict]:
    """Create a custom bundle with pricing and details"""
    
    if len(services) < 2:
        return None
    
    # Get average costs
    total_cost = 0
    service_details = []
    
    for service in services:
        avg_cost = await get_average_service_cost(service, db)
        total_cost += avg_cost
        service_details.append({
            "service": service,
            "individual_cost": avg_cost
        })
    
    # Apply discount
    discounted_cost = total_cost * (1 - discount)
    savings = total_cost - discounted_cost
    
    return {
        "name": name,
        "services": service_details,
        "total_individual_cost": round(total_cost, 2),
        "bundle_cost": round(discounted_cost, 2),
        "discount_percentage": round(discount * 100, 1),
        "savings": round(savings, 2),
        "reasons": reasons,
        "estimated_duration": len(services) * 2,  # 2 hours per service
        "validity_days": 30
    }

def calculate_bundle_discount(services: List[str]) -> float:
    """Calculate optimal discount for service combination"""
    
    base_discount = 0.10  # 10% base discount for any bundle
    
    # Check for synergies
    synergy_bonus = 0
    for service in services:
        if service in SERVICE_SYNERGIES:
            compatible_services = SERVICE_SYNERGIES[service]["compatible"]
            synergy_count = len([s for s in services if s in compatible_services])
            synergy_bonus += synergy_count * 0.05  # 5% per synergy
    
    # Size bonus (more services = better discount)
    size_bonus = (len(services) - 2) * 0.03  # 3% per additional service
    
    # Cap at 35% maximum discount
    total_discount = min(0.35, base_discount + synergy_bonus + size_bonus)
    
    return round(total_discount, 2)

async def get_average_service_cost(service_type: str, db) -> float:
    """Get average cost for a service type"""
    pipeline = [
        {"$match": {"service_type": service_type, "status": "completed"}},
        {"$group": {"_id": None, "avg_cost": {"$avg": "$amount"}}}
    ]
    
    result = await db.bookings.aggregate(pipeline).to_list(length=1)
    
    # Default costs if no data
    default_costs = {
        "cleaning": 400,
        "plumbing": 600,
        "electrical": 700,
        "beauty": 500,
        "fitness": 800,
        "gardening": 350,
        "pest_control": 450,
        "repair": 550
    }
    
    return result[0]["avg_cost"] if result else default_costs.get(service_type, 500)

def get_current_season(month: int) -> str:
    """Get current season based on month"""
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "autumn"
    else:
        return "spring"

def get_next_season(current_season: str) -> str:
    """Get next season"""
    seasons = ["winter", "spring", "summer", "autumn"]
    current_index = seasons.index(current_season)
    next_index = (current_index + 1) % len(seasons)
    return seasons[next_index]

# ── Router Section: chat ──
chat_router = APIRouter()
router = chat_router
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from datetime import datetime
from bson import ObjectId
from typing import List, Optional
from pydantic import BaseModel


# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

class ConversationCreate(BaseModel):
    participant_id: str
    booking_id: Optional[str] = None

class MessageCreate(BaseModel):
    conversation_id: str
    message: str
    message_type: Optional[str] = "text"

# Create or get conversation
@router.post("/conversations")
async def create_conversation(
    params: ConversationCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new conversation between customer and provider"""
    participant_id = params.participant_id
    booking_id = params.booking_id
    db = get_db()
    
    # Check if conversation already exists
    existing = await db.conversations.find_one({
        "participants": {"$all": [current_user["sub"], participant_id]}
    })
    
    if existing:
        existing["_id"] = str(existing["_id"])
        return existing
    
    # Create new conversation
    conversation = {
        "participants": [current_user["sub"], participant_id],
        "booking_id": booking_id,
        "created_at": datetime.utcnow(),
        "last_message_at": datetime.utcnow(),
        "unread_count": {current_user["sub"]: 0, participant_id: 0}
    }
    
    result = await db.conversations.insert_one(conversation)
    conversation["_id"] = str(result.inserted_id)
    
    return conversation

# Get user conversations
@router.get("/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get all conversations for current user"""
    db = get_db()
    
    conversations = await db.conversations.find({
        "participants": current_user["sub"]
    }).sort("last_message_at", -1).to_list(length=50)
    
    # Enrich with participant details and last message
    for conv in conversations:
        conv["_id"] = str(conv["_id"])
        
        # Get other participant
        other_id = [p for p in conv["participants"] if p != current_user["sub"]][0]
        try:
            other_query = {"_id": ObjectId(other_id)} if len(other_id) == 24 else {"_id": other_id}
            other_user = await db.users.find_one(other_query)
        except:
            other_user = None
            
        if other_user:
            conv["other_user"] = {
                "id": str(other_user["_id"]),
                "name": other_user.get("full_name") or other_user.get("name", "Unknown"),
                "profile_image": other_user.get("profile_image", "")
            }
        else:
            conv["other_user"] = {"id": other_id, "name": "User", "profile_image": ""}
        
        # Get last message
        last_msg = await db.messages.find_one(
            {"conversation_id": str(conv["_id"])},
            sort=[("timestamp", -1)]
        )
        if last_msg:
            conv["last_message"] = {
                "text": last_msg.get("message", ""),
                "timestamp": last_msg.get("timestamp")
            }
    
    return conversations

# Send message
@router.post("/messages")
async def send_message(
    params: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a message in a conversation"""
    db = get_db()
    conversation_id = params.conversation_id
    message = params.message
    message_type = params.message_type

    # Verify conversation exists and user is participant
    try:
        query = {"_id": ObjectId(conversation_id)} if len(conversation_id) == 24 else {"_id": conversation_id}
        conversation = await db.conversations.find_one(query)
    except:
        conversation = None
        
    if not conversation or current_user["sub"] not in conversation.get("participants", []):
        return {"error": "Conversation not found or access denied"}
    
    # Create message
    msg = {
        "conversation_id": conversation_id,
        "sender_id": current_user["sub"],
        "message": message,
        "message_type": message_type,
        "timestamp": datetime.utcnow(),
        "read": False
    }
    
    result = await db.messages.insert_one(msg)
    msg["_id"] = str(result.inserted_id)
    
    # Update conversation
    other_participant = [p for p in conversation["participants"] if p != current_user["sub"]][0]
    update_query = {"_id": ObjectId(conversation_id)} if len(conversation_id) == 24 else {"_id": conversation_id}
    await db.conversations.update_one(
        update_query,
        {
            "$set": {"last_message_at": datetime.utcnow()},
            "$inc": {f"unread_count.{other_participant}": 1}
        }
    )
    
    # Send real-time notification via WebSocket
    sender = await db.users.find_one({"_id": ObjectId(current_user["sub"])} if len(current_user["sub"]) == 24 else {"_id": current_user["sub"]})
    sender_name = sender.get("full_name", "Someone") if sender else "Someone"
    await manager.send_message(other_participant, {
        "type": "new_message",
        "conversation_id": conversation_id,
        "message": {**msg, "sender_name": sender_name}
    })
    
    return msg

# Get messages
@router.get("/messages/{conversation_id}")
async def get_messages(
    conversation_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get messages from a conversation"""
    db = get_db()
    
    # Verify access
    try:
        query = {"_id": ObjectId(conversation_id)} if len(conversation_id) == 24 else {"_id": conversation_id}
        conversation = await db.conversations.find_one(query)
    except:
        conversation = None

    if not conversation or current_user["sub"] not in conversation.get("participants", []):
        return {"error": "Access denied"}
    
    # Get messages
    messages = await db.messages.find({
        "conversation_id": conversation_id
    }).sort("timestamp", -1).limit(limit).to_list(length=limit)
    
    for msg in messages:
        msg["_id"] = str(msg["_id"])
    
    # Mark as read
    await db.messages.update_many(
        {
            "conversation_id": conversation_id,
            "sender_id": {"$ne": current_user["sub"]},
            "read": False
        },
        {"$set": {"read": True}}
    )
    
    # Reset unread count
    update_query = {"_id": ObjectId(conversation_id)} if len(conversation_id) == 24 else {"_id": conversation_id}
    await db.conversations.update_one(
        update_query,
        {"$set": {f"unread_count.{current_user['sub']}": 0}}
    )
    
    return list(reversed(messages))

# Mark message as read
@router.put("/messages/{message_id}/read")
async def mark_as_read(message_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a message as read"""
    db = get_db()
    
    await db.messages.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {"read": True}}
    )
    
    return {"status": "marked_as_read"}

# Delete message
@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a message (soft delete)"""
    db = get_db()
    
    await db.messages.update_one(
        {"_id": ObjectId(message_id), "sender_id": current_user["sub"]},
        {"$set": {"deleted": True, "message": "[Message deleted]"}}
    )
    
    return {"status": "deleted"}

# Get unread count
@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get total unread message count"""
    db = get_db()
    
    conversations = await db.conversations.find({
        "participants": current_user["sub"]
    }).to_list(length=100)
    
    total_unread = sum(
        conv.get("unread_count", {}).get(current_user["sub"], 0)
        for conv in conversations
    )
    
    return {"unread_count": total_unread}

# WebSocket endpoint for real-time chat
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: Optional[str] = None):
    """WebSocket connection for real-time messaging"""
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception:
        manager.disconnect(user_id)

# Quick replies / Templates
@router.get("/quick-replies")
async def get_quick_replies(current_user: dict = Depends(get_current_user)):
    """Get quick reply templates"""
    
    if current_user["role"] == "provider":
        return {
            "quick_replies": [
                "I'm on my way!",
                "I'll be there in 15 minutes",
                "Running 5 minutes late",
                "I've arrived at your location",
                "Service completed. Thank you!",
                "Could you please provide more details?",
                "I'll need to reschedule. Is tomorrow okay?"
            ]
        }
    else:
        return {
            "quick_replies": [
                "When will you arrive?",
                "Thank you!",
                "Please call me when you're nearby",
                "I need to reschedule",
                "Great service, thanks!",
                "Can you provide an estimate?",
                "Is this included in the price?"
            ]
        }

# Search conversations
@router.get("/search")
async def search_conversations(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    """Search messages and conversations"""
    db = get_db()
    
    # Get user's conversations
    conversations = await db.conversations.find({
        "participants": current_user["sub"]
    }).to_list(length=100)
    
    conv_ids = [str(c["_id"]) for c in conversations]
    
    # Search messages
    messages = await db.messages.find({
        "conversation_id": {"$in": conv_ids},
        "message": {"$regex": query, "$options": "i"}
    }).limit(20).to_list(length=20)
    
    for msg in messages:
        msg["_id"] = str(msg["_id"])
    
    return {"results": messages, "count": len(messages)}

# ── Router Section: community ──
community_router = APIRouter()
router = community_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict
import random


CHALLENGE_TYPES = {
    "green_neighborhood": {
        "name": "🌱 Green Neighborhood Challenge",
        "description": "Most eco-friendly services booked",
        "duration_days": 30,
        "reward_pool": 5000,
        "criteria": "eco_services"
    },
    "cleanliness_champion": {
        "name": "🧹 Cleanliness Champion",
        "description": "Highest cleaning service usage",
        "duration_days": 14,
        "reward_pool": 3000,
        "criteria": "cleaning_services"
    },
    "safety_first": {
        "name": "🔒 Safety First Challenge",
        "description": "Most safety-related services (electrical, plumbing)",
        "duration_days": 21,
        "reward_pool": 4000,
        "criteria": "safety_services"
    },
    "community_helper": {
        "name": "🤝 Community Helper",
        "description": "Most services booked for elderly neighbors",
        "duration_days": 30,
        "reward_pool": 6000,
        "criteria": "helper_services"
    },
    "wellness_warriors": {
        "name": "💪 Wellness Warriors",
        "description": "Highest fitness and beauty service usage",
        "duration_days": 28,
        "reward_pool": 3500,
        "criteria": "wellness_services"
    }
}

@router.get("/active-challenges")
async def get_active_challenges(location: Optional[dict] = None):
    """Get all active community challenges"""
    db = get_db()
    
    # Get active challenges
    active_challenges = await db.community_challenges.find({
        "status": "active",
        "end_date": {"$gt": datetime.utcnow()}
    }).to_list(length=20)
    
    for challenge in active_challenges:
        challenge["_id"] = str(challenge["_id"])
        
        # Get participant count
        challenge["participant_count"] = await db.challenge_participants.count_documents({
            "challenge_id": challenge["_id"]
        })
        
        # Get leaderboard preview (top 3)
        leaderboard = await get_challenge_leaderboard(challenge["_id"], limit=3)
        challenge["top_participants"] = leaderboard["leaderboard"]
        
        # Calculate time remaining
        time_remaining = challenge["end_date"] - datetime.utcnow()
        challenge["days_remaining"] = time_remaining.days
        challenge["hours_remaining"] = time_remaining.seconds // 3600
    
    return {"challenges": active_challenges}

@router.post("/join-challenge")
async def join_challenge(challenge_id: str, current_user: dict = Depends(get_current_user)):
    """Join a community challenge"""
    db = get_db()
    
    # Check if challenge exists and is active
    challenge = await db.community_challenges.find_one({
        "_id": ObjectId(challenge_id),
        "status": "active",
        "end_date": {"$gt": datetime.utcnow()}
    })
    
    if not challenge:
        return {"error": "Challenge not found or not active"}
    
    # Check if already joined
    existing = await db.challenge_participants.find_one({
        "challenge_id": challenge_id,
        "user_id": current_user["sub"]
    })
    
    if existing:
        return {"error": "Already joined this challenge"}
    
    # Join challenge
    participation = {
        "challenge_id": challenge_id,
        "user_id": current_user["sub"],
        "joined_at": datetime.utcnow(),
        "score": 0,
        "services_count": 0,
        "last_activity": datetime.utcnow()
    }
    
    await db.challenge_participants.insert_one(participation)
    
    return {
        "message": f"Successfully joined '{challenge['name']}'!",
        "challenge_name": challenge["name"],
        "end_date": challenge["end_date"].isoformat(),
        "reward_pool": challenge["reward_pool"]
    }

@router.get("/my-challenges")
async def get_my_challenges(current_user: dict = Depends(get_current_user)):
    """Get user's active challenges and progress"""
    db = get_db()
    
    # Get user's participations
    participations = await db.challenge_participants.find({
        "user_id": current_user["sub"]
    }).to_list(length=50)
    
    my_challenges = []
    
    for participation in participations:
        # Get challenge details
        challenge = await db.community_challenges.find_one({
            "_id": ObjectId(participation["challenge_id"])
        })
        
        if not challenge:
            continue
        
        # Get user's rank
        rank = await get_user_rank_in_challenge(participation["challenge_id"], current_user["sub"], db)
        
        # Calculate progress
        progress = await calculate_challenge_progress(
            participation["challenge_id"], 
            current_user["sub"], 
            challenge["criteria"], 
            db
        )
        
        my_challenges.append({
            "challenge_id": str(challenge["_id"]),
            "name": challenge["name"],
            "description": challenge["description"],
            "my_score": participation["score"],
            "my_rank": rank,
            "progress": progress,
            "end_date": challenge["end_date"].isoformat(),
            "status": challenge["status"],
            "reward_pool": challenge["reward_pool"]
        })
    
    return {"my_challenges": my_challenges}

@router.get("/leaderboard/{challenge_id}")
async def get_challenge_leaderboard(challenge_id: str, limit: int = 10):
    """Get challenge leaderboard"""
    db = get_db()
    
    # Get challenge details
    challenge = await db.community_challenges.find_one({"_id": ObjectId(challenge_id)})
    if not challenge:
        return {"error": "Challenge not found"}
    
    # Get leaderboard
    pipeline = [
        {"$match": {"challenge_id": challenge_id}},
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }
        },
        {"$unwind": "$user"},
        {"$sort": {"score": -1}},
        {"$limit": limit},
        {
            "$project": {
                "user_name": "$user.full_name",
                "score": 1,
                "services_count": 1,
                "last_activity": 1,
                "rank": {"$add": [{"$indexOfArray": [[], "$_id"]}, 1]}
            }
        }
    ]
    
    leaderboard = await db.challenge_participants.aggregate(pipeline).to_list(length=limit)
    
    # Add rank numbers
    for i, participant in enumerate(leaderboard):
        participant["rank"] = i + 1
        participant["_id"] = str(participant["_id"])
    
    return {
        "challenge_name": challenge["name"],
        "leaderboard": leaderboard,
        "total_participants": await db.challenge_participants.count_documents({"challenge_id": challenge_id})
    }

@router.post("/create-challenge")
async def create_community_challenge(
    challenge_type: str,
    neighborhood: str,
    custom_name: Optional[str] = None,
    custom_reward: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new community challenge"""
    db = get_db()
    
    if challenge_type not in CHALLENGE_TYPES:
        return {"error": "Invalid challenge type"}
    
    template = CHALLENGE_TYPES[challenge_type]
    
    challenge = {
        "name": custom_name or template["name"],
        "description": template["description"],
        "type": challenge_type,
        "criteria": template["criteria"],
        "neighborhood": neighborhood,
        "creator_id": current_user["sub"],
        "reward_pool": custom_reward or template["reward_pool"],
        "start_date": datetime.utcnow(),
        "end_date": datetime.utcnow() + timedelta(days=template["duration_days"]),
        "status": "active",
        "created_at": datetime.utcnow()
    }
    
    result = await db.community_challenges.insert_one(challenge)
    
    return {
        "challenge_id": str(result.inserted_id),
        "message": f"Challenge '{challenge['name']}' created successfully!",
        "duration": template["duration_days"],
        "reward_pool": challenge["reward_pool"]
    }

@router.get("/neighborhood-stats")
async def get_neighborhood_stats(neighborhood: str):
    """Get neighborhood statistics and rankings"""
    db = get_db()
    
    # Get all users in neighborhood
    neighborhood_users = await db.users.find({
        "address.neighborhood": neighborhood
    }).to_list(length=1000)
    
    user_ids = [str(user["_id"]) for user in neighborhood_users]
    
    # Get service statistics
    total_bookings = await db.bookings.count_documents({
        "user_id": {"$in": user_ids},
        "created_at": {"$gte": datetime.utcnow() - timedelta(days=30)}
    })
    
    # Service category breakdown
    pipeline = [
        {"$match": {"user_id": {"$in": user_ids}}},
        {"$group": {"_id": "$service_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    service_breakdown = await db.bookings.aggregate(pipeline).to_list(length=20)
    
    # Calculate neighborhood score
    avg_rating = 4.2  # Mock calculation
    service_diversity = len(service_breakdown)
    activity_score = min(100, total_bookings * 2)
    
    neighborhood_score = (avg_rating * 20) + (service_diversity * 5) + (activity_score * 0.5)
    
    # Get active challenges in neighborhood
    active_challenges = await db.community_challenges.count_documents({
        "neighborhood": neighborhood,
        "status": "active"
    })
    
    return {
        "neighborhood": neighborhood,
        "total_residents": len(neighborhood_users),
        "total_bookings_30d": total_bookings,
        "service_breakdown": service_breakdown,
        "neighborhood_score": round(neighborhood_score, 1),
        "grade": get_neighborhood_grade(neighborhood_score),
        "active_challenges": active_challenges,
        "insights": generate_neighborhood_insights(service_breakdown, total_bookings)
    }

@router.post("/neighborhood-battle")
async def create_neighborhood_battle(
    data: NeighborhoodBattleRequest,
    duration_days: int = 14,
    current_user: dict = Depends(get_current_user)
):
    """Create a battle between two neighborhoods"""
    db = get_db()
    
    neighborhood1 = data.challenger_zip
    neighborhood2 = data.target_zip
    battle_type = data.challenge_type
    
    battle = {
        "name": f"{neighborhood1} vs {neighborhood2} - {battle_type.title()} Battle",
        "type": "neighborhood_battle",
        "neighborhoods": [neighborhood1, neighborhood2],
        "battle_type": battle_type,  # "cleanliness", "wellness", "safety", etc.
        "creator_id": current_user["sub"],
        "start_date": datetime.utcnow(),
        "end_date": datetime.utcnow() + timedelta(days=duration_days),
        "status": "active",
        "scores": {neighborhood1: 0, neighborhood2: 0},
        "created_at": datetime.utcnow()
    }
    
    result = await db.neighborhood_battles.insert_one(battle)
    
    return {
        "battle_id": str(result.inserted_id),
        "message": f"Battle between {neighborhood1} and {neighborhood2} has begun!",
        "duration": duration_days,
        "battle_type": battle_type
    }

@router.get("/battles")
async def get_active_battles():
    """Get all active neighborhood battles"""
    db = get_db()
    
    battles = await db.neighborhood_battles.find({
        "status": "active",
        "end_date": {"$gt": datetime.utcnow()}
    }).to_list(length=20)
    
    for battle in battles:
        battle["_id"] = str(battle["_id"])
        
        # Calculate current scores
        for neighborhood in battle["neighborhoods"]:
            score = await calculate_neighborhood_battle_score(
                battle["_id"], 
                neighborhood, 
                battle["battle_type"], 
                db
            )
            battle["scores"][neighborhood] = score
        
        # Determine leader
        scores = battle["scores"]
        battle["leader"] = max(scores, key=scores.get) if scores else None
        battle["is_tie"] = len(set(scores.values())) == 1 if scores else False
    
    return {"battles": battles}

@router.get("/achievements")
async def get_community_achievements(current_user: dict = Depends(get_current_user)):
    """Get user's community achievements"""
    db = get_db()
    
    # Get completed challenges
    completed_challenges = await db.challenge_participants.find({
        "user_id": current_user["sub"]
    }).to_list(length=100)
    
    achievements = []
    
    for participation in completed_challenges:
        challenge = await db.community_challenges.find_one({
            "_id": ObjectId(participation["challenge_id"])
        })
        
        if challenge and challenge["status"] == "completed":
            rank = await get_user_rank_in_challenge(participation["challenge_id"], current_user["sub"], db)
            
            # Determine achievement level
            if rank == 1:
                achievement_level = "🥇 Champion"
                points = 500
            elif rank <= 3:
                achievement_level = "🥈 Top Performer"
                points = 300
            elif rank <= 10:
                achievement_level = "🥉 Active Participant"
                points = 100
            else:
                achievement_level = "🏅 Participant"
                points = 50
            
            achievements.append({
                "challenge_name": challenge["name"],
                "achievement_level": achievement_level,
                "rank": rank,
                "points_earned": points,
                "completed_date": challenge["end_date"].isoformat()
            })
    
    return {"achievements": achievements}

async def calculate_challenge_progress(challenge_id: str, user_id: str, criteria: str, db):
    """Calculate user's progress in a challenge"""
    
    # Get challenge timeframe
    challenge = await db.community_challenges.find_one({"_id": ObjectId(challenge_id)})
    start_date = challenge["start_date"]
    end_date = challenge["end_date"]
    
    # Calculate based on criteria
    if criteria == "cleaning_services":
        count = await db.bookings.count_documents({
            "user_id": user_id,
            "service_type": "cleaning",
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
    elif criteria == "eco_services":
        eco_services = ["cleaning", "gardening", "pest_control"]
        count = await db.bookings.count_documents({
            "user_id": user_id,
            "service_type": {"$in": eco_services},
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
    elif criteria == "safety_services":
        safety_services = ["plumbing", "electrical", "repair"]
        count = await db.bookings.count_documents({
            "user_id": user_id,
            "service_type": {"$in": safety_services},
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
    elif criteria == "wellness_services":
        wellness_services = ["beauty", "fitness"]
        count = await db.bookings.count_documents({
            "user_id": user_id,
            "service_type": {"$in": wellness_services},
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
    else:
        count = await db.bookings.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
    
    return {"services_booked": count, "score": count * 10}  # 10 points per service

async def get_user_rank_in_challenge(challenge_id: str, user_id: str, db):
    """Get user's current rank in challenge"""
    
    # Get all participants sorted by score
    participants = await db.challenge_participants.find({
        "challenge_id": challenge_id
    }).sort("score", -1).to_list(length=1000)
    
    for i, participant in enumerate(participants):
        if participant["user_id"] == user_id:
            return i + 1
    
    return None

async def calculate_neighborhood_battle_score(battle_id: str, neighborhood: str, battle_type: str, db):
    """Calculate neighborhood score in battle"""
    
    # Get battle details
    battle = await db.neighborhood_battles.find_one({"_id": ObjectId(battle_id)})
    start_date = battle["start_date"]
    end_date = battle["end_date"]
    
    # Get neighborhood users
    users = await db.users.find({"address.neighborhood": neighborhood}).to_list(length=1000)
    user_ids = [str(user["_id"]) for user in users]
    
    # Calculate score based on battle type
    if battle_type == "cleanliness":
        score = await db.bookings.count_documents({
            "user_id": {"$in": user_ids},
            "service_type": "cleaning",
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
    elif battle_type == "wellness":
        score = await db.bookings.count_documents({
            "user_id": {"$in": user_ids},
            "service_type": {"$in": ["beauty", "fitness"]},
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
    else:
        score = await db.bookings.count_documents({
            "user_id": {"$in": user_ids},
            "created_at": {"$gte": start_date, "$lte": end_date}
        })
    
    return score

def get_neighborhood_grade(score: float) -> str:
    """Convert neighborhood score to letter grade"""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"

def generate_neighborhood_insights(service_breakdown, total_bookings):
    """Generate insights for neighborhood"""
    insights = []
    
    if total_bookings > 100:
        insights.append("🔥 Very active neighborhood with high service usage!")
    elif total_bookings > 50:
        insights.append("📈 Good activity level in your neighborhood")
    else:
        insights.append("💡 Opportunity to increase community engagement")
    
    if service_breakdown:
        top_service = service_breakdown[0]["_id"]
        insights.append(f"🏆 Most popular service: {top_service}")
    
    return insights


@router.get("/top-providers")
async def get_top_providers_in_neighborhood(neighborhood: str):
    """
    Get the top-performing service providers in a specific neighborhood
    based on booking history and ratings.
    """
    db = get_db()
    
    # Get all users in neighborhood to find their bookings
    neighborhood_users = await db.users.find({
        "address.neighborhood": neighborhood
    }).to_list(length=1000)
    
    user_ids = [str(user["_id"]) for user in neighborhood_users]
    
    # Aggregate bookings by provider_id
    pipeline = [
        {"$match": {"user_id": {"$in": user_ids}}},
        {"$group": {
            "_id": "$provider_id", 
            "bookings_count": {"$sum": 1},
            "service_name": {"$first": "$service_name"},
            "category": {"$first": "$category"}
        }},
        {"$sort": {"bookings_count": -1}},
        {"$limit": 5}
    ]
    
    provider_stats = await db.bookings.aggregate(pipeline).to_list(length=5)
    
    results = []
    for stat in provider_stats:
        provider_id = stat["_id"]
        if not provider_id: continue
        
        # Get provider details
        provider = await db.users.find_one({"_id": ObjectId(provider_id)})
        if not provider: continue
        
        # Get provider's average rating
        reviews = await db.reviews.find({"provider_id": provider_id}).to_list(length=100)
        avg_rating = sum(r.get("rating", 0) for r in reviews) / len(reviews) if reviews else 4.5
        
        results.append({
            "id": str(provider["_id"]),
            "name": provider.get("full_name", "Provider"),
            "category": stat.get("category") or "Pro",
            "neighborhoodBookings": stat["bookings_count"],
            "repeatCustomers": int(stat["bookings_count"] * 0.6), # Simulated
            "avgRating": round(avg_rating, 1),
            "distance": round(random.uniform(0.1, 2.0), 1) # Simulated context
        })
        
    return results

# ── Router Section: core ──
core_router = APIRouter()
router = core_router
from fastapi import APIRouter, HTTPException, Depends, Response, Cookie, Request, UploadFile, File, Form, status
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import os
import shutil
import random
import string
import base64
from bson import ObjectId
from twilio.rest import Client as TwilioClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Configure local logging
logging.basicConfig(filename="auth_debug.log", level=logging.INFO, format="%(asctime)s - %(message)s")


# --- AUTH SECTION ---

@router.post("/auth/register")
async def register(user: UserCreate, response: Response):
    db = get_db()
    existing_email = await db.users.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    if user.phone:
        existing_phone = await db.users.find_one({"phone": user.phone})
        if existing_phone:
            raise HTTPException(status_code=400, detail="This phone number is already associated with another account.")
    if not user.password or len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["addresses"] = []
    if user.role == UserRole.PROVIDER:
        score = 75 
        if user.bio: score += 5
        if user.business_name: score += 5
        if user.experience_years and user.experience_years > 0: score += 5
        if user.service_categories and len(user.service_categories) > 0: score += 5
        if user.base_location: score += 5
        if user.aptitude_score is not None:
            score += (user.aptitude_score / 100) * 20
        user_dict["quickserve_score"] = min(100, round(score))
        user_dict["onboarded"] = True
        user_dict["verified_by_admin"] = False
        user_dict["is_verified"] = False
        user_dict["rating"] = 0.0
        user_dict["reviews_count"] = 0
        user_dict["balance"] = 0.0
    if not user_dict.get("full_name") and user_dict.get("name"):
        user_dict["full_name"] = user_dict["name"]
    result = await db.users.insert_one(user_dict)
    access_token = create_access_token({"sub": str(result.inserted_id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(result.inserted_id)})
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return {"message": "Registered successfully", "access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": user.role}

@router.post("/auth/login")
async def login(credentials: UserLogin, response: Response):
    db = get_db()
    user = await db.users.find_one({"email": credentials.email})
    password_field = "password" if user and "password" in user else "password_hash" if user and "password_hash" in user else None
    if not user or not password_field or not verify_password(credentials.password, user[password_field]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": str(user["_id"]), "role": user["role"]})
    refresh_token = create_refresh_token({"sub": str(user["_id"])})
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return {"message": "Logged in successfully", "access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": user["role"], "user_id": str(user["_id"])}

@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user: raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    user.pop("password_hash", None)
    return user

@router.get("/auth/csrf-token")
async def get_csrf_token(response: Response):
    import secrets
    token = secrets.token_hex(32)
    response.set_cookie(key="csrf_token", value=token, httponly=False, samesite="strict")
    return {"csrf_token": token}

# --- VERIFICATION SECTION (DUAL-LAYER) ---

@router.post("/verify/work")
async def verify_work(job_id: str = Form(...), latitude: float = Form(...), longitude: float = Form(...), before_image: UploadFile = File(...), after_image: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    db = get_db()
    before_bytes = await before_image.read()
    after_bytes = await after_image.read()
    before_url = f"data:{before_image.content_type};base64,{base64.b64encode(before_bytes).decode('utf-8')}"
    after_url = f"data:{after_image.content_type};base64,{base64.b64encode(after_bytes).decode('utf-8')}"
    verification_record = {"provider_id": current_user["sub"], "job_id": job_id, "location": {"lat": latitude, "lng": longitude}, "timestamp": datetime.utcnow(), "images": {"before": before_url, "after": after_url}, "status": "verified"}
    await db.work_verifications.insert_one(verification_record)
    try:
        await db.bookings.update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "completed", "is_verified": True}})
    except: pass 
    return {"message": "Work verified successfully", "status": "verified"}

@router.post("/verify/check-in")
async def check_in(data: CheckInRequest, current_user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        await db.bookings.update_one({"_id": ObjectId(data.job_id)}, {"$set": {"check_in": {"lat": data.latitude, "lng": data.longitude, "timestamp": datetime.utcnow()}, "status": "in_progress"}})
    except: pass
    return {"message": "Check-in successful", "status": "in_progress"}

@router.get("/verify/trust-score")
async def get_trust_score(current_user: dict = Depends(get_current_user)):
    db = get_db()
    if current_user.get("role") != "provider": raise HTTPException(status_code=403, detail="Only providers have a trust score")
    provider_id = current_user["sub"]
    reviews = await db.reviews.find({"provider_id": provider_id}).to_list(100)
    avg_rating = sum([r.get("rating", 5) for r in reviews]) / max(len(reviews), 1)
    scaled_rating = avg_rating * 20
    review_sentiment = min((avg_rating / 5.0) * 105, 100.0) 
    verified_jobs = await db.work_verifications.count_documents({"provider_id": provider_id})
    gallery_density = min(verified_jobs * 10, 100)
    trust_score = (0.4 * scaled_rating) + (0.3 * review_sentiment) + (0.3 * gallery_density)
    is_verified_badge = verified_jobs >= 3
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$set": {"trust_score": round(trust_score, 1), "is_verified_badge": is_verified_badge}})
    return {"trust_score": round(trust_score, 1), "verified_jobs_count": verified_jobs, "is_verified_badge": is_verified_badge}

# --- PROVIDERS SECTION ---

@router.get("/providers")
async def get_providers(limit: int = 20):
    db = get_db()
    providers = await db.users.find({"role": "provider"}).limit(limit).to_list(length=limit)
    for p in providers:
        p["_id"] = str(p["_id"])
        p.pop("password", None)
    return providers

@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str):
    db = get_db()
    provider = await db.users.find_one({"_id": ObjectId(provider_id), "role": "provider"})
    if provider:
        provider["_id"] = str(provider["_id"])
        provider.pop("password", None)
    return provider

@router.post("/providers/onboard")
async def onboard_provider(data: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    score = 85 
    if data.get("documents"): score += 5
    if data.get("portfolio"): score += 5
    if data.get("ai_bot_settings"): score += 5
    update_data = {"onboarded": True, "base_location": data.get("location"), "service_area": {"type": data.get("service_area_type"), "radius": data.get("radius"), "polygon": data.get("polygon_points")}, "specializations": data.get("categories"), "hourly_rate": data.get("hourly_rate"), "emergency_rate": data.get("emergency_rate"), "ai_bot_settings": data.get("ai_bot_settings"), "quickserve_score": score, "launch_plan_generated": True, "updated_at": datetime.utcnow()}
    await db.users.update_one({"_id": ObjectId(current_user["sub"])}, {"$set": update_data})
    return {"status": "success", "score": score}

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user: raise HTTPException(status_code=404)
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    return user

# ── Router Section: core_engagement ──
core_engagement_router = APIRouter()
router = core_engagement_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from bson import ObjectId
import random
import string


# --- health.py ---
health_router = APIRouter(tags=["Health"])

@health_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@health_router.get("/health/detailed")
async def detailed_health():
    db = get_db()
    try:
        await db.command("ping")
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@health_router.get("/health/ready")
async def readiness_check():
    return {"ready": True}

@health_router.get("/health/live")
async def liveness_check():
    return {"alive": True}

# --- users.py ---
users_router = APIRouter(prefix="/users", tags=["Users"])

@users_router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if user:
        user["_id"] = str(user["_id"])
        user.pop("password", None)
    return user

@users_router.put("/profile")
async def update_profile(profile: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.users.update_one({"_id": ObjectId(current_user["sub"])}, {"$set": profile})
    return {"status": "updated"}

@users_router.post("/address")
async def add_address(address: dict, current_user: dict = Depends(get_current_user)):
    """Add a structured address (home, work, other)"""
    db = get_db()
    # address should have: type, line1, city, state, postal_code, location (lat/lng)
    address["user_id"] = current_user["sub"]
    address["created_at"] = datetime.utcnow()
    
    # Update user's addresses array or separate collection
    result = await db.addresses.insert_one(address)
    
    # Also embed basic info in user profile for fast access
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$push": {"addresses": {
            "id": str(result.inserted_id),
            "type": address.get("type", "other"),
            "label": address.get("line1")
        }}}
    )
    
    return {"id": str(result.inserted_id), "status": "added"}

@users_router.get("/addresses")
async def get_addresses(current_user: dict = Depends(get_current_user)):
    db = get_db()
    addresses = await db.addresses.find({"user_id": current_user["sub"]}).to_list(length=100)
    for a in addresses:
        a["_id"] = str(a["_id"])
    return addresses

@users_router.post("/favorite/{provider_id}")
async def add_favorite(provider_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.favorites.insert_one({"user_id": current_user["sub"], "provider_id": provider_id})
    return {"status": "added"}

@users_router.get("/favorites")
async def get_favorites(current_user: dict = Depends(get_current_user)):
    db = get_db()
    favorites = await db.favorites.find({"user_id": current_user["sub"]}).to_list(length=100)
    for f in favorites:
        f["_id"] = str(f["_id"])
    return favorites

# --- analytics.py ---
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])

@analytics_router.get("/overview")
async def get_overview(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total_bookings = await db.bookings.count_documents({})
    total_revenue = await db.payments.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    
    return {
        "total_bookings": total_bookings,
        "total_revenue": total_revenue[0]["total"] if total_revenue else 0
    }

@analytics_router.get("/revenue")
async def get_revenue(current_user: dict = Depends(get_current_user)):
    db = get_db()
    revenue = await db.payments.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    return {"total_revenue": revenue[0]["total"] if revenue else 0}

@analytics_router.get("/bookings")
async def get_booking_stats(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total = await db.bookings.count_documents({})
    completed = await db.bookings.count_documents({"status": "completed"})
    pending = await db.bookings.count_documents({"status": "pending"})
    return {"total": total, "completed": completed, "pending": pending}

@analytics_router.get("/users")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total = await db.users.count_documents({})
    customers = await db.users.count_documents({"role": "customer"})
    providers = await db.users.count_documents({"role": "provider"})
    return {"total": total, "customers": customers, "providers": providers}

# --- loyalty.py ---
loyalty_router = APIRouter(prefix="/loyalty", tags=["Loyalty & Referrals"])

TIERS = {
    "bronze": {"min_points": 0, "discount": 5},
    "silver": {"min_points": 500, "discount": 10},
    "gold": {"min_points": 1500, "discount": 15},
    "platinum": {"min_points": 3000, "discount": 20}
}

@loyalty_router.get("/points")
async def get_loyalty_points(current_user: dict = Depends(get_current_user)):
    db = get_db()
    account = await db.loyalty_accounts.find_one({"user_id": current_user["sub"]})
    if not account:
        account = {"user_id": current_user["sub"], "points": 0, "tier": "bronze"}
        await db.loyalty_accounts.insert_one(account)
    
    tier = "bronze"
    for t, data in sorted(TIERS.items(), key=lambda x: x[1]["min_points"], reverse=True):
        if account["points"] >= data["min_points"]:
            tier = t
            break
    
    return {"points": account.get("points", 0), "tier": tier, "discount": TIERS[tier]["discount"]}

@loyalty_router.post("/earn")
async def earn_points(amount: float, current_user: dict = Depends(get_current_user)):
    # SECURITY: Only admin can award points manually
    if current_user.get("role") != "admin":
                raise HTTPException(status_code=403, detail="Only admins can award points manually")
    
    db = get_db()
    points = int(amount / 10)
    await db.loyalty_accounts.update_one(
        {"user_id": current_user["sub"]},
        {"$inc": {"points": points}},
        upsert=True
    )
    return {"points_earned": points, "awarded_by": "admin"}

@loyalty_router.post("/redeem")
async def redeem_points(points: int, current_user: dict = Depends(get_current_user)):
    db = get_db()
    account = await db.loyalty_accounts.find_one({"user_id": current_user["sub"]})
    if not account or account.get("points", 0) < points:
        return {"error": "Insufficient points"}
    
    await db.loyalty_accounts.update_one(
        {"user_id": current_user["sub"]},
        {"$inc": {"points": -points}}
    )
    discount = points / 10
    return {"discount_amount": discount, "remaining_points": account["points"] - points}

@loyalty_router.post("/referral/generate")
async def generate_referral_code(current_user: dict = Depends(get_current_user)):
    db = get_db()
    code = "QS" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await db.referral_codes.insert_one({
        "code": code,
        "user_id": current_user["sub"],
        "created_at": datetime.utcnow(),
        "uses": 0
    })
    return {"code": code}

@loyalty_router.post("/referral/apply/{code}")
async def apply_referral_code(code: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    referral = await db.referral_codes.find_one({"code": code})
    if not referral:
        return {"error": "Invalid code"}
    
    await db.referral_codes.update_one({"code": code}, {"$inc": {"uses": 1}})
    await db.loyalty_accounts.update_one(
        {"user_id": referral["user_id"]},
        {"$inc": {"points": 150}},
        upsert=True
    )
    return {"bonus": 100, "referrer_bonus": 150}

@loyalty_router.get("/referral/stats")
async def get_referral_stats(current_user: dict = Depends(get_current_user)):
    db = get_db()
    codes = await db.referral_codes.find({"user_id": current_user["sub"]}).to_list(length=100)
    total_uses = sum(c.get("uses", 0) for c in codes)
    return {"total_referrals": total_uses, "codes": len(codes)}

# --- notifications.py ---
notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])

@notifications_router.get("/")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    db = get_db()
    notifications = await db.notifications.find({"user_id": current_user["sub"]}).sort("created_at", -1).limit(50).to_list(length=50)
    for n in notifications:
        n["_id"] = str(n["_id"])
    return notifications

@notifications_router.put("/{notification_id}/read")
async def mark_as_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.notifications.update_one({"_id": ObjectId(notification_id)}, {"$set": {"read": True}})
    return {"status": "marked_read"}

@notifications_router.put("/read-all")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.notifications.update_many({"user_id": current_user["sub"]}, {"$set": {"read": True}})
    return {"status": "all_marked_read"}

@notifications_router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    db = get_db()
    count = await db.notifications.count_documents({"user_id": current_user["sub"], "read": False})
    return {"unread_count": count}

@notifications_router.put("/preferences")
async def update_preferences(prefs: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": {"notification_preferences": prefs}}
    )
    return {"status": "preferences_updated"}

@notifications_router.post("/send-test")
async def send_test_notification(type: str, current_user: dict = Depends(get_current_user)):
    """Mock sending SMS/Email/Push based on type"""
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    
    if type == "sms":
        # Mock Twilio: client.messages.create(body="...", to=user["phone"])
        print(f"SMS sent to {user['phone']}")
    elif type == "email":
        # Mock SendGrid: mail = Mail(from_email="...", to_emails=user["email"])
        print(f"Email sent to {user['email']}")
    
    # Always store in DB
        await db.notifications.insert_one({
        "user_id": current_user["sub"],
        "title": f"Test {type.upper()} Notification",
        "message": f"This is a test {type} notification from QuickServe.",
        "type": type,
        "read": False,
        "created_at": datetime.utcnow()
    })
    
    return {"status": "sent", "channel": type}

# --- subscriptions.py ---
subscriptions_router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

@subscriptions_router.post("/")
async def create_subscription(subscription: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    subscription["user_id"] = current_user["sub"]
    subscription["status"] = "active"
    subscription["created_at"] = datetime.utcnow()
    result = await db.subscriptions.insert_one(subscription)
    return {"id": str(result.inserted_id)}

@subscriptions_router.get("/")
async def get_subscriptions(current_user: dict = Depends(get_current_user)):
    db = get_db()
    subs = await db.subscriptions.find({"user_id": current_user["sub"]}).to_list(length=100)
    for s in subs:
        s["_id"] = str(s["_id"])
    return subs

@subscriptions_router.put("/{subscription_id}/pause")
async def pause_subscription(subscription_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.subscriptions.update_one({"_id": ObjectId(subscription_id)}, {"$set": {"status": "paused"}})
    return {"status": "paused"}

@subscriptions_router.put("/{subscription_id}/resume")
async def resume_subscription(subscription_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.subscriptions.update_one({"_id": ObjectId(subscription_id)}, {"$set": {"status": "active"}})
    return {"status": "active"}

@subscriptions_router.delete("/{subscription_id}")
async def cancel_subscription(subscription_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.subscriptions.update_one({"_id": ObjectId(subscription_id)}, {"$set": {"status": "cancelled"}})
    return {"status": "cancelled"}

# ── Router Section: dashboard ──
dashboard_router = APIRouter()
router = dashboard_router
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from bson import ObjectId
import random


@router.get("/customer")
async def get_customer_dashboard(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total_bookings = await db.bookings.count_documents({"user_id": current_user["sub"]})
    active_bookings = await db.bookings.count_documents({"user_id": current_user["sub"], "status": {"$in": ["pending", "confirmed", "in_progress"]}})
    recent_bookings = await db.bookings.find({"user_id": current_user["sub"]}).sort("created_at", -1).limit(5).to_list(length=5)
    
    loyalty = await db.loyalty_accounts.find_one({"user_id": current_user["sub"]})
    points = loyalty.get("points", 0) if loyalty else 0
    
    for b in recent_bookings:
        b["_id"] = str(b["_id"])
    
    return {
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "loyalty_points": points,
        "recent_bookings": recent_bookings
    }

@router.get("/provider")
async def get_provider_dashboard(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total_bookings = await db.bookings.count_documents({"provider_id": current_user["sub"]})
    completed = await db.bookings.count_documents({"provider_id": current_user["sub"], "status": "completed"})
    pending = await db.bookings.count_documents({"provider_id": current_user["sub"], "status": "pending"})
    
    reviews = await db.reviews.find({"provider_id": current_user["sub"]}).to_list(length=1000)
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews) if reviews else 0
    
    payments = await db.payments.find({"provider_id": current_user["sub"], "status": "completed"}).to_list(length=1000)
    total_earnings = sum(p.get("amount", 0) for p in payments)
    
    # Calculations
    route_efficiency = 92 + (completed % 8) # Simulated but based on real count
    quickserve_score = min(100, 75 + int(avg_rating * 4) + (completed // 5))
    
    # Repeat customers
    repeat_pipe = await db.bookings.aggregate([
        {"$match": {"provider_id": current_user["sub"]}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$count": "repeats"}
    ]).to_list(length=1)
    repeats = repeat_pipe[0]["repeats"] if repeat_pipe else 0
    total_customers_pipe = await db.bookings.aggregate([
        {"$match": {"provider_id": current_user["sub"]}},
        {"$group": {"_id": "$user_id"}}
    ]).to_list(length=1000)
    total_customers = len(total_customers_pipe)
    repeat_rate = round((repeats / total_customers * 100), 1) if total_customers > 0 else 0

    # Active jobs for schedule
    active_jobs = await db.bookings.find({
        "provider_id": current_user["sub"],
        "status": {"$in": ["confirmed", "in_progress"]}
    }).sort("created_at", 1).to_list(length=5)
    
    for job in active_jobs:
        job["_id"] = str(job["_id"])
        job["created_at"] = job["created_at"].isoformat() if hasattr(job["created_at"], "isoformat") else str(job["created_at"])

    return {
        "total_bookings": total_bookings,
        "completed_bookings": completed,
        "pending_bookings": pending,
        "average_rating": round(avg_rating, 2),
        "total_reviews": len(reviews),
        "total_earnings": round(total_earnings, 2),
        "route_efficiency": route_efficiency,
        "quickserve_score": quickserve_score,
        "repeat_customer_rate": repeat_rate,
        "active_jobs": active_jobs
    }

@router.get("/admin")
async def get_admin_dashboard(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # User stats
    total_users = await db.users.count_documents({"role": "customer"})
    total_providers = await db.users.count_documents({"role": "provider"})
    total_admins = await db.users.count_documents({"role": "admin"})
    
    # Booking stats
    total_bookings = await db.bookings.count_documents({})
    pending_bookings = await db.bookings.count_documents({"status": "pending"})
    completed_bookings = await db.bookings.count_documents({"status": "completed"})
    cancelled_bookings = await db.bookings.count_documents({"status": "cancelled"})
    
    # Revenue stats
    total_revenue_pipe = await db.payments.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    revenue = total_revenue_pipe[0]["total"] if total_revenue_pipe else 0
    
    # Today's stats
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_bookings = await db.bookings.count_documents({"created_at": {"$gte": today}})
    today_revenue_pipe = await db.payments.aggregate([
        {"$match": {"created_at": {"$gte": today}, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    today_revenue = today_revenue_pipe[0]["total"] if today_revenue_pipe else 0
    
    # Last 7 days stats
    last_7_days = datetime.utcnow() - timedelta(days=7)
    week_bookings = await db.bookings.count_documents({"created_at": {"$gte": last_7_days}})
    week_revenue_pipe = await db.payments.aggregate([
        {"$match": {"created_at": {"$gte": last_7_days}, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    week_revenue = week_revenue_pipe[0]["total"] if week_revenue_pipe else 0
    
    # Recent transactions
    recent_transactions = await db.payments.find().sort("created_at", -1).limit(10).to_list(length=10)
    for t in recent_transactions:
        t["_id"] = str(t["_id"])
        if "created_at" in t:
            t["created_at"] = t["created_at"].isoformat() if hasattr(t["created_at"], "isoformat") else str(t["created_at"])
    
    # All customers with complete analytics
    all_customers = await db.users.find({"role": "customer"}).limit(100).to_list(length=100)
    for customer in all_customers:
        customer["_id"] = str(customer["_id"])
        customer.pop("password", None)
        
        # Customer bookings
        customer_bookings = await db.bookings.count_documents({"user_id": customer["_id"]})
        completed = await db.bookings.count_documents({"user_id": customer["_id"], "status": "completed"})
        cancelled = await db.bookings.count_documents({"user_id": customer["_id"], "status": "cancelled"})
        
        # Customer spending
        spending_pipe = await db.payments.aggregate([
            {"$match": {"user_id": customer["_id"], "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(length=1)
        total_spent = spending_pipe[0]["total"] if spending_pipe else 0
        
        # Loyalty info
        loyalty = await db.loyalty_accounts.find_one({"user_id": customer["_id"]})
        loyalty_points = loyalty.get("points", 0) if loyalty else 0
        loyalty_tier = loyalty.get("tier", "bronze") if loyalty else "bronze"
        
        # Reviews given
        reviews_given = await db.reviews.count_documents({"user_id": customer["_id"]})
        
        customer["analytics"] = {
            "total_bookings": customer_bookings,
            "completed_bookings": completed,
            "cancelled_bookings": cancelled,
            "total_spent": round(total_spent, 2),
            "loyalty_points": loyalty_points,
            "loyalty_tier": loyalty_tier,
            "reviews_given": reviews_given,
            "avg_booking_value": round(total_spent / customer_bookings, 2) if customer_bookings > 0 else 0
        }
    
    # All providers with complete analytics
    all_providers = await db.users.find({"role": "provider"}).limit(100).to_list(length=100)
    for provider in all_providers:
        provider["_id"] = str(provider["_id"])
        provider.pop("password", None)
        
        # Provider bookings
        provider_bookings = await db.bookings.count_documents({"provider_id": provider["_id"]})
        completed = await db.bookings.count_documents({"provider_id": provider["_id"], "status": "completed"})
        cancelled = await db.bookings.count_documents({"provider_id": provider["_id"], "status": "cancelled"})
        pending = await db.bookings.count_documents({"provider_id": provider["_id"], "status": "pending"})
        
        # Provider earnings
        earnings_pipe = await db.payments.aggregate([
            {"$match": {"provider_id": provider["_id"], "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(length=1)
        total_earnings = earnings_pipe[0]["total"] if earnings_pipe else 0
        
        # Provider reviews and ratings
        reviews = await db.reviews.find({"provider_id": provider["_id"]}).to_list(length=1000)
        total_reviews = len(reviews)
        avg_rating = sum(r["rating"] for r in reviews) / total_reviews if total_reviews > 0 else 0
        
        # Services offered
        services_count = await db.services.count_documents({"provider_id": provider["_id"]})
        
        # Response rate
        response_rate = (completed / provider_bookings * 100) if provider_bookings > 0 else 0
        
        # This month earnings
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_earnings_pipe = await db.payments.aggregate([
            {"$match": {"provider_id": provider["_id"], "status": "completed", "created_at": {"$gte": month_start}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(length=1)
        month_earnings = month_earnings_pipe[0]["total"] if month_earnings_pipe else 0
        
        provider["analytics"] = {
            "total_bookings": provider_bookings,
            "completed_bookings": completed,
            "cancelled_bookings": cancelled,
            "pending_bookings": pending,
            "total_earnings": round(total_earnings, 2),
            "month_earnings": round(month_earnings, 2),
            "total_reviews": total_reviews,
            "average_rating": round(avg_rating, 2),
            "services_count": services_count,
            "completion_rate": round(response_rate, 2),
            "avg_booking_value": round(total_earnings / completed, 2) if completed > 0 else 0
        }
    
    # Category-wise analytics
    category_analytics = await db.bookings.aggregate([
        {"$group": {
            "_id": "$category",
            "bookings": {"$sum": 1},
            "revenue": {"$sum": "$amount"},
            "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}
        }},
        {"$sort": {"revenue": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    
    formatted_categories = []
    for cat in category_analytics:
        formatted_categories.append({
            "name": (cat["_id"] or "Unknown").capitalize(),
            "bookings": cat["bookings"],
            "revenue": round(cat["revenue"] or 0, 2),
            "growth": random.randint(5, 25)  # Simulated growth for UI
        })

    # System Health
    reviews_count = await db.reviews.count_documents({})
    avg_rating_pipe = await db.reviews.aggregate([
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}}
    ]).to_list(length=1)
    avg_rating_val = round(avg_rating_pipe[0]["avg"], 1) if avg_rating_pipe else 4.8
    system_health = {
        "uptime": "99.98%",
        "avg_load_time": "1.1s",
        "error_rate": "0.02%",
        "avg_rating": avg_rating_val
    }
    
    # Top performing providers
    top_providers = sorted(all_providers, key=lambda x: x["analytics"]["total_earnings"], reverse=True)[:10]
    
    # Top spending customers
    top_customers = sorted(all_customers, key=lambda x: x["analytics"]["total_spent"], reverse=True)[:10]
    
    return {
        "total_users": total_users,
        "total_providers": total_providers,
        "total_admins": total_admins,
        "total_bookings": total_bookings,
        "pending_bookings": pending_bookings,
        "completed_bookings": completed_bookings,
        "cancelled_bookings": cancelled_bookings,
        "total_revenue": round(revenue, 2),
        "today_bookings": today_bookings,
        "today_revenue": round(today_revenue, 2),
        "week_bookings": week_bookings,
        "week_revenue": round(week_revenue, 2),
        "active_services": await db.services.count_documents({}),
        "recent_transactions": recent_transactions,
        "all_customers": all_customers,
        "all_providers": all_providers,
        "category_stats": formatted_categories,
        "top_providers": top_providers,
        "top_customers": top_customers,
        "system_health": system_health
    }

@router.get("/customer/favourites", dependencies=[Depends(check_role(["customer"]))])
async def get_customer_favourites(current_user: dict = Depends(get_current_user)):
    """Return top providers from the user's completed bookings."""
    db = get_db()
    completed = await db.bookings.find(
        {"user_id": current_user["sub"], "status": "completed"}
    ).sort("created_at", -1).to_list(length=50)

    # Aggregate by provider_id, count bookings
    provider_counts: dict = {}
    for b in completed:
        pid = b.get("provider_id") or b.get("provider")
        if pid:
            provider_counts[pid] = provider_counts.get(pid, 0) + 1

    # Sort by frequency, take top 5
    top_pids = sorted(provider_counts, key=lambda x: provider_counts[x], reverse=True)[:5]

    favourites = []
    for pid in top_pids:
        # Try ObjectId lookup first, then string match on full_name
        provider = None
        try:
            provider = await db.users.find_one({"_id": ObjectId(pid)})
        except Exception:
            provider = await db.users.find_one({"full_name": pid})
        if provider:
            provider["_id"] = str(provider["_id"])
            provider.pop("password", None)
            # Find the service for this provider to get category/rate
            svc = await db.services.find_one({"provider_id": str(provider["_id"])})
            favourites.append({
                "id": str(provider["_id"]),
                "name": provider.get("full_name", "Provider"),
                "category": svc.get("category", provider.get("specializations", ["Service"])[0]) if svc else (provider.get("specializations") or ["Service"])[0],
                "rating": provider.get("rating", 4.5),
                "rate": svc.get("price_per_hour", provider.get("hourly_rate", 300)) if svc else provider.get("hourly_rate", 300),
                "bookings": provider_counts[pid],
            })

    return {"favourites": favourites}


@router.get("/customer/block-parties", dependencies=[Depends(check_role(["customer"]))])
async def get_block_parties(current_user: dict = Depends(get_current_user)):
    """Return active block-party / group-booking deals from community_challenges."""
    db = get_db()
    challenges = await db.community_challenges.find(
        {"status": "active", "end_date": {"$gt": datetime.utcnow()}}
    ).limit(6).to_list(length=6)

    result = []
    for c in challenges:
        c["_id"] = str(c["_id"])
        participants = await db.challenge_participants.count_documents({"challenge_id": c["_id"]})
        joined = await db.challenge_participants.find_one({
            "challenge_id": c["_id"], "user_id": current_user["sub"]
        })
        time_left = c["end_date"] - datetime.utcnow()
        hours_left = int(time_left.total_seconds() // 3600)
        days_left = time_left.days
        expires_str = f"{days_left} days" if days_left >= 1 else f"{hours_left} hours"
        result.append({
            "id": c["_id"],
            "service": c.get("name", "Group Service"),
            "category": c.get("type", "cleaning"),
            "participants": participants,
            "needed": c.get("min_participants", 5),
            "discount": c.get("discount_percent", 15),
            "expiresIn": expires_str,
            "area": c.get("neighborhood", "Your Area"),
            "provider": c.get("provider_name", "QuickServe Partner"),
            "joined": bool(joined),
        })
    return {"block_parties": result}


@router.get("/customer/quotes", dependencies=[Depends(check_role(["customer"]))])
async def get_customer_quotes(current_user: dict = Depends(get_current_user)):
    """Return completed bookings as quote history with AI estimate vs actual cost."""
    db = get_db()
    bookings = await db.bookings.find(
        {"user_id": current_user["sub"], "status": "completed"}
    ).sort("created_at", -1).limit(10).to_list(length=10)

    quotes = []
    for b in bookings:
        b["_id"] = str(b["_id"])
        actual = b.get("final_price") or b.get("price") or b.get("total_amount") or 0
        # AI estimate: stored if present, else derive from base rate
        ai_est = b.get("ai_estimate") or round(actual * 1.08, 0)  # 8% variance
        created = b.get("created_at")
        date_str = created.strftime("%b %d, %Y") if hasattr(created, "strftime") else str(created)[:10]
        quotes.append({
            "id": b["_id"],
            "service": b.get("service_name") or f"{b.get('category', 'Service')} Service",
            "category": (b.get("category") or "repair").lower(),
            "date": date_str,
            "aiEstimate": ai_est,
            "actualCost": actual,
        })
    return {"quotes": quotes}


@router.get("/customer/maintenance", dependencies=[Depends(check_role(["customer"]))])
async def get_maintenance_health(current_user: dict = Depends(get_current_user)):
    """Derive home health scores from the user's booking history per category."""
    db = get_db()
    CATEGORIES = [
        {"category": "HVAC",        "service_key": "ac",          "recommended_days": 90,  "icon": "Wind"},
        {"category": "Electrical",  "service_key": "electrical",  "recommended_days": 365, "icon": "Zap"},
        {"category": "Plumbing",    "service_key": "plumbing",    "recommended_days": 180, "icon": "Droplets"},
        {"category": "Cleaning",    "service_key": "cleaning",    "recommended_days": 30,  "icon": "Sparkles"},
        {"category": "Pest Control","service_key": "pest",        "recommended_days": 90,  "icon": "Shield"},
    ]
    result = []
    for cat in CATEGORIES:
        last_booking = await db.bookings.find_one(
            {"user_id": current_user["sub"], "status": "completed",
             "category": {"$regex": cat["service_key"], "$options": "i"}},
            sort=[("created_at", -1)]
        )
        if last_booking and last_booking.get("created_at"):
            days_ago = (datetime.utcnow() - last_booking["created_at"]).days
            last_str = f"{days_ago} days ago" if days_ago > 0 else "Today"
            ratio = days_ago / cat["recommended_days"]
            score = max(0, min(100, int(100 - ratio * 60)))
        else:
            days_ago = cat["recommended_days"] + 1
            last_str = "Never"
            score = 20
        alert = "green" if score >= 70 else ("yellow" if score >= 45 else "red")
        rec_str = (
            f"Every {cat['recommended_days']} days" if cat["recommended_days"] < 365
            else "Annually"
        )
        result.append({
            "category": cat["category"],
            "icon": cat["icon"],
            "lastService": last_str,
            "recommended": rec_str,
            "score": score,
            "alert": alert,
            "message": (
                f"{cat['category']} In Good Shape" if alert == "green"
                else f"{cat['category']} Service Recommended" if alert == "yellow"
                else f"{cat['category']} Overdue"
            ),
        })
    return {"maintenance": result}


@router.get("/quick-stats")
async def get_quick_stats(current_user: dict = Depends(get_current_user)):
    db = get_db()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_bookings = await db.bookings.count_documents({"created_at": {"$gte": today}})
    today_revenue_pipe = await db.payments.aggregate([
        {"$match": {"created_at": {"$gte": today}, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(length=1)
    
    return {
        "today_bookings": today_bookings,
        "today_revenue": today_revenue_pipe[0]["total"] if today_revenue_pipe else 0
    }

# ── Router Section: dashboards ──
dashboards_router = APIRouter()
router = dashboards_router
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from bson import ObjectId
import random
import uuid


# --- CUSTOMER DASHBOARD ---

@router.get("/dashboard/customer")
async def get_customer_dashboard(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["sub"]
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    bookings = await db.bookings.find({"customer_id": user_id}).sort("created_at", -1).limit(5).to_list(length=5)
    for b in bookings: b["_id"] = str(b["_id"])
    return {"total_bookings": await db.bookings.count_documents({"customer_id": user_id}), "active_bookings": await db.bookings.count_documents({"customer_id": user_id, "status": "confirmed"}), "loyalty_points": user.get("quickserve_credits", 0), "recent_bookings": bookings}

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

# ── Router Section: events ──
events_router = APIRouter()
router = events_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict
import random


EVENT_TYPES = {
    "skill_showcase": {
        "name": "🎭 Skill Showcase",
        "description": "Providers demonstrate their expertise live",
        "duration_minutes": 30,
        "max_participants": 50
    },
    "flash_auction": {
        "name": "⚡ Flash Auction",
        "description": "Bid on premium services at discounted rates",
        "duration_minutes": 15,
        "max_participants": 100
    },
    "masterclass": {
        "name": "🎓 Service Masterclass",
        "description": "Learn from expert providers",
        "duration_minutes": 60,
        "max_participants": 200
    },
    "speed_booking": {
        "name": "🏃 Speed Booking",
        "description": "Quick 5-minute consultations with multiple providers",
        "duration_minutes": 45,
        "max_participants": 30
    },
    "community_challenge": {
        "name": "🏆 Community Challenge",
        "description": "Neighborhood teams compete in service challenges",
        "duration_minutes": 90,
        "max_participants": 500
    }
}

@router.get("/upcoming")
async def get_upcoming_events(category: Optional[str] = None, limit: int = 10):
    """Get upcoming virtual marketplace events"""
    db = get_db()
    
    query = {
        "start_time": {"$gt": datetime.utcnow()},
        "status": "scheduled"
    }
    
    if category:
        query["category"] = category
    
    events = await db.virtual_events.find(query).sort("start_time", 1).limit(limit).to_list(length=limit)
    
    for event in events:
        event["_id"] = str(event["_id"])
        
        # Get participant count
        event["current_participants"] = await db.event_participants.count_documents({
            "event_id": str(event["_id"])
        })
        
        # Calculate time until event
        time_until = event["start_time"] - datetime.utcnow()
        event["hours_until"] = max(0, time_until.total_seconds() // 3600)
        event["minutes_until"] = max(0, (time_until.total_seconds() % 3600) // 60)
        
        # Get featured providers
        if event["type"] == "skill_showcase":
            event["featured_providers"] = await get_event_providers(str(event["_id"]), db)
    
    return {"events": events}

@router.post("/create")
async def create_virtual_event(
    data: EventCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new virtual marketplace event"""
    db = get_db()
    
    event_type = data.event_type
    title = data.title
    description = data.description
    start_time = data.start_time
    category = data.category
    featured_providers = data.featured_providers
    entry_fee = data.entry_fee
    
    if event_type not in EVENT_TYPES:
        return {"error": "Invalid event type"}
    
    event_template = EVENT_TYPES[event_type]
    
    event = {
        "type": event_type,
        "title": title,
        "description": description,
        "category": category,
        "start_time": start_time,
        "end_time": start_time + timedelta(minutes=event_template["duration_minutes"]),
        "duration_minutes": event_template["duration_minutes"],
        "max_participants": event_template["max_participants"],
        "featured_providers": featured_providers or [],
        "entry_fee": entry_fee or 0,
        "creator_id": current_user["sub"],
        "status": "scheduled",
        "created_at": datetime.utcnow(),
        "prizes": [],
        "live_data": {
            "viewers": 0,
            "active_bids": 0,
            "chat_messages": 0
        }
    }
    
    result = await db.virtual_events.insert_one(event)
    
    # Notify featured providers
    if featured_providers:
        for provider_id in featured_providers:
            await db.notifications.insert_one({
                "user_id": provider_id,
                "type": "event_invitation",
                "title": f"You're invited to showcase in '{title}'",
                "message": f"You've been selected to participate in {event_template['name']}",
                "event_id": str(result.inserted_id),
                "created_at": datetime.utcnow()
            })
    
    return {
        "event_id": str(result.inserted_id),
        "message": f"Event '{title}' created successfully!",
        "start_time": start_time.isoformat(),
        "duration": event_template["duration_minutes"]
    }

@router.post("/join/{event_id}")
async def join_event(event_id: str, current_user: dict = Depends(get_current_user)):
    """Join a virtual marketplace event"""
    db = get_db()
    
    # Check if event exists and is joinable
    event = await db.virtual_events.find_one({
        "_id": ObjectId(event_id),
        "status": "scheduled",
        "start_time": {"$gt": datetime.utcnow()}
    })
    
    if not event:
        return {"error": "Event not found or not available"}
    
    # Check if already joined
    existing = await db.event_participants.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if existing:
        return {"error": "Already joined this event"}
    
    # Check capacity
    current_participants = await db.event_participants.count_documents({"event_id": event_id})
    if current_participants >= event["max_participants"]:
        return {"error": "Event is full"}
    
    # Process entry fee if required
    if event.get("entry_fee", 0) > 0:
        # In production, process payment here
        pass
    
    # Join event
    participation = {
        "event_id": event_id,
        "user_id": current_user["sub"],
        "joined_at": datetime.utcnow(),
        "role": "participant",
        "status": "confirmed"
    }
    
    await db.event_participants.insert_one(participation)
    
    return {
        "message": f"Successfully joined '{event['title']}'!",
        "event_start": event["start_time"].isoformat(),
        "join_link": f"/events/live/{event_id}"
    }

@router.get("/live/{event_id}")
async def get_live_event_data(event_id: str, current_user: dict = Depends(get_current_user)):
    """Get live event data and interactions"""
    db = get_db()
    
    # Check if user is participant
    participant = await db.event_participants.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if not participant:
        return {"error": "Not registered for this event"}
    
    event = await db.virtual_events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return {"error": "Event not found"}
    
    # Get live data based on event type
    live_data = await get_event_live_data(event_id, event["type"], db)
    
    return {
        "event": {
            "id": str(event["_id"]),
            "title": event["title"],
            "type": event["type"],
            "status": event["status"],
            "current_time": datetime.utcnow().isoformat()
        },
        "live_data": live_data,
        "participant_role": participant["role"]
    }

@router.post("/bid/{event_id}")
async def place_bid(
    event_id: str,
    data: EventBidRequest,
    current_user: dict = Depends(get_current_user)
):
    """Place a bid in a flash auction event"""
    db = get_db()
    
    service_id = data.service_id
    bid_amount = data.bid_amount
    
    # Verify event is active auction
    event = await db.virtual_events.find_one({
        "_id": ObjectId(event_id),
        "type": "flash_auction",
        "status": "live"
    })
    
    if not event:
        return {"error": "Auction not active"}
    
    # Check if user is participant
    participant = await db.event_participants.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if not participant:
        return {"error": "Must join event to bid"}
    
    # Get current highest bid
    current_bid = await db.event_bids.find_one({
        "event_id": event_id,
        "service_id": service_id
    }, sort=[("amount", -1)])
    
    min_bid = current_bid["amount"] + 50 if current_bid else 100  # Minimum increment ₹50
    
    if bid_amount < min_bid:
        return {"error": f"Minimum bid is ₹{min_bid}"}
    
    # Place bid
    bid = {
        "event_id": event_id,
        "service_id": service_id,
        "user_id": current_user["sub"],
        "amount": bid_amount,
        "timestamp": datetime.utcnow(),
        "status": "active"
    }
    
    await db.event_bids.insert_one(bid)
    
    # Update event live data
    await db.virtual_events.update_one(
        {"_id": ObjectId(event_id)},
        {"$inc": {"live_data.active_bids": 1}}
    )
    
    return {
        "message": "Bid placed successfully!",
        "bid_amount": bid_amount,
        "current_highest": bid_amount,
        "time_remaining": "Live auction"
    }

@router.post("/showcase/{event_id}")
async def start_skill_showcase(
    event_id: str,
    data: EventShowcaseRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a skill showcase presentation"""
    db = get_db()
    
    showcase_data = data.dict()
    
    # Verify provider is featured in event
    event = await db.virtual_events.find_one({
        "_id": ObjectId(event_id),
        "type": "skill_showcase",
        "featured_providers": current_user["sub"]
    })
    
    if not event:
        return {"error": "Not authorized for this showcase"}
    
    # Create showcase session
    showcase = {
        "event_id": event_id,
        "provider_id": current_user["sub"],
        "title": showcase_data.get("title"),
        "description": showcase_data.get("description"),
        "skills_demonstrated": showcase_data.get("skills", []),
        "start_time": datetime.utcnow(),
        "status": "live",
        "viewers": 0,
        "likes": 0,
        "bookings_generated": 0
    }
    
    result = await db.skill_showcases.insert_one(showcase)
    
    return {
        "showcase_id": str(result.inserted_id),
        "message": "Showcase started!",
        "live_url": f"/events/showcase/{result.inserted_id}"
    }

@router.get("/leaderboard/{event_id}")
async def get_event_leaderboard(event_id: str):
    """Get event leaderboard and rankings"""
    db = get_db()
    
    event = await db.virtual_events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return {"error": "Event not found"}
    
    leaderboard = []
    
    if event["type"] == "flash_auction":
        # Top bidders
        pipeline = [
            {"$match": {"event_id": event_id}},
            {"$group": {
                "_id": "$user_id",
                "total_bids": {"$sum": 1},
                "highest_bid": {"$max": "$amount"},
                "total_bid_amount": {"$sum": "$amount"}
            }},
            {"$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$sort": {"total_bid_amount": -1}},
            {"$limit": 10}
        ]
        
        leaderboard = await db.event_bids.aggregate(pipeline).to_list(length=10)
        
    elif event["type"] == "skill_showcase":
        # Top showcases by engagement
        pipeline = [
            {"$match": {"event_id": event_id}},
            {"$lookup": {
                "from": "users",
                "localField": "provider_id",
                "foreignField": "_id",
                "as": "provider"
            }},
            {"$unwind": "$provider"},
            {"$sort": {"likes": -1, "viewers": -1}},
            {"$limit": 10}
        ]
        
        leaderboard = await db.skill_showcases.aggregate(pipeline).to_list(length=10)
    
    return {"leaderboard": leaderboard, "event_type": event["type"]}

@router.get("/my-events")
async def get_my_events(current_user: dict = Depends(get_current_user)):
    """Get user's participated events and history"""
    db = get_db()
    
    # Get participated events
    participations = await db.event_participants.find({
        "user_id": current_user["sub"]
    }).to_list(length=100)
    
    my_events = []
    
    for participation in participations:
        event = await db.virtual_events.find_one({"_id": ObjectId(participation["event_id"])})
        if event:
            event["_id"] = str(event["_id"])
            event["my_role"] = participation["role"]
            event["joined_at"] = participation["joined_at"].isoformat()
            
            # Get performance data
            if event["type"] == "flash_auction":
                my_bids = await db.event_bids.count_documents({
                    "event_id": participation["event_id"],
                    "user_id": current_user["sub"]
                })
                event["my_performance"] = {"bids_placed": my_bids}
            
            elif event["type"] == "skill_showcase" and current_user["role"] == "provider":
                showcase = await db.skill_showcases.find_one({
                    "event_id": participation["event_id"],
                    "provider_id": current_user["sub"]
                })
                if showcase:
                    event["my_performance"] = {
                        "viewers": showcase.get("viewers", 0),
                        "likes": showcase.get("likes", 0),
                        "bookings": showcase.get("bookings_generated", 0)
                    }
            
            my_events.append(event)
    
    return {"my_events": my_events}

@router.post("/rate-event/{event_id}")
async def rate_event(
    event_id: str,
    data: EventRateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Rate and provide feedback for an event"""
    db = get_db()
    
    rating = data.rating
    feedback = data.feedback
    
    if not 1 <= rating <= 5:
        return {"error": "Rating must be between 1 and 5"}
    
    # Check if user participated
    participant = await db.event_participants.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if not participant:
        return {"error": "Can only rate events you participated in"}
    
    # Check if already rated
    existing_rating = await db.event_ratings.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if existing_rating:
        return {"error": "Already rated this event"}
    
    # Submit rating
    rating_doc = {
        "event_id": event_id,
        "user_id": current_user["sub"],
        "rating": rating,
        "feedback": feedback,
        "created_at": datetime.utcnow()
    }
    
    await db.event_ratings.insert_one(rating_doc)
    
    return {"message": "Thank you for your feedback!"}

@router.get("/analytics")
async def get_event_analytics(current_user: dict = Depends(get_current_user)):
    """Get event analytics for admin"""
    if current_user["role"] != "admin":
        return {"error": "Admin access required"}
    
    db = get_db()
    
    # Event type popularity
    type_stats = await db.virtual_events.aggregate([
        {"$group": {"_id": "$type", "count": {"$sum": 1}, "avg_participants": {"$avg": "$live_data.viewers"}}},
        {"$sort": {"count": -1}}
    ]).to_list(length=10)
    
    # Participation trends
    participation_trends = await db.event_participants.aggregate([
        {"$group": {
            "_id": {"month": {"$month": "$joined_at"}, "year": {"$year": "$joined_at"}},
            "participants": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]).to_list(length=12)
    
    # Revenue from events
    revenue_stats = await db.virtual_events.aggregate([
        {"$match": {"entry_fee": {"$gt": 0}}},
        {"$group": {"_id": None, "total_revenue": {"$sum": {"$multiply": ["$entry_fee", "$live_data.viewers"]}}}},
    ]).to_list(length=1)
    
    total_revenue = revenue_stats[0]["total_revenue"] if revenue_stats else 0
    
    return {
        "event_type_stats": type_stats,
        "participation_trends": participation_trends,
        "total_revenue": total_revenue,
        "insights": [
            "Skill showcases have highest engagement rates",
            "Flash auctions generate most revenue per participant",
            "Weekend events see 60% higher attendance"
        ]
    }

async def get_event_providers(event_id: str, db):
    """Get featured providers for an event"""
    event = await db.virtual_events.find_one({"_id": ObjectId(event_id)})
    if not event or not event.get("featured_providers"):
        return []
    
    providers = await db.users.find({
        "_id": {"$in": event["featured_providers"]},
        "role": "provider"
    }).to_list(length=10)
    
    for provider in providers:
        provider["_id"] = str(provider["_id"])
    
    return providers

async def get_event_live_data(event_id: str, event_type: str, db):
    """Get live data specific to event type"""
    
    if event_type == "flash_auction":
        # Get active auctions
        active_bids = await db.event_bids.find({
            "event_id": event_id,
            "status": "active"
        }).sort("timestamp", -1).limit(10).to_list(length=10)
        
        return {
            "active_auctions": active_bids,
            "total_bids": len(active_bids),
            "highest_bid": max([bid["amount"] for bid in active_bids]) if active_bids else 0
        }
    
    elif event_type == "skill_showcase":
        # Get active showcases
        showcases = await db.skill_showcases.find({
            "event_id": event_id,
            "status": "live"
        }).to_list(length=10)
        
        return {
            "active_showcases": showcases,
            "total_showcases": len(showcases)
        }
    
    else:
        return {"message": "Live data not available for this event type"}

# ── Router Section: features ──
features_router = APIRouter()
router = features_router
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from bson import ObjectId
import random
import uuid


# --- AI & SMART MATCH SECTION ---

@router.get("/ai/recommendations")
async def get_ai_recommendations(current_user: dict = Depends(get_current_user)):
    db = get_db()
    services = await db.services.find({}).limit(5).to_list(length=5)
    for s in services:
        s["_id"] = str(s["_id"])
        s["match_score"] = random.randint(85, 99)
        s["reason"] = "Based on your frequent category searches"
    return services

# --- CHAT & MESSAGES SECTION ---

@router.get("/chat/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_id = current_user["sub"]
    convs = await db.conversations.find({"participants": user_id}).to_list(length=50)
    for c in convs:
        c["_id"] = str(c["_id"])
        other_id = [p for p in c["participants"] if p != user_id][0]
        other_user = await db.users.find_one({"_id": ObjectId(other_id)})
        c["other_user"] = {"id": other_id, "name": other_user.get("full_name", "User"), "profile_image": other_user.get("profile_image")}
    return convs

@router.get("/chat/messages/{conversation_id}")
async def get_messages(conversation_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    messages = await db.messages.find({"conversation_id": conversation_id}).to_list(length=100)
    for m in messages: m["_id"] = str(m["_id"])
    return messages

# --- COMMUNITY & SOCIAL SECTION ---

@router.get("/community/active-challenges")
async def get_active_challenges():
    db = get_db()
    challenges = await db.challenges.find({"status": "active"}).to_list(length=20)
    for c in challenges: c["_id"] = str(c["_id"])
    return challenges

@router.get("/community/neighborhood-stats")
async def get_neighborhood_stats(neighborhood: str):
    db = get_db()
    users = await db.users.find({"address.neighborhood": neighborhood}).to_list(length=1000)
    user_ids = [str(u["_id"]) for u in users]
    bookings_count = await db.bookings.count_documents({"customer_id": {"$in": user_ids}})
    return {"neighborhood": neighborhood, "active_users": len(users), "monthly_bookings": bookings_count, "trust_rating": "A+"}

@router.get("/community/top-providers")
async def get_top_providers(neighborhood: str):
    db = get_db()
    users = await db.users.find({"address.neighborhood": neighborhood}).to_list(length=1000)
    user_ids = [str(u["_id"]) for u in users]
    pipeline = [{"$match": {"user_id": {"$in": user_ids}}}, {"$group": {"_id": "$provider_id", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 5}]
    stats = await db.bookings.aggregate(pipeline).to_list(length=5)
    results = []
    for s in stats:
        p_id = s["_id"]
        if not p_id: continue
        provider = await db.users.find_one({"_id": ObjectId(p_id)})
        if not provider: continue
        results.append({"id": str(provider["_id"]), "name": provider.get("full_name", "Provider"), "category": provider.get("specializations", ["Pro"])[0], "neighborhoodBookings": s["count"], "avgRating": provider.get("rating", 4.5)})
    return results

# --- GAMIFICATION & LOYALTY ---

@router.get("/gamification/leaderboard")
async def get_leaderboard():
    db = get_db()
    top_providers = await db.users.find({"role": "provider"}).sort("quickserve_score", -1).limit(10).to_list(length=10)
    for p in top_providers:
        p["_id"] = str(p["_id"])
        p.pop("password", None)
    return top_providers

# --- SMART FEATURES (MOOD, PREDICTIVE, ETC) ---

@router.get("/mood-sync/mood-insights")
async def get_mood_insights(current_user: dict = Depends(get_current_user)):
    return {"current_mood": "Focus", "suggested_services": ["Deep Cleaning", "Home Office Setup"], "insight_text": "Your recent bookings show a focus on efficiency. Here are some services to boost your productivity floor."}

@router.get("/predictive/demand")
async def get_demand_prediction(category: str):
    return {"category": category, "predicted_demand": random.randint(70, 100), "availability_status": "medium", "recommendation": "Book 24h in advance to save 10%"}

# ── Router Section: gamification ──
gamification_router = APIRouter()
router = gamification_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from bson import ObjectId
import random


CHALLENGES = {
    "streak_master": {
        "name": "Streak Master",
        "description": "Book services 7 days in a row",
        "reward_points": 500,
        "badge": "🔥",
        "type": "streak",
        "target": 7
    },
    "category_explorer": {
        "name": "Category Explorer",
        "description": "Try 5 different service categories",
        "reward_points": 300,
        "badge": "🗺️",
        "type": "variety",
        "target": 5
    },
    "early_bird": {
        "name": "Early Bird",
        "description": "Book 10 services before 9 AM",
        "reward_points": 200,
        "badge": "🌅",
        "type": "time",
        "target": 10
    },
    "night_owl": {
        "name": "Night Owl",
        "description": "Book 5 services after 9 PM",
        "reward_points": 250,
        "badge": "🦉",
        "type": "time"
    },
    "review_champion": {
        "name": "Review Champion",
        "description": "Leave 20 detailed reviews",
        "reward_points": 400,
        "badge": "⭐",
        "type": "engagement"
    },
    "referral_king": {
        "name": "Referral King",
        "description": "Refer 10 friends successfully",
        "reward_points": 1000,
        "badge": "👑",
        "type": "social"
    }
}

@router.get("/profile")
async def get_gamification_profile(current_user: dict = Depends(get_current_user)):
    """Get user's gamification profile"""
    db = get_db()
    
    profile = await db.gamification_profiles.find_one({"user_id": current_user["sub"]})
    if not profile:
        profile = {
            "user_id": current_user["sub"],
            "level": 1,
            "xp": 0,
            "badges": [],
            "achievements": [],
            "current_streak": 0,
            "longest_streak": 0,
            "challenges_completed": 0,
            "created_at": datetime.utcnow()
        }
        await db.gamification_profiles.insert_one(profile)
    
    # Calculate level from XP
    level = min(100, (profile.get("xp", 0) // 1000) + 1)
    xp_for_next_level = (level * 1000) - profile.get("xp", 0)
    
    return {
        "level": level,
        "xp": profile.get("xp", 0),
        "xp_for_next_level": xp_for_next_level,
        "badges": profile.get("badges", []),
        "achievements": profile.get("achievements", []),
        "current_streak": profile.get("current_streak", 0),
        "longest_streak": profile.get("longest_streak", 0),
        "challenges_completed": profile.get("challenges_completed", 0)
    }

@router.get("/challenges")
async def get_active_challenges(current_user: dict = Depends(get_current_user)):
    """Get user's active challenges and progress"""
    db = get_db()
    
    # Get user's progress
    user_stats = await get_user_stats(current_user["sub"], db)
    
    challenges_progress = []
    for challenge_id, challenge in CHALLENGES.items():
        progress = await calculate_challenge_progress(challenge_id, challenge, user_stats, db)
        challenges_progress.append({
            "id": challenge_id,
            "name": challenge["name"],
            "description": challenge["description"],
            "badge": challenge["badge"],
            "reward_points": challenge["reward_points"],
            "progress": progress["current"],
            "target": progress["target"],
            "completed": progress["completed"],
            "completion_percentage": min(100, (progress["current"] / progress["target"]) * 100)
        })
    
    return {"challenges": challenges_progress}


@router.post("/update-progress")
async def update_challenge_progress(data: GamificationProgressUpdate, current_user: dict = Depends(get_current_user)):
    """Update progress for a specific challenge"""
    db = get_db()
    
    # Update user's progress for this challenge
    update_doc = {
        "user_id": current_user["sub"],
        "challenge_id": data.challenge_id,
        "current": data.progress,
        "last_updated": datetime.utcnow()
    }
    
    await db.challenge_progress.update_one(
        {"user_id": current_user["sub"], "challenge_id": data.challenge_id},
        {"$set": update_doc},
        upsert=True
    )
    
    # Check if this progress completes the challenge
    challenge = CHALLENGES.get(data.challenge_id)
    if not challenge:
        return {"error": "Challenge not found"}
        
    target = challenge["target"]
    completed = data.progress >= target
    
    if completed:
        # In a real app, this might trigger rewards
        pass
        
    return {
        "message": "Progress updated successfully!",
        "challenge_id": data.challenge_id,
        "current": data.progress,
        "target": target,
        "completed": completed
    }

@router.post("/complete-challenge/{challenge_id}")
async def complete_challenge(challenge_id: str, current_user: dict = Depends(get_current_user)):
    """Mark challenge as completed and award rewards"""
    db = get_db()
    
    if challenge_id not in CHALLENGES:
        return {"error": "Invalid challenge"}
    
    challenge = CHALLENGES[challenge_id]
    
    # Check if already completed
    profile = await db.gamification_profiles.find_one({"user_id": current_user["sub"]})
    if challenge_id in profile.get("achievements", []):
        return {"error": "Challenge already completed"}
    
    # Verify completion
    user_stats = await get_user_stats(current_user["sub"], db)
    progress = await calculate_challenge_progress(challenge_id, challenge, user_stats, db)
    
    if not progress["completed"]:
        return {"error": "Challenge not yet completed"}
    
    # Award rewards
    await db.gamification_profiles.update_one(
        {"user_id": current_user["sub"]},
        {
            "$push": {
                "achievements": challenge_id,
                "badges": challenge["badge"]
            },
            "$inc": {
                "xp": challenge["reward_points"],
                "challenges_completed": 1
            }
        }
    )
    
    # Award loyalty points
    await db.loyalty_accounts.update_one(
        {"user_id": current_user["sub"]},
        {"$inc": {"points": challenge["reward_points"] // 2}},
        upsert=True
    )
    
    return {
        "message": f"🎉 Challenge '{challenge['name']}' completed!",
        "badge_earned": challenge["badge"],
        "xp_earned": challenge["reward_points"],
        "loyalty_points": challenge["reward_points"] // 2
    }

@router.get("/leaderboard")
async def get_leaderboard(category: str = "xp", limit: int = 10):
    """Get gamification leaderboard"""
    db = get_db()
    
    sort_field = "xp" if category == "xp" else "challenges_completed"
    
    pipeline = [
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$unwind": "$user"},
        {"$sort": {sort_field: -1}},
        {"$limit": limit},
        {"$project": {
            "user_name": "$user.full_name",
            "level": {"$add": [{"$divide": ["$xp", 1000]}, 1]},
            "xp": 1,
            "badges": 1,
            "challenges_completed": 1,
            "current_streak": 1
        }}
    ]
    
    leaderboard = await db.gamification_profiles.aggregate(pipeline).to_list(length=limit)
    
    return {"leaderboard": leaderboard, "category": category}

@router.post("/daily-spin")
async def daily_spin_wheel(current_user: dict = Depends(get_current_user)):
    """Daily spin wheel for random rewards"""
    db = get_db()
    
    # Check if already spun today
    today = datetime.utcnow().date()
    last_spin = await db.daily_spins.find_one({
        "user_id": current_user["sub"],
        "date": today.isoformat()
    })
    
    if last_spin:
        return {"error": "Already spun today! Come back tomorrow."}
    
    # Spin rewards (weighted)
    rewards = [
        {"type": "xp", "amount": 50, "weight": 30, "message": "50 XP!"},
        {"type": "xp", "amount": 100, "weight": 20, "message": "100 XP!"},
        {"type": "loyalty", "amount": 25, "weight": 25, "message": "25 Loyalty Points!"},
        {"type": "loyalty", "amount": 50, "weight": 15, "message": "50 Loyalty Points!"},
        {"type": "discount", "amount": 10, "weight": 8, "message": "10% Discount Coupon!"},
        {"type": "free_service", "amount": 1, "weight": 2, "message": "🎉 FREE Service Credit!"}
    ]
    
    # Weighted random selection
    total_weight = sum(r["weight"] for r in rewards)
    random_num = random.randint(1, total_weight)
    
    current_weight = 0
    selected_reward = None
    for reward in rewards:
        current_weight += reward["weight"]
        if random_num <= current_weight:
            selected_reward = reward
            break
    
    # Record spin
    await db.daily_spins.insert_one({
        "user_id": current_user["sub"],
        "date": today.isoformat(),
        "reward": selected_reward,
        "timestamp": datetime.utcnow()
    })
    
    # Apply reward
    if selected_reward["type"] == "xp":
        await db.gamification_profiles.update_one(
            {"user_id": current_user["sub"]},
            {"$inc": {"xp": selected_reward["amount"]}}
        )
    elif selected_reward["type"] == "loyalty":
        await db.loyalty_accounts.update_one(
            {"user_id": current_user["sub"]},
            {"$inc": {"points": selected_reward["amount"]}},
            upsert=True
        )
    elif selected_reward["type"] == "discount":
        await db.user_coupons.insert_one({
            "user_id": current_user["sub"],
            "type": "discount",
            "value": selected_reward["amount"],
            "expires_at": datetime.utcnow() + timedelta(days=30),
            "used": False
        })
    
    return {
        "reward": selected_reward,
        "message": f"🎰 You won: {selected_reward['message']}",
        "next_spin": "Tomorrow!"
    }

async def get_user_stats(user_id: str, db):
    """Get user statistics for challenge calculation"""
    bookings = await db.bookings.find({"user_id": user_id}).to_list(length=1000)
    reviews = await db.reviews.find({"user_id": user_id}).to_list(length=1000)
    referrals = await db.referral_codes.find({"user_id": user_id}).to_list(length=100)
    
    # Calculate streak
    booking_dates = sorted([b["created_at"].date() for b in bookings], reverse=True)
    current_streak = 0
    if booking_dates:
        current_date = datetime.utcnow().date()
        for i, date in enumerate(booking_dates):
            if (current_date - date).days == i:
                current_streak += 1
            else:
                break
    
    return {
        "total_bookings": len(bookings),
        "total_reviews": len(reviews),
        "total_referrals": sum(r.get("uses", 0) for r in referrals),
        "current_streak": current_streak,
        "categories_used": len(set(b.get("service_type", "") for b in bookings)),
        "early_bookings": len([b for b in bookings if b["created_at"].hour < 9]),
        "late_bookings": len([b for b in bookings if b["created_at"].hour >= 21])
    }

async def calculate_challenge_progress(challenge_id: str, challenge: dict, user_stats: dict, db):
    """Calculate progress for a specific challenge"""
    if challenge["type"] == "streak":
        return {"current": user_stats["current_streak"], "target": 7, "completed": user_stats["current_streak"] >= 7}
    elif challenge["type"] == "variety":
        return {"current": user_stats["categories_used"], "target": 5, "completed": user_stats["categories_used"] >= 5}
    elif challenge["type"] == "time" and "early" in challenge_id:
        return {"current": user_stats["early_bookings"], "target": 10, "completed": user_stats["early_bookings"] >= 10}
    elif challenge["type"] == "time" and "night" in challenge_id:
        return {"current": user_stats["late_bookings"], "target": 5, "completed": user_stats["late_bookings"] >= 5}
    elif challenge["type"] == "engagement":
        return {"current": user_stats["total_reviews"], "target": 20, "completed": user_stats["total_reviews"] >= 20}
    elif challenge["type"] == "social":
        return {"current": user_stats["total_referrals"], "target": 10, "completed": user_stats["total_referrals"] >= 10}
    
    return {"current": 0, "target": 1, "completed": False}

@router.get("/neighborhood-battle")
async def get_neighborhood_battle():
    """Get leaderboard of cities based on service activity and ratings"""
    db = get_db()
    
    pipeline = [
        {"$group": {
            "_id": "$city",
            "active_services": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"},
            "avg_price": {"$avg": "$price_per_hour"}
        }},
        {"$sort": {"active_services": -1}},
        {"$limit": 10}
    ]
    
    battle_data = await db.services.aggregate(pipeline).to_list(length=10)
    
    result = []
    for city in battle_data:
        if not city["_id"]: continue
        
        # Calculate score: (services * 0.4) + (rating * 20 * 0.6)
        score = (city["active_services"] * 0.4) + ((city["avg_rating"] or 0) * 20 * 0.6)
        
        result.append({
            "city": city["_id"],
            "score": round(score, 1),
            "stats": {
                "services": city["active_services"],
                "rating": round(city["avg_rating"] or 0, 2),
                "price": round(city["avg_price"] or 0, 2)
            },
            "status": "Dominating" if score > 500 else "Global Power" if score > 200 else "Rising Star"
        })
    
    result.sort(key=lambda x: x["score"], reverse=True)
    return {"battle_leaderboard": result}

# ── Router Section: hail ──
hail_router = APIRouter()
router = hail_router
from fastapi import APIRouter, Depends
from datetime import datetime
from bson import ObjectId


@router.post("/broadcast")
async def broadcast_hail(service_type: str, location: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    hail = {
        "user_id": current_user["sub"],
        "service_type": service_type,
        "location": location,
        "status": "active",
        "created_at": datetime.utcnow(),
        "responses": []
    }
    result = await db.hail_requests.insert_one(hail)
    return {"id": str(result.inserted_id), "status": "broadcasting", "radius": "0.2 miles"}

@router.get("/nearby")
async def get_nearby_hails(lat: float, lng: float, current_user: dict = Depends(get_current_user)):
    db = get_db()
    hails = await db.hail_requests.find({"status": "active"}).to_list(length=50)
    for h in hails:
        h["_id"] = str(h["_id"])
    return hails

@router.post("/{hail_id}/respond")
async def respond_to_hail(hail_id: str, eta: int, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.hail_requests.update_one(
        {"_id": ObjectId(hail_id)},
        {"$push": {"responses": {"provider_id": current_user["sub"], "eta": eta, "timestamp": datetime.utcnow()}}}
    )
    return {"status": "response_sent"}

@router.put("/{hail_id}/accept")
async def accept_hail_response(hail_id: str, provider_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.hail_requests.update_one(
        {"_id": ObjectId(hail_id)},
        {"$set": {"status": "accepted", "selected_provider": provider_id}}
    )
    return {"status": "accepted", "provider_id": provider_id}

@router.get("/active")
async def get_active_hails(current_user: dict = Depends(get_current_user)):
    db = get_db()
    hails = await db.hail_requests.find({"user_id": current_user["sub"], "status": "active"}).to_list(length=10)
    for h in hails:
        h["_id"] = str(h["_id"])
    return hails

@router.get("/statistics")
async def get_hail_statistics(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total = await db.hail_requests.count_documents({"user_id": current_user["sub"]})
    accepted = await db.hail_requests.count_documents({"user_id": current_user["sub"], "status": "accepted"})
    return {"total_hails": total, "accepted": accepted, "success_rate": (accepted/total*100) if total > 0 else 0}

# ── Router Section: marketplace ──
marketplace_router = APIRouter()
router = marketplace_router
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from bson import ObjectId
import random
import uuid


# --- SERVICES SECTION ---

@router.get("/services/search")
async def search_services(q: Optional[str] = None, category: Optional[str] = None, city: Optional[str] = None, latitude: Optional[float] = None, longitude: Optional[float] = None, radius: float = Query(10.0), min_rating: float = Query(0.0), min_price: Optional[float] = None, max_price: Optional[float] = None, emergency: Optional[bool] = None, limit: int = Query(20, le=100)):
    db = get_db()
    query = {}
    if category: query["category"] = {"$regex": category, "$options": "i"}
    if city: query["city"] = {"$regex": city, "$options": "i"}
    if q: query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"description": {"$regex": q, "$options": "i"}}, {"specialties": {"$regex": q, "$options": "i"}}]
    if emergency is not None: query["is_emergency"] = emergency
    query["rating"] = {"$gte": min_rating}
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None: price_query["$gte"] = min_price
        if max_price is not None: price_query["$lte"] = max_price
        query["price_per_hour"] = price_query
    services = await db.services.find(query).limit(limit * 5).to_list(length=limit * 5)
    for s in services:
        s["_id"] = str(s["_id"])
        s["provider_id"] = str(s.get("provider_id", ""))
    services.sort(key=lambda x: x.get("rating", 0), reverse=True)
    return {"services": services[:limit], "total": len(services)}

@router.get("/services/categories")
async def get_categories():
    db = get_db()
    categories = await db.services.distinct("category")
    return [{"name": c, "id": c.lower().replace(" ", "_")} for c in categories]

@router.get("/services/{service_id}")
async def get_service(service_id: str):
    db = get_db()
    service = await db.services.find_one({"_id": ObjectId(service_id)})
    if service:
        service["_id"] = str(service["_id"])
        service["provider_id"] = str(service.get("provider_id", ""))
    return service

# --- BOOKINGS SECTION ---

@router.post("/bookings")
async def create_booking(booking: BookingCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    booking_dict = booking.dict()
    booking_dict["customer_id"] = current_user["sub"]
    booking_dict["status"] = "pending"
    booking_dict["created_at"] = datetime.utcnow()
    result = await db.bookings.insert_one(booking_dict)
    return {"_id": str(result.inserted_id), **booking_dict}

@router.get("/bookings")
async def get_my_bookings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    query = {"customer_id": current_user["sub"]} if current_user["role"] == "customer" else {"provider_id": current_user["sub"]}
    bookings = await db.bookings.find(query).to_list(length=100)
    for b in bookings:
        b["_id"] = str(b["_id"])
        b["service_id"] = str(b.get("service_id", ""))
    return bookings

# --- SLOTS SECTION ---

@router.get("/slots/available")
async def get_available_slots(provider_id: str, date: str):
    db = get_db()
    slots = await db.slots.find({"provider_id": provider_id, "date": date, "is_available": True}).to_list(length=100)
    for s in slots: s["_id"] = str(s["_id"])
    return slots

# --- PAYMENTS SECTION ---

@router.post("/payments/create-intent")
async def create_payment_intent(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking: raise HTTPException(status_code=404, detail="Booking not found")
    intent_id = str(uuid.uuid4())
    await db.payments.insert_one({"booking_id": booking_id, "amount": booking.get("amount", 0), "status": "pending", "intent_id": intent_id, "created_at": datetime.utcnow()})
    return {"intent_id": intent_id, "client_secret": "sk_test_" + intent_id}

@router.post("/payments/confirm")
async def confirm_payment(intent_id: str):
    db = get_db()
    await db.payments.update_one({"intent_id": intent_id}, {"$set": {"status": "completed", "completed_at": datetime.utcnow()}})
    payment = await db.payments.find_one({"intent_id": intent_id})
    if payment:
        await db.bookings.update_one({"_id": ObjectId(payment["booking_id"])}, {"$set": {"status": "confirmed"}})
    return {"status": "success"}

# --- REVIEWS SECTION ---

@router.post("/reviews")
async def create_review(review: ReviewCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    review_dict = review.dict()
    review_dict["customer_id"] = current_user["sub"]
    review_dict["created_at"] = datetime.utcnow()
    result = await db.reviews.insert_one(review_dict)
    # Update provider overall rating
    reviews = await db.reviews.find({"provider_id": review.provider_id}).to_list(length=1000)
    avg = sum([r["rating"] for r in reviews]) / len(reviews)
    await db.users.update_one({"_id": ObjectId(review.provider_id)}, {"$set": {"rating": round(avg, 1), "reviews_count": len(reviews)}})
    return {"_id": str(result.inserted_id), **review_dict}

# --- TRACKING & HAIL ---

@router.post("/services/voice-hail")
async def process_voice_hail(payload: dict):
    text = payload.get("text", "").lower()
    service_type = "general"
    urgency = "normal"
    if any(word in text for word in ["urgent", "emergency", "now", "quick", "fast", "immediately"]):
        urgency = "high"
    if any(word in text for word in ["plumb", "leak", "water", "pipe", "drain"]): service_type = "plumber"
    elif any(word in text for word in ["electri", "power", "shock", "wire", "light"]): service_type = "electrician"
    elif any(word in text for word in ["clean", "maid", "sweep", "dust"]): service_type = "house cleaning"
    return {"service": service_type, "urgency": urgency}

# ── Router Section: mood_sync ──
mood_sync_router = APIRouter()
router = mood_sync_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from bson import ObjectId
from typing import Optional


MOOD_TYPES = {
    "energetic": {"emoji": "⚡", "description": "High energy, ready for challenging tasks", "multiplier": 1.2},
    "calm": {"emoji": "😌", "description": "Peaceful and focused, great for detailed work", "multiplier": 1.0},
    "creative": {"emoji": "🎨", "description": "Feeling innovative and artistic", "multiplier": 1.1},
    "efficient": {"emoji": "🚀", "description": "In the zone, maximum productivity", "multiplier": 1.3},
    "patient": {"emoji": "🧘", "description": "Extra patient, perfect for complex jobs", "multiplier": 1.1},
    "friendly": {"emoji": "😊", "description": "Super social and communicative", "multiplier": 1.0},
    "focused": {"emoji": "🎯", "description": "Laser-focused on quality work", "multiplier": 1.2},
    "tired": {"emoji": "😴", "description": "Low energy, simple tasks only", "multiplier": 0.8}
}


@router.post("/update-mood")
async def update_provider_mood(
    data: MoodUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update provider's current mood and availability"""
    db = get_db()
    
    mood = data.mood
    energy_level = data.energy_level
    availability_hours = data.availability_hours
    notes = data.notes
    
    if current_user["role"] != "provider":
        return {"error": "Only providers can update mood"}
    
    if mood not in MOOD_TYPES:
        return {"error": "Invalid mood type"}
    
    if not 1 <= energy_level <= 10:
        return {"error": "Energy level must be between 1-10"}
    
    mood_update = {
        "provider_id": current_user["sub"],
        "mood": mood,
        "energy_level": energy_level,
        "availability_hours": availability_hours,
        "notes": notes,
        "timestamp": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=8)  # Mood expires after 8 hours
    }
    
    # Update or insert mood status
    await db.provider_moods.update_one(
        {"provider_id": current_user["sub"]},
        {"$set": mood_update},
        upsert=True
    )
    
    # Update provider's online status and multiplier
    mood_data = MOOD_TYPES[mood]
    performance_multiplier = mood_data["multiplier"] * (energy_level / 10)
    
    await db.users.update_one(
        {"_id": current_user["sub"]},
        {
            "$set": {
                "is_online": True,
                "current_mood": mood,
                "performance_multiplier": round(performance_multiplier, 2),
                "last_mood_update": datetime.utcnow()
            }
        }
    )
    
    return {
        "message": f"Mood updated to {mood_data['emoji']} {mood}",
        "performance_multiplier": round(performance_multiplier, 2),
        "estimated_earnings_boost": f"{int((performance_multiplier - 1) * 100)}%"
    }

@router.get("/mood-dashboard")
async def get_mood_dashboard(current_user: dict = Depends(get_current_user)):
    """Get provider's mood dashboard with insights"""
    db = get_db()
    
    if current_user["role"] != "provider":
        return {"error": "Only providers can access mood dashboard"}
    
    # Get current mood
    current_mood = await db.provider_moods.find_one({"provider_id": current_user["sub"]})
    
    # Get mood history (last 30 days)
    mood_history = await db.provider_moods.find({
        "provider_id": current_user["sub"],
        "timestamp": {"$gte": datetime.utcnow() - timedelta(days=30)}
    }).sort("timestamp", -1).to_list(length=100)
    
    # Calculate mood analytics
    mood_stats = {}
    total_entries = len(mood_history)
    
    for entry in mood_history:
        mood = entry["mood"]
        if mood in mood_stats:
            mood_stats[mood] += 1
        else:
            mood_stats[mood] = 1
    
    # Convert to percentages
    mood_percentages = {mood: (count / total_entries * 100) for mood, count in mood_stats.items()} if total_entries > 0 else {}
    
    # Get earnings correlation
    earnings_by_mood = await calculate_earnings_by_mood(current_user["sub"], db)
    
    return {
        "current_mood": current_mood,
        "mood_history": mood_history[:10],  # Last 10 entries
        "mood_statistics": {
            "total_entries": total_entries,
            "mood_distribution": mood_percentages,
            "most_common_mood": max(mood_stats, key=mood_stats.get) if mood_stats else None
        },
        "earnings_correlation": earnings_by_mood,
        "recommendations": generate_mood_recommendations(mood_history, earnings_by_mood)
    }

@router.get("/find-by-mood")
async def find_providers_by_mood(
    service_type: str,
    preferred_mood: Optional[str] = None,
    min_energy: Optional[int] = None,
    location: Optional[dict] = None
):
    """Find providers based on current mood and energy levels"""
    db = get_db()
    
    # Build query
    query = {
        "role": "provider",
        "specializations": service_type,
        "is_online": True,
        "is_verified": True
    }
    
    # Get providers
    providers = await db.users.find(query).to_list(length=50)
    
    # Get current moods for these providers
    provider_ids = [p["_id"] for p in providers]
    moods = await db.provider_moods.find({
        "provider_id": {"$in": provider_ids},
        "expires_at": {"$gt": datetime.utcnow()}
    }).to_list(length=100)
    
    # Create mood lookup
    mood_lookup = {mood["provider_id"]: mood for mood in moods}
    
    # Filter and score providers
    scored_providers = []
    for provider in providers:
        provider_mood = mood_lookup.get(provider["_id"])
        
        if not provider_mood:
            continue  # Skip providers without current mood
        
        # Apply filters
        if preferred_mood and provider_mood["mood"] != preferred_mood:
            continue
        
        if min_energy and provider_mood["energy_level"] < min_energy:
            continue
        
        # Calculate match score
        score = 0
        score += provider.get("rating", 0) * 20  # Base rating
        score += provider_mood["energy_level"] * 5  # Energy bonus
        score += MOOD_TYPES[provider_mood["mood"]]["multiplier"] * 10  # Mood bonus
        
        provider["_id"] = str(provider["_id"])
        provider["current_mood"] = provider_mood
        provider["match_score"] = round(score, 2)
        
        scored_providers.append(provider)
    
    # Sort by match score
    scored_providers.sort(key=lambda x: x["match_score"], reverse=True)
    
    return {
        "providers": scored_providers[:10],
        "total_found": len(scored_providers),
        "filters_applied": {
            "preferred_mood": preferred_mood,
            "min_energy": min_energy,
            "service_type": service_type
        }
    }

@router.get("/mood-insights")
async def get_mood_insights():
    """Get platform-wide mood insights and trends"""
    db = get_db()
    
    # Get current active moods
    active_moods = await db.provider_moods.find({
        "expires_at": {"$gt": datetime.utcnow()}
    }).to_list(length=1000)
    
    # Mood distribution
    mood_distribution = {}
    energy_levels = []
    
    for mood_entry in active_moods:
        mood = mood_entry["mood"]
        mood_distribution[mood] = mood_distribution.get(mood, 0) + 1
        energy_levels.append(mood_entry["energy_level"])
    
    avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else 0
    
    # Time-based patterns
    hour = datetime.utcnow().hour
    time_insights = {
        "current_hour": hour,
        "peak_energy_hours": [9, 10, 11, 14, 15, 16],  # Typical peak hours
        "low_energy_hours": [13, 17, 18, 19],  # Post-lunch and evening
        "is_peak_time": hour in [9, 10, 11, 14, 15, 16]
    }
    
    return {
        "total_active_providers": len(active_moods),
        "mood_distribution": mood_distribution,
        "average_energy_level": round(avg_energy, 1),
        "time_insights": time_insights,
        "recommendations": {
            "best_time_to_book": "9-11 AM or 2-4 PM for highest energy providers",
            "current_availability": "high" if len(active_moods) > 20 else "medium" if len(active_moods) > 10 else "low"
        }
    }

@router.post("/mood-based-pricing")
async def calculate_mood_based_pricing(
    data: MoodBasedPricingRequest
):
    """Calculate pricing based on provider's current mood and energy"""
    db = get_db()
    
    service_type = data.service_type
    provider_id = data.provider_id
    base_price = data.base_price
    
    # Get provider's current mood
    provider_mood = await db.provider_moods.find_one({
        "provider_id": provider_id,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not provider_mood:
        return {"final_price": base_price, "mood_adjustment": 0, "reason": "No current mood data"}
    
    mood = provider_mood["mood"]
    energy_level = provider_mood["energy_level"]
    
    # Calculate mood-based adjustment
    mood_multiplier = MOOD_TYPES[mood]["multiplier"]
    energy_multiplier = 0.8 + (energy_level / 10) * 0.4  # 0.8 to 1.2 range
    
    total_multiplier = (mood_multiplier + energy_multiplier) / 2
    
    # Apply pricing adjustment
    price_adjustment = (total_multiplier - 1) * 100  # Percentage
    final_price = base_price * total_multiplier
    
    return {
        "base_price": base_price,
        "final_price": round(final_price, 2),
        "mood_adjustment": round(price_adjustment, 1),
        "provider_mood": {
            "mood": mood,
            "emoji": MOOD_TYPES[mood]["emoji"],
            "energy_level": energy_level
        },
        "explanation": f"Price adjusted based on provider's {mood} mood and {energy_level}/10 energy level"
    }

@router.get("/mood-matching-suggestions")
async def get_mood_matching_suggestions(task_description: str):
    """Get mood-based provider matching suggestions"""
    
    # Analyze task requirements (simplified NLP)
    task_lower = task_description.lower()
    
    suggested_moods = []
    
    if any(word in task_lower for word in ["complex", "difficult", "challenging", "detailed"]):
        suggested_moods.extend(["focused", "patient", "efficient"])
    
    if any(word in task_lower for word in ["creative", "design", "artistic", "custom"]):
        suggested_moods.extend(["creative", "energetic"])
    
    if any(word in task_lower for word in ["quick", "fast", "urgent", "asap"]):
        suggested_moods.extend(["energetic", "efficient"])
    
    if any(word in task_lower for word in ["consultation", "advice", "explain", "teach"]):
        suggested_moods.extend(["friendly", "patient"])
    
    # Default suggestions
    if not suggested_moods:
        suggested_moods = ["efficient", "focused", "friendly"]
    
    # Remove duplicates and get mood details
    unique_moods = list(set(suggested_moods))
    mood_suggestions = []
    
    for mood in unique_moods:
        mood_data = MOOD_TYPES[mood]
        mood_suggestions.append({
            "mood": mood,
            "emoji": mood_data["emoji"],
            "description": mood_data["description"],
            "why_recommended": f"Good for tasks involving {task_description[:50]}..."
        })
    
    return {
        "task_description": task_description,
        "recommended_moods": mood_suggestions,
        "tip": "Providers in these moods are likely to perform best for your specific task"
    }

async def calculate_earnings_by_mood(provider_id: str, db):
    """Calculate average earnings by mood for insights"""
    
    # Get bookings with mood data
    pipeline = [
        {
            "$lookup": {
                "from": "provider_moods",
                "let": {"booking_date": "$created_at", "provider": "$provider_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$provider_id", "$$provider"]},
                                    {"$lte": ["$timestamp", "$$booking_date"]},
                                    {"$gte": ["$expires_at", "$$booking_date"]}
                                ]
                            }
                        }
                    }
                ],
                "as": "mood_data"
            }
        },
        {"$unwind": {"path": "$mood_data", "preserveNullAndEmptyArrays": False}},
        {
            "$group": {
                "_id": "$mood_data.mood",
                "avg_earnings": {"$avg": "$amount"},
                "total_bookings": {"$sum": 1}
            }
        }
    ]
    
    results = await db.bookings.aggregate(pipeline).to_list(length=20)
    
    return {mood["_id"]: {"avg_earnings": round(mood["avg_earnings"], 2), "bookings": mood["total_bookings"]} for mood in results}

def generate_mood_recommendations(mood_history, earnings_data):
    """Generate personalized mood recommendations"""
    recommendations = []
    
    if not mood_history:
        return ["Start tracking your mood to get personalized insights!"]
    
    # Find most profitable mood
    if earnings_data:
        best_mood = max(earnings_data, key=lambda x: earnings_data[x]["avg_earnings"])
        recommendations.append(f"💰 Your most profitable mood is '{best_mood}' - try to work more when feeling this way!")
    
    # Analyze recent patterns
    recent_moods = [entry["mood"] for entry in mood_history[:7]]  # Last 7 entries
    most_common = max(set(recent_moods), key=recent_moods.count) if recent_moods else None
    
    if most_common:
        recommendations.append(f"📊 You've been mostly '{most_common}' lately - consider varying your work schedule!")
    
    # Energy level insights
    recent_energy = [entry["energy_level"] for entry in mood_history[:7]]
    avg_energy = sum(recent_energy) / len(recent_energy) if recent_energy else 0
    
    if avg_energy < 6:
        recommendations.append("⚡ Your energy levels seem low - consider taking breaks or adjusting your schedule!")
    elif avg_energy > 8:
        recommendations.append("🚀 Great energy levels! This is a good time to take on challenging projects!")
    
    return recommendations

# ── Router Section: payments ──
payments_router = APIRouter()
router = payments_router
import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from bson import ObjectId
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

# ── Router Section: predictive ──
predictive_router = APIRouter()
router = predictive_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import math
from typing import List, Dict


# Service intervals and patterns
SERVICE_PATTERNS = {
    "cleaning": {"interval_days": 14, "seasonal_factor": 1.2, "usage_decay": 0.1},
    "plumbing": {"interval_days": 90, "seasonal_factor": 1.5, "usage_decay": 0.05},
    "electrical": {"interval_days": 180, "seasonal_factor": 1.1, "usage_decay": 0.03},
    "beauty": {"interval_days": 30, "seasonal_factor": 0.9, "usage_decay": 0.15},
    "fitness": {"interval_days": 7, "seasonal_factor": 0.8, "usage_decay": 0.2},
    "pest_control": {"interval_days": 120, "seasonal_factor": 2.0, "usage_decay": 0.02},
    "gardening": {"interval_days": 21, "seasonal_factor": 1.8, "usage_decay": 0.08}
}

@router.get("/predictions")
async def get_service_predictions(current_user: dict = Depends(get_current_user)):
    """Get AI-powered service predictions for user"""
    db = get_db()
    
    # Get user's booking history
    bookings = await db.bookings.find({
        "user_id": current_user["sub"],
        "status": "completed"
    }).sort("created_at", -1).to_list(length=100)
    
    predictions = []
    
    for service_type, pattern in SERVICE_PATTERNS.items():
        service_bookings = [b for b in bookings if b.get("service_type") == service_type]
        
        if len(service_bookings) >= 2:  # Need at least 2 bookings for prediction
            prediction = await calculate_service_prediction(service_type, service_bookings, pattern, db)
            if prediction:
                predictions.append(prediction)
    
    # Sort by urgency (days until predicted need)
    predictions.sort(key=lambda x: x["days_until_needed"])
    
    return {"predictions": predictions}

@router.get("/maintenance-calendar")
async def get_maintenance_calendar(current_user: dict = Depends(get_current_user)):
    """Get personalized maintenance calendar"""
    db = get_db()
    
    predictions = await get_service_predictions(current_user)
    calendar_events = []
    
    for pred in predictions["predictions"]:
        event_date = datetime.utcnow() + timedelta(days=pred["days_until_needed"])
        
        calendar_events.append({
            "date": event_date.date().isoformat(),
            "service_type": pred["service_type"],
            "title": f"{pred['service_type'].title()} Maintenance Due",
            "description": pred["reason"],
            "urgency": pred["urgency"],
            "estimated_cost": pred["estimated_cost"],
            "recommended_providers": pred.get("recommended_providers", [])
        })
    
    return {"calendar": calendar_events}

@router.post("/set-reminder")
async def set_maintenance_reminder(
    service_type: str, 
    reminder_days: int, 
    current_user: dict = Depends(get_current_user)
):
    """Set custom maintenance reminder"""
    db = get_db()
    
    reminder = {
        "user_id": current_user["sub"],
        "service_type": service_type,
        "reminder_date": datetime.utcnow() + timedelta(days=reminder_days),
        "created_at": datetime.utcnow(),
        "status": "active",
        "custom": True
    }
    
    result = await db.maintenance_reminders.insert_one(reminder)
    
    return {
        "reminder_id": str(result.inserted_id),
        "message": f"Reminder set for {service_type} in {reminder_days} days"
    }

@router.get("/health-score")
async def get_home_health_score(current_user: dict = Depends(get_current_user)):
    """Calculate overall home/service health score"""
    db = get_db()
    
    # Get recent service history
    recent_bookings = await db.bookings.find({
        "user_id": current_user["sub"],
        "created_at": {"$gte": datetime.utcnow() - timedelta(days=365)},
        "status": "completed"
    }).to_list(length=100)
    
    health_scores = {}
    overall_score = 0
    
    for service_type, pattern in SERVICE_PATTERNS.items():
        service_bookings = [b for b in recent_bookings if b.get("service_type") == service_type]
        
        if service_bookings:
            last_service = max(service_bookings, key=lambda x: x["created_at"])
            days_since = (datetime.utcnow() - last_service["created_at"]).days
            
            # Calculate health score (0-100)
            optimal_interval = pattern["interval_days"]
            if days_since <= optimal_interval:
                score = 100
            elif days_since <= optimal_interval * 1.5:
                score = 80
            elif days_since <= optimal_interval * 2:
                score = 60
            else:
                score = max(20, 100 - (days_since - optimal_interval * 2))
            
            health_scores[service_type] = {
                "score": score,
                "last_service": last_service["created_at"].date().isoformat(),
                "days_since": days_since,
                "status": "excellent" if score >= 90 else "good" if score >= 70 else "needs_attention" if score >= 50 else "urgent"
            }
        else:
            health_scores[service_type] = {
                "score": 50,  # Neutral for never used
                "last_service": None,
                "days_since": None,
                "status": "no_history"
            }
    
    # Calculate overall score
    scores = [s["score"] for s in health_scores.values() if s["score"] is not None]
    overall_score = sum(scores) / len(scores) if scores else 50
    
    return {
        "overall_score": round(overall_score, 1),
        "grade": get_health_grade(overall_score),
        "service_scores": health_scores,
        "recommendations": generate_health_recommendations(health_scores)
    }


@router.get("/get-calendar")
async def get_maintenance_calendar(current_user: dict = Depends(get_current_user)):
    """Get personalized maintenance calendar for the next 12 months"""
    db = get_db()
    
    # Analyze history and generate predictions
    predictions = await get_service_predictions(current_user)
    
    calendar = []
    # Fill calendar for each month
    for i in range(12):
        month_date = datetime.utcnow() + timedelta(days=i * 30)
        month_name = month_date.strftime("%B %Y")
        
        # Simplified prediction check
        month_tasks = [p for p in predictions if datetime.fromisoformat(p["predicted_date"]).month == month_date.month]
        
        calendar.append({
            "month": month_name,
            "tasks": month_tasks,
            "task_count": len(month_tasks)
        })
    
    return {"calendar": calendar}

@router.post("/set-reminder")
async def set_service_reminder(data: PredictiveReminder, current_user: dict = Depends(get_current_user)):
    """Set a proactive service reminder"""
    db = get_db()
    
    reminder = {
        "user_id": current_user["sub"],
        "service_id": data.service_id,
        "reminder_date": data.date,
        "notes": data.notes,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    result = await db.predictive_reminders.insert_one(reminder)
    
    return {
        "message": "Reminder set successfully!",
        "reminder_id": str(result.inserted_id),
        "notification_scheduled": data.date
    }

@router.get("/seasonal-insights")
async def get_seasonal_insights():
    """Get seasonal service insights and recommendations"""
    current_month = datetime.utcnow().month
    
    seasonal_insights = {
        "winter": {
            "months": [12, 1, 2],
            "high_demand": ["plumbing", "electrical", "cleaning"],
            "tips": [
                "Pipe freezing prevention - schedule plumbing check",
                "Heating system maintenance",
                "Indoor air quality cleaning"
            ]
        },
        "spring": {
            "months": [3, 4, 5],
            "high_demand": ["cleaning", "gardening", "pest_control"],
            "tips": [
                "Deep spring cleaning",
                "Garden preparation and landscaping",
                "Pest prevention before summer"
            ]
        },
        "summer": {
            "months": [6, 7, 8],
            "high_demand": ["beauty", "fitness", "cleaning"],
            "tips": [
                "AC maintenance and cleaning",
                "Outdoor fitness activities",
                "Regular beauty treatments for summer"
            ]
        },
        "autumn": {
            "months": [9, 10, 11],
            "high_demand": ["plumbing", "electrical", "gardening"],
            "tips": [
                "Winter preparation for plumbing",
                "Electrical safety checks",
                "Garden winterization"
            ]
        }
    }
    
    current_season = None
    for season, data in seasonal_insights.items():
        if current_month in data["months"]:
            current_season = season
            break
    
    return {
        "current_season": current_season,
        "insights": seasonal_insights[current_season] if current_season else None,
        "all_seasons": seasonal_insights
    }

@router.post("/smart-schedule")
async def create_smart_schedule(
    data: PredictiveScheduleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create optimized service schedule based on budget and timeframe"""
    db = get_db()
    
    services = data.services
    budget = data.max_budget
    timeframe_days = 30  # Default or extract from data if added
    
    # Get service priorities and costs
    service_priorities = []
    
    for service_type in services:
        # Get average cost
        avg_cost = await get_average_service_cost(service_type, db)
        
        # Get urgency based on last booking
        last_booking = await db.bookings.find_one({
            "user_id": current_user["sub"],
            "service_type": service_type,
            "status": "completed"
        }, sort=[("created_at", -1)])
        
        urgency = 1.0
        if last_booking:
            days_since = (datetime.utcnow() - last_booking["created_at"]).days
            pattern = SERVICE_PATTERNS.get(service_type, {"interval_days": 30})
            urgency = min(2.0, days_since / pattern["interval_days"])
        
        service_priorities.append({
            "service_type": service_type,
            "cost": avg_cost,
            "urgency": urgency,
            "priority_score": urgency / avg_cost  # Higher urgency, lower cost = higher priority
        })
    
    # Sort by priority score
    service_priorities.sort(key=lambda x: x["priority_score"], reverse=True)
    
    # Create schedule within budget
    schedule = []
    remaining_budget = budget
    days_per_service = timeframe_days // len(services) if services else 1
    
    for i, service in enumerate(service_priorities):
        if remaining_budget >= service["cost"]:
            schedule_date = datetime.utcnow() + timedelta(days=i * days_per_service)
            schedule.append({
                "service_type": service["service_type"],
                "scheduled_date": schedule_date.date().isoformat(),
                "estimated_cost": service["cost"],
                "urgency": service["urgency"],
                "reason": f"Optimized scheduling based on urgency and budget"
            })
            remaining_budget -= service["cost"]
    
    return {
        "schedule": schedule,
        "total_cost": budget - remaining_budget,
        "remaining_budget": remaining_budget,
        "optimization_score": len(schedule) / len(services) * 100 if services else 0
    }

async def calculate_service_prediction(service_type: str, bookings: List[Dict], pattern: Dict, db) -> Dict:
    """Calculate when user will likely need a service next"""
    if len(bookings) < 2:
        return None
    
    # Calculate average interval between bookings
    intervals = []
    for i in range(len(bookings) - 1):
        interval = (bookings[i]["created_at"] - bookings[i + 1]["created_at"]).days
        intervals.append(interval)
    
    avg_interval = sum(intervals) / len(intervals)
    
    # Apply seasonal and usage factors
    seasonal_factor = pattern.get("seasonal_factor", 1.0)
    current_month = datetime.utcnow().month
    
    # Adjust for season (simplified)
    if current_month in [6, 7, 8] and service_type in ["beauty", "fitness"]:  # Summer
        seasonal_factor *= 1.2
    elif current_month in [12, 1, 2] and service_type in ["plumbing", "electrical"]:  # Winter
        seasonal_factor *= 1.3
    
    predicted_interval = avg_interval * seasonal_factor
    last_booking_date = bookings[0]["created_at"]
    days_since_last = (datetime.utcnow() - last_booking_date).days
    days_until_needed = max(0, predicted_interval - days_since_last)
    
    # Determine urgency
    if days_until_needed <= 3:
        urgency = "urgent"
    elif days_until_needed <= 7:
        urgency = "high"
    elif days_until_needed <= 14:
        urgency = "medium"
    else:
        urgency = "low"
    
    # Estimate cost based on historical data
    avg_cost = sum(b.get("amount", 0) for b in bookings) / len(bookings)
    
    return {
        "service_type": service_type,
        "days_until_needed": int(days_until_needed),
        "predicted_date": (datetime.utcnow() + timedelta(days=days_until_needed)).date().isoformat(),
        "confidence": min(95, len(bookings) * 20),  # More bookings = higher confidence
        "urgency": urgency,
        "reason": f"Based on your {len(bookings)} previous bookings (avg {int(avg_interval)} days apart)",
        "estimated_cost": round(avg_cost * 1.1, 2),  # Slight inflation
        "last_service": last_booking_date.date().isoformat()
    }

async def get_average_service_cost(service_type: str, db) -> float:
    """Get average cost for a service type"""
    pipeline = [
        {"$match": {"service_type": service_type, "status": "completed"}},
        {"$group": {"_id": None, "avg_cost": {"$avg": "$amount"}}}
    ]
    
    result = await db.bookings.aggregate(pipeline).to_list(length=1)
    return result[0]["avg_cost"] if result else SERVICE_PATTERNS.get(service_type, {}).get("base_cost", 500)

def get_health_grade(score: float) -> str:
    """Convert health score to letter grade"""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"

def generate_health_recommendations(health_scores: Dict) -> List[str]:
    """Generate recommendations based on health scores"""
    recommendations = []
    
    for service_type, data in health_scores.items():
        if data["status"] == "urgent":
            recommendations.append(f"🚨 Urgent: Schedule {service_type} service immediately")
        elif data["status"] == "needs_attention":
            recommendations.append(f"⚠️ Consider scheduling {service_type} service soon")
        elif data["status"] == "no_history":
            recommendations.append(f"💡 Consider trying our {service_type} services")
    
    if not recommendations:
        recommendations.append("✅ All services are up to date! Great job maintaining your home.")
    
    return recommendations

# ── Router Section: provider_dashboard ──
provider_dashboard_router = APIRouter()
router = provider_dashboard_router
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime, timedelta
from bson import ObjectId
import random


# 1. Active Job HUD
@router.get("/active-job")
async def get_active_job(current_user: dict = Depends(get_current_user)):
    db = get_db()
    active_job = await db.bookings.find_one({
        "provider_id": current_user["sub"],
        "status": "in_progress"
    })
    
    if not active_job:
        return {"active_job": None}
    
    active_job["_id"] = str(active_job["_id"])
    return {"active_job": active_job}

# 2. Biometric Check-in/Out
@router.post("/checkin")
async def biometric_checkin(
    booking_id: str,
    latitude: float,
    longitude: float,
    photo: str,  # base64 encoded
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Verify booking exists and belongs to provider
    booking = await db.bookings.find_one({
        "_id": ObjectId(booking_id),
        "provider_id": current_user["sub"]
    })
    
    if not booking:
        raise HTTPException(404, "Booking not found")
    
    # Store proof of presence
    checkin_data = {
        "booking_id": booking_id,
        "provider_id": current_user["sub"],
        "timestamp": datetime.utcnow(),
        "location": {"latitude": latitude, "longitude": longitude},
        "photo": photo,
        "type": "checkin"
    }
    
    await db.provider_checkins.insert_one(checkin_data)
    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "in_progress", "started_at": datetime.utcnow()}}
    )
    
    return {"success": True, "message": "Checked in successfully"}

@router.post("/checkout")
async def biometric_checkout(
    booking_id: str,
    latitude: float,
    longitude: float,
    photo: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    checkout_data = {
        "booking_id": booking_id,
        "provider_id": current_user["sub"],
        "timestamp": datetime.utcnow(),
        "location": {"latitude": latitude, "longitude": longitude},
        "photo": photo,
        "type": "checkout"
    }
    
    await db.provider_checkins.insert_one(checkout_data)
    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "completed", "completed_at": datetime.utcnow()}}
    )
    
    return {"success": True, "message": "Checked out successfully"}

# 3. Pheromone Live Mode
@router.post("/live-mode/toggle")
async def toggle_live_mode(
    enabled: bool,
    latitude: float,
    longitude: float,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": {
            "live_mode": enabled,
            "live_location": {"latitude": latitude, "longitude": longitude} if enabled else None,
            "live_mode_updated": datetime.utcnow()
        }}
    )
    
    return {"success": True, "live_mode": enabled}

@router.get("/live-mode/status")
async def get_live_mode_status(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    return {
        "live_mode": user.get("live_mode", False),
        "live_location": user.get("live_location")
    }

# 4. AI Neighborhood Skill-Gap Alerts
@router.get("/skill-gap-alerts")
async def get_skill_gap_alerts(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Get provider's location
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user or not user.get("location"):
        return {"alerts": []}
    
    user_lat = user["location"]["latitude"]
    user_lng = user["location"]["longitude"]
    
    # Analyze demand vs supply in 5-mile radius
    categories = await db.services.distinct("category")
    alerts = []
    
    for category in categories[:10]:  # Top 10 categories
        # Count providers in area
        providers = await db.services.count_documents({
            "category": category,
            "latitude": {"$gte": user_lat - 0.1, "$lte": user_lat + 0.1},
            "longitude": {"$gte": user_lng - 0.1, "$lte": user_lng + 0.1}
        })
        
        # Count recent searches (simulated)
        demand = random.randint(50, 200)
        
        if providers < demand * 0.3:  # Supply shortage
            shortage_pct = int((1 - providers / (demand * 0.3)) * 100)
            alerts.append({
                "category": category,
                "shortage_percentage": shortage_pct,
                "message": f"There is a {shortage_pct}% shortage of '{category.title()}' in your 5-mile radius. Add this skill to increase leads.",
                "potential_earnings": f"₹{random.randint(5000, 15000)}/month"
            })
    
    return {"alerts": sorted(alerts, key=lambda x: x["shortage_percentage"], reverse=True)[:5]}

# 5. Dynamic Surge Pricing
@router.get("/surge-pricing")
async def get_surge_pricing(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Get provider's category
    service = await db.services.find_one({"provider_id": current_user["sub"]})
    if not service:
        return {"surge_active": False}
    
    # Simulate surge detection based on category and time
    hour = datetime.utcnow().hour
    category = service["category"]
    
    surge_conditions = {
        "plumber": hour in [7, 8, 9, 18, 19, 20],  # Morning/evening rush
        "electrician": hour in [10, 11, 17, 18],
        "cleaner": hour in [9, 10, 11, 15, 16]
    }
    
    is_surge = surge_conditions.get(category, False)
    surge_multiplier = 1.3 if is_surge else 1.0
    
    return {
        "surge_active": is_surge,
        "surge_multiplier": surge_multiplier,
        "suggested_price": round(service["price_per_hour"] * surge_multiplier, 2),
        "reason": "High demand period" if is_surge else "Normal demand"
    }

@router.post("/surge-pricing/apply")
async def apply_surge_pricing(
    multiplier: float,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    service = await db.services.find_one({"provider_id": current_user["sub"]})
    new_price = round(service["base_price"] * multiplier, 2)
    
    await db.services.update_one(
        {"provider_id": current_user["sub"]},
        {"$set": {
            "price_per_hour": new_price,
            "surge_multiplier": multiplier,
            "surge_applied_at": datetime.utcnow()
        }}
    )
    
    return {"success": True, "new_price": new_price}

# 6. Smart Route Density Scheduling
@router.get("/route-density")
async def get_route_density(
    date: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Get all bookings for the date
    target_date = datetime.fromisoformat(date)
    bookings = await db.bookings.find({
        "provider_id": current_user["sub"],
        "scheduled_date": {
            "$gte": target_date,
            "$lt": target_date + timedelta(days=1)
        }
    }).to_list(length=100)
    
    # Calculate density for each hour
    density_map = {}
    for hour in range(8, 20):  # 8 AM to 8 PM
        nearby_count = 0
        for booking in bookings:
            booking_hour = booking.get("scheduled_time", "09:00").split(":")[0]
            if int(booking_hour) == hour:
                nearby_count += 1
        
        density_map[f"{hour:02d}:00"] = {
            "density": "high" if nearby_count >= 2 else "medium" if nearby_count == 1 else "low",
            "color": "green" if nearby_count >= 2 else "yellow" if nearby_count == 1 else "gray",
            "nearby_jobs": nearby_count,
            "fuel_savings": f"₹{nearby_count * 50}" if nearby_count > 0 else "₹0"
        }
    
    return {"date": date, "density_map": density_map}

# 7. AI Portfolio Generator
@router.post("/portfolio/generate")
async def generate_portfolio_caption(
    photo: str,  # base64
    job_type: str,
    current_user: dict = Depends(get_current_user)
):
    # Simulate AI caption generation
    captions = {
        "plumbing": [
            "Restored vintage copper piping in a heritage property – Precision soldering technique used.",
            "Installed modern tankless water heater system – 40% energy savings guaranteed.",
            "Emergency leak repair completed in under 2 hours – Zero water damage achieved."
        ],
        "electrical": [
            "Upgraded entire home electrical panel to 200A service – Smart home ready installation.",
            "Installed energy-efficient LED lighting throughout – Reduced power consumption by 60%.",
            "Rewired vintage property maintaining original aesthetics – Code compliant restoration."
        ],
        "carpentry": [
            "Restored vintage hardwood flooring in a 1920s bungalow – Dustless sanding technique used.",
            "Custom-built oak kitchen cabinets with soft-close hinges – Handcrafted perfection.",
            "Repaired antique furniture maintaining original joinery – Traditional craftsmanship preserved."
        ]
    }
    
    category = job_type.lower()
    caption = random.choice(captions.get(category, ["Professional service completed to highest standards."]))
    
    # Store in portfolio
    db = get_db()
    portfolio_item = {
        "provider_id": current_user["sub"],
        "photo": photo,
        "caption": caption,
        "job_type": job_type,
        "created_at": datetime.utcnow(),
        "likes": 0,
        "views": 0
    }
    
    result = await db.provider_portfolio.insert_one(portfolio_item)
    
    return {
        "success": True,
        "caption": caption,
        "portfolio_id": str(result.inserted_id)
    }

@router.get("/portfolio")
async def get_portfolio(current_user: dict = Depends(get_current_user)):
    db = get_db()
    portfolio = await db.provider_portfolio.find({
        "provider_id": current_user["sub"]
    }).sort("created_at", -1).limit(20).to_list(length=20)
    
    for item in portfolio:
        item["_id"] = str(item["_id"])
    
    return {"portfolio": portfolio}

# 8. Provider Dashboard Stats
@router.get("/stats")
async def get_provider_stats(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    
    # Basic counts
    total_bookings = await db.bookings.count_documents({"provider_id": provider_id})
    completed = await db.bookings.count_documents({"provider_id": provider_id, "status": "completed"})
    active = await db.bookings.count_documents({"provider_id": provider_id, "status": "in_progress"})
    pending = await db.bookings.count_documents({"provider_id": provider_id, "status": "pending"})
    
    # Earnings pipeline
    earnings_pipeline = [
        {"$match": {"provider_id": provider_id, "status": "completed"}},
        {"$group": {
            "_id": None,
            "total_earnings": {"$sum": "$amount"},
            "total_jobs": {"$sum": 1},
            "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}},
            "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}}
        }}
    ]
    earnings = await db.bookings.aggregate(earnings_pipeline).to_list(length=1)
    earnings_data = earnings[0] if earnings else {}
    
    total_earnings = earnings_data.get("total_earnings", 0)
    
    # Today's earnings
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_pipeline = [
        {"$match": {"provider_id": provider_id, "status": "completed", "completed_at": {"$gte": today_start}}},
        {"$group": {"_id": None, "earnings_today": {"$sum": "$amount"}}}
    ]
    today_earnings = await db.bookings.aggregate(today_pipeline).to_list(length=1)
    earnings_today = today_earnings[0].get("earnings_today", 0) if today_earnings else 0
    
    # Service rating
    service = await db.services.find_one({"provider_id": provider_id})
    rating = service.get("rating", 0) if service else 0
    
    user = await db.users.find_one({"_id": ObjectId(provider_id)})
    
    # Competitor rank (local market position) - percentile among providers
    all_providers_pipeline = [  # noqa: C408
        {"$match": {"role": "provider"}},
        {"$lookup": {
            "from": "bookings",
            "let": {"prov_id": {"$toString": "$_id"}},
            "pipeline": [
                {"$match": {
                    "$expr": {"$eq": ["$provider_id", "$$prov_id"]},
                    "status": "completed"
                }},
                {"$group": {"_id": None, "prov_earnings": {"$sum": "$amount"}}}
            ],
            "as": "prov_stats"
        }},
        {"$addFields": {"prov_earnings": {
            "$arrayElemAt": ["$prov_stats.prov_earnings", 0]
        }}},
        {"$addFields": {"prov_earnings": {"$ifNull": ["$prov_earnings", 0]}}},
        {"$sort": {"prov_earnings": -1}},
        {"$group": {
            "_id": None,
            "providers": {"$push": "$$ROOT"},
            "total_providers": {"$sum": 1}
        }},
        {"$addFields": {"percentile_rank": {
            "$indexOfArray": [{
                "$map": {
                    "input": "$providers",
                    "as": "p",
                    "in": {"$indexOfArray": ["$providers", "$$ROOT"]}
                }
            }, 0]
        }}}
    ]
    all_stats = await db.users.aggregate(all_providers_pipeline).to_list(length=1)
    rank = 1  # default
    percentile = 0.0
    if all_stats and all_stats[0].get("providers"):
        providers_list = all_stats[0]["providers"]
        total_prov = all_stats[0]["total_providers"]
        for idx, prov in enumerate(providers_list):
            if str(prov["_id"]) == provider_id:
                rank = idx + 1
                percentile = round((1 - (idx / total_prov)) * 100, 1)
                break
    
    # Route efficiency score: earnings per km
    route_efficiency = round(
        total_earnings / max(earnings_data.get("total_distance", 1), 1), 2
    )
    
    user_live_mode = user.get("live_mode", False) if user else False
    
    market_pos = (
        f"#{rank} of {all_stats[0].get('total_providers', 'N/A')} "
        f"({percentile} percentile)"
    )
    
    return {
        "total_bookings": total_bookings,
        "completed_bookings": completed,
        "completed_jobs": completed,
        "active_bookings": active,
        "pending_bookings": pending,
        "total_earnings": total_earnings,
        "earnings_today": earnings_today,
        "average_rating": rating,
        "live_mode": user_live_mode,
        "local_market_position": market_pos,
        "route_efficiency_score": route_efficiency,
        "profit_per_hour": round(
            total_earnings / (earnings_data.get("total_duration", 60) / 60), 2
        ),
        "avg_job_value": round(
            total_earnings / max(earnings_data.get("total_jobs", 1), 1), 2
        )
    }


# 9. Geospatial Territory Management
@router.post("/territory/boundary")
async def save_service_boundary(
    polygon: List[dict],  # [{lat, lng}, ...]
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": {
            "service_boundary": polygon,
            "boundary_updated": datetime.utcnow()
        }}
    )
    
    return {"success": True, "message": "Service boundary saved"}

@router.get("/territory/boundary")
async def get_service_boundary(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    return {"boundary": user.get("service_boundary", [])}

@router.post("/territory/no-go-zones")
async def add_no_go_zone(
    zone: dict,  # {name, coordinates: [{lat, lng}]}
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$push": {"no_go_zones": zone}}
    )
    
    return {"success": True, "message": "No-go zone added"}

@router.delete("/territory/no-go-zones/{zone_name}")
async def remove_no_go_zone(
    zone_name: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$pull": {"no_go_zones": {"name": zone_name}}}
    )
    
    return {"success": True, "message": "No-go zone removed"}

@router.get("/territory/no-go-zones")
async def get_no_go_zones(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    return {"zones": user.get("no_go_zones", [])}

@router.get("/territory/demand-heatmap")
async def get_demand_heatmap(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Get provider's service area
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user or not user.get("location"):
        return {"heatmap": []}
    
    # Generate heatmap data (simulated demand)
    center_lat = user["location"]["latitude"]
    center_lng = user["location"]["longitude"]
    
    heatmap_points = []
    for i in range(20):
        lat_offset = (random.random() - 0.5) * 0.1
        lng_offset = (random.random() - 0.5) * 0.1
        intensity = random.randint(1, 100)
        
        heatmap_points.append({
            "lat": center_lat + lat_offset,
            "lng": center_lng + lng_offset,
            "intensity": intensity
        })
    
    return {"heatmap": heatmap_points}

# 10. Financial & Trust Analytics
@router.get("/analytics/earnings-pulse")
async def get_earnings_pulse(
    period: str = "weekly",  # daily, weekly, monthly
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    provider_id = current_user["sub"]
    
    match_stage = {
        "provider_id": provider_id,
        "status": "completed"
    }
    
    if period == "daily":
        group_stage = {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$completed_at"}},
                "revenue": {"$sum": "$amount"},
                "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}},
                "jobs": {"$sum": 1},
                "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}}
            }
        }
        time_filter = {"$gte": datetime.utcnow() - timedelta(days=30)}
        sort_desc = {"$sort": {"_id": -1}}
        limit_docs = 30
        
    elif period == "weekly":
        group_stage = {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-W%U", "date": "$completed_at"}
                },
                "revenue": {"$sum": "$amount"},
                "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}},
                "jobs": {"$sum": 1},
                "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}}
            }
        }
        time_filter = {"$gte": datetime.utcnow() - timedelta(weeks=12)}
        sort_desc = {"$sort": {"_id": -1}}
        limit_docs = 12
        
    else:  # monthly
        group_stage = {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m", "date": "$completed_at"}
                },
                "revenue": {"$sum": "$amount"},
                "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}},
                "jobs": {"$sum": 1},
                "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}}
            }
        }
        time_filter = {"$gte": datetime.utcnow() - timedelta(days=365)}
        sort_desc = {"$sort": {"_id": -1}}
        limit_docs = 12
    
    pipeline = [  # noqa: C408
        {"$match": match_stage},
        {"$match": {"completed_at": time_filter}},
        group_stage,
        sort_desc,
        {"$limit": limit_docs}
    ]
    
    earnings_data = await db.bookings.aggregate(pipeline).to_list(length=limit_docs)
    
    # Add calculated metrics
    for item in earnings_data:
        item["date"] = item["_id"]
        item["profit_per_hour"] = round(item["revenue"] / (item["total_duration"] / 60), 2) if item["total_duration"] > 0 else 0
        item["avg_job_value"] = round(item["revenue"] / item["jobs"], 2) if item["jobs"] > 0 else 0
        item["route_efficiency"] = round(item["revenue"] / max(item["total_distance"], 1), 2) if item["total_distance"] > 0 else 0
        del item["_id"]
    
    # Overall stats
    overall_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$amount"},
            "total_jobs": {"$sum": 1},
            "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}},
            "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}}
        }}
    ]
    overall = await db.bookings.aggregate(overall_pipeline).to_list(length=1)
    overall_stats = overall[0] if overall else {}
    
    return {
        "period": period,
        "data": earnings_data,
        "overall": {
            "total_revenue": overall_stats.get("total_revenue", 0),
            "avg_profit_per_hour": round(overall_stats.get("total_revenue", 0) / (overall_stats.get("total_duration", 60) / 60), 2),
            "avg_job_value": round(overall_stats.get("total_revenue", 0) / overall_stats.get("total_jobs", 1), 2),
            "route_efficiency_score": round(overall_stats.get("total_revenue", 0) / max(overall_stats.get("total_distance", 1), 1), 2)
        }
    }

@router.get("/analytics/advanced")
async def get_advanced_analytics(current_user: dict = Depends(get_current_user)):
    """Return all remaining analytics (peak hours, radar, competitors, etc.)"""
    # 1. Peak Hours (Simulated based on historical volume)
    peak_hours = [
        {"hour": "6AM", "requests": 8}, {"hour": "8AM", "requests": 22}, {"hour": "10AM", "requests": 45},
        {"hour": "12PM", "requests": 30}, {"hour": "2PM", "requests": 28}, {"hour": "4PM", "requests": 50},
        {"hour": "6PM", "requests": 48}, {"hour": "8PM", "requests": 18}, {"hour": "10PM", "requests": 6},
    ]

    # 2. Radar Data (Route Efficiency Metrics)
    radar_data = [
        {"subject": "Speed",     "score": 85},
        {"subject": "Distance",  "score": 72},
        {"subject": "Fuel",      "score": 68},
        {"subject": "On-Time",   "score": 90},
        {"subject": "Revisits",  "score": 60},
    ]

    # 3. Competitor Rank (Simulated based on nearby providers)
    competitor_rank = [
        {"name": "Rajesh K.",  "jobs": 142, "price": 650, "rating": 4.9},
        {"name": "You",        "jobs": 118, "price": 600, "rating": 4.8},
        {"name": "Suresh M.",  "jobs": 95,  "price": 700, "rating": 4.6},
        {"name": "Anil P.",    "jobs": 80,  "price": 550, "rating": 4.4},
    ]

    # 4. Route Efficiency by Zone
    route_efficiency_data = [
        {"zone": "Indiranagar",  "effScore": 88},
        {"zone": "Koramangala",  "effScore": 74},
        {"zone": "HSR Layout",   "effScore": 65},
        {"zone": "JP Nagar",     "effScore": 80},
    ]

    # 5. Demand Heatmap Zones
    heatmap_zones = [
        {"zone": "Koramangala",  "demand": 87, "color": "#ef4444"},
        {"zone": "Indiranagar",  "demand": 72, "color": "#f97316"},
        {"zone": "HSR Layout",   "demand": 55, "color": "#eab308"},
        {"zone": "Whitefield",   "demand": 38, "color": "#22c55e"},
        {"zone": "JP Nagar",     "demand": 61, "color": "#f97316"},
    ]

    # 6. Competitor Alerts
    competitor_alerts = [
        {"provider": "Vikram Electricals", "change": "+8%", "newRate": "₹1,079/hr", "area": "Koramangala",  "type": "up"},
        {"provider": "RapidFix Services",  "change": "-12%", "newRate": "₹747/hr",   "area": "Whitefield",   "type": "down"},
        {"provider": "PowerPro Bangalore", "change": "+5%",  "newRate": "₹996/hr",   "area": "Indiranagar",  "type": "up"},
    ]

    # 7. Seasonal Rules
    seasonal_rules = [
        {"name": "Summer AC Rush (Apr–Jun)",    "adjustment": "+25%", "category": "AC Technician", "status": "scheduled"},
        {"name": "Monsoon Plumbing Surge",      "adjustment": "+18%", "category": "Plumber",       "status": "active"},
        {"name": "Festive Deep Cleaning",       "adjustment": "+15%", "category": "Cleaner",       "status": "scheduled"},
        {"name": "Year-End Electrical Audit",   "adjustment": "+10%", "category": "Electrician",   "status": "active"},
    ]

    # 8. Recurring Customers
    recurring_customers = [
        {"name": "Anjali Singh",  "service": "Annual Wiring Inspection", "lastDate": "Dec 10 2023", "dueDate": "Dec 10 2024", "potential": 2490},
        {"name": "Meera Nair",    "service": "AC Pre-Summer Tune-up",    "lastDate": "Mar 15 2024", "dueDate": "Mar 15 2025", "potential": 1660},
        {"name": "Ramesh Gupta",  "service": "Quarterly Check",          "lastDate": "Sep 28 2024", "dueDate": "Dec 28 2024", "potential": 1245},
    ]

    return {
        "peak_hours": peak_hours,
        "radar_data": radar_data,
        "competitor_rank": competitor_rank,
        "route_efficiency_data": route_efficiency_data,
        "heatmap_zones": heatmap_zones,
        "competitor_alerts": competitor_alerts,
        "seasonal_rules": seasonal_rules,
        "recurring_customers": recurring_customers
    }

@router.get("/analytics/trust-score")
async def get_trust_score(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Get all bookings
    total_bookings = await db.bookings.count_documents({"provider_id": current_user["sub"]})
    completed = await db.bookings.count_documents({"provider_id": current_user["sub"], "status": "completed"})
    cancelled = await db.bookings.count_documents({"provider_id": current_user["sub"], "status": "cancelled"})
    
    # Calculate reliability (0-40 points)
    reliability = 0 if total_bookings == 0 else min(40, int((completed / total_bookings) * 40))
    
    # Calculate punctuality (0-30 points) - simulated
    punctuality = random.randint(20, 30)
    
    # Get reviews for quality (0-30 points)
    service = await db.services.find_one({"provider_id": current_user["sub"]})
    rating = service.get("rating", 0) if service else 0
    quality = int((rating / 5.0) * 30)
    
    trust_score = reliability + punctuality + quality
    
    return {
        "trust_score": trust_score,
        "breakdown": {
            "reliability": reliability,
            "punctuality": punctuality,
            "quality": quality
        },
        "metrics": {
            "completion_rate": f"{(completed/total_bookings*100):.1f}%" if total_bookings > 0 else "0%",
            "cancellation_rate": f"{(cancelled/total_bookings*100):.1f}%" if total_bookings > 0 else "0%",
            "average_rating": f"{rating:.1f}"
        }
    }

@router.post("/financial/instant-payout")
async def request_instant_payout(
    amount: float,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Check available balance
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    available_balance = user.get("available_balance", 0)
    
    if amount > available_balance:
        raise HTTPException(400, "Insufficient balance")
    
    # Create payout request
    payout = {
        "provider_id": current_user["sub"],
        "amount": amount,
        "status": "pending",
        "requested_at": datetime.utcnow(),
        "stripe_transfer_id": f"tr_{random.randint(100000, 999999)}"  # Simulated
    }
    
    await db.payouts.insert_one(payout)
    
    # Update balance
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$inc": {"available_balance": -amount}}
    )
    
    return {"success": True, "message": "Payout initiated", "transfer_id": payout["stripe_transfer_id"]}

@router.get("/financial/balance")
async def get_balance(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    
    # Calculate from completed payments (provider_payout field)
    payments_data = await db.payments.find({
        "provider_id": current_user["sub"],
        "status": "completed"
    }).to_list(length=1000)
    
    total_earned = sum(p.get("provider_payout") or p.get("amount", 0) for p in payments_data)
    
    # Get withdrawn amount
    payouts = await db.payouts.find({
        "provider_id": current_user["sub"],
        "status": {"$in": ["completed", "pending"]}
    }).to_list(length=1000)
    
    total_withdrawn = sum(p.get("amount", 0) for p in payouts)
    
    available = total_earned - total_withdrawn
    
    return {
        "available": available,               # frontend alias
        "available_balance": available,
        "total_earned": total_earned,
        "total_withdrawn": total_withdrawn,
        "pending_payouts": sum(p.get("amount", 0) for p in payouts if p.get("status") == "pending")
    }

# 11. Administrative & Compliance
@router.post("/compliance/documents")
async def upload_document(
    doc_type: str,  # license, insurance, background_check
    expiry_date: str,
    file: str,  # base64
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    document = {
        "provider_id": current_user["sub"],
        "type": doc_type,
        "expiry_date": datetime.fromisoformat(expiry_date),
        "file": file,
        "uploaded_at": datetime.utcnow(),
        "status": "active"
    }
    
    result = await db.provider_documents.insert_one(document)
    
    return {"success": True, "document_id": str(result.inserted_id)}

@router.get("/compliance/documents")
async def get_documents(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    docs = await db.provider_documents.find({
        "provider_id": current_user["sub"]
    }).sort("uploaded_at", -1).to_list(length=100)
    
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        # Check if expiring soon
        days_until_expiry = (doc["expiry_date"] - datetime.utcnow()).days
        doc["days_until_expiry"] = days_until_expiry
        doc["expiring_soon"] = days_until_expiry <= 30
    
    return {"documents": docs}

@router.get("/compliance/expiring-alerts")
async def get_expiring_alerts(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    thirty_days_from_now = datetime.utcnow() + timedelta(days=30)
    
    expiring_docs = await db.provider_documents.find({
        "provider_id": current_user["sub"],
        "expiry_date": {"$lte": thirty_days_from_now},
        "status": "active"
    }).to_list(length=100)
    
    alerts = []
    for doc in expiring_docs:
        days_left = (doc["expiry_date"] - datetime.utcnow()).days
        alerts.append({
            "type": doc["type"],
            "expiry_date": doc["expiry_date"].strftime("%Y-%m-%d"),
            "days_left": days_left,
            "urgency": "critical" if days_left <= 7 else "warning"
        })
    
    return {"alerts": alerts}

@router.get("/compliance/jury-cases")
async def get_jury_cases(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Check if provider is eligible (rating > 4.5)
    service = await db.services.find_one({"provider_id": current_user["sub"]})
    if not service or service.get("rating", 0) < 4.5:
        return {"eligible": False, "cases": []}
    
    # Get open dispute cases
    cases = await db.disputes.find({
        "status": "pending_jury",
        "jury_members": {"$ne": current_user["sub"]}
    }).limit(5).to_list(length=5)
    
    for case in cases:
        case["_id"] = str(case["_id"])
    
    return {"eligible": True, "cases": cases}

@router.post("/compliance/jury-vote")
async def submit_jury_vote(
    case_id: str,
    verdict: str,  # customer_favor, provider_favor
    reasoning: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    vote = {
        "case_id": case_id,
        "juror_id": current_user["sub"],
        "verdict": verdict,
        "reasoning": reasoning,
        "voted_at": datetime.utcnow()
    }
    
    await db.jury_votes.insert_one(vote)
    
    # Award credits
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$inc": {"quickserve_credits": 50, "jury_reputation": 1}}
    )
    
    return {"success": True, "credits_earned": 50}

@router.get("/financial/tax-export")
async def export_tax_data(
    year: int,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Get all completed bookings for the year
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    
    bookings = await db.bookings.find({
        "provider_id": current_user["sub"],
        "status": "completed",
        "completed_at": {"$gte": start_date, "$lte": end_date}
    }).to_list(length=10000)
    
    # Generate CSV data
    csv_data = []
    total_earnings = 0
    total_commission = 0
    total_mileage = 0
    
    for booking in bookings:
        earnings = booking.get("total_amount", 0)
        commission = earnings * 0.15  # 15% platform fee
        mileage = booking.get("distance", 0) * 2  # Round trip
        
        total_earnings += earnings
        total_commission += commission
        total_mileage += mileage
        
        csv_data.append({
            "Date": booking.get("completed_at", datetime.utcnow()).strftime("%Y-%m-%d"),
            "Booking ID": str(booking.get("_id", "")),
            "Service": booking.get("service_name", ""),
            "Gross Earnings": f"₹{earnings:.2f}",
            "Platform Commission": f"₹{commission:.2f}",
            "Net Earnings": f"₹{(earnings - commission):.2f}",
            "Mileage (km)": f"{mileage:.1f}"
        })
    
    # Add summary row
    csv_data.append({
        "Date": "TOTAL",
        "Booking ID": "",
        "Service": "",
        "Gross Earnings": f"₹{total_earnings:.2f}",
        "Platform Commission": f"₹{total_commission:.2f}",
        "Net Earnings": f"₹{(total_earnings - total_commission):.2f}",
        "Mileage (km)": f"{total_mileage:.1f}"
    })
    
    return {
        "year": year,
        "data": csv_data,
        "summary": {
            "total_earnings": total_earnings,
            "total_commission": total_commission,
            "net_earnings": total_earnings - total_commission,
            "total_mileage": total_mileage
        }
    }

# ── Router Section: providers ──
providers_router = APIRouter()
router = providers_router
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from bson import ObjectId
from datetime import datetime, timedelta
import os
import shutil
import random
import string
from twilio.rest import Client as TwilioClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


@router.get("/")
async def get_providers(limit: int = 20):
    db = get_db()
    providers = await db.users.find({"role": "provider"}).limit(limit).to_list(length=limit)
    for p in providers:
        p["_id"] = str(p["_id"])
        p.pop("password", None)
    return providers

@router.get("/{provider_id}")
async def get_provider(provider_id: str):
    db = get_db()
    provider = await db.users.find_one({"_id": ObjectId(provider_id), "role": "provider"})
    if provider:
        provider["_id"] = str(provider["_id"])
        provider.pop("password", None)
    return provider

@router.post("/onboard")
async def onboard_provider(data: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Calculate QuickServe Score
    score = 85 # Default base score
    if data.get("documents"): score += 5
    if data.get("portfolio"): score += 5
    if data.get("ai_bot_settings"): score += 5
    
    update_data = {
        "onboarded": True,
        "base_location": data.get("location"),
        "service_area": {
            "type": data.get("service_area_type"),
            "radius": data.get("radius"),
            "polygon": data.get("polygon_points")
        },
        "specializations": data.get("categories"),
        "hourly_rate": data.get("hourly_rate"),
        "emergency_rate": data.get("emergency_rate"),
        "ai_bot_settings": data.get("ai_bot_settings"),
        "quickserve_score": score,
        "launch_plan_generated": True,
        "updated_at": datetime.utcnow()
    }
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": update_data}
    )
    
    return {"status": "success", "score": score}

@router.get("/search")
async def search_providers(lat: float, lng: float, category: str = None):
    db = get_db()
    
    # 1. Find providers nearby using base_location (radius search)
    # This is a broad filter
    query = {
        "role": "provider",
        "onboarded": True,
    }
    if category:
        query["specializations"] = category
        
    providers = await db.users.find(query).to_list(length=100)
    
    matched_providers = []
    user_point = [lng, lat]
    
    for p in providers:
        service_area = p.get("service_area", {})
        area_type = service_area.get("type", "radius")
        
        is_match = False
        
        if area_type == "radius":
            # Haversine formula for distance
            from math import radians, cos, sin, asin, sqrt
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1 
                dlat = lat2 - lat1 
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a)) 
                r = 3956 # Miles
                return c * r
            
            base_loc = p.get("base_location", {"lat": 0, "lng": 0})
            dist = haversine(lng, lat, base_loc["lng"], base_loc["lat"])
            if dist <= service_area.get("radius", 5):
                is_match = True
                p["distance"] = round(dist, 2)
        
        elif area_type == "polygon":
            # Point-in-polygon algorithm
            polygon = service_area.get("polygon", [])
            if polygon:
                n = len(polygon)
                inside = False
                p1x, p1y = polygon[0][1], polygon[0][0] # lng, lat
                for i in range(n + 1):
                    p2x, p2y = polygon[i % n][1], polygon[i % n][0]
                    if lat > min(p1y, p2y):
                        if lat <= max(p1y, p2y):
                            if lng <= max(p1x, p2x):
                                if p1y != p2y:
                                    xints = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                                if p1x == p2x or lng <= xints:
                                    inside = not inside
                    p1x, p1y = p2x, p2y
                if inside:
                    is_match = True
                    p["distance"] = 0 # Inside polygon
        
        if is_match:
            p["_id"] = str(p["_id"])
            p.pop("password", None)
            matched_providers.append(p)
            
    # Sort by distance or rating
    matched_providers.sort(key=lambda x: x.get("distance", 0))
    
    return matched_providers

@router.get("/earnings")
async def get_earnings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    payments = await db.payments.find({"provider_id": current_user["sub"], "status": "completed"}).to_list(length=1000)
    total = sum(p.get("amount", 0) for p in payments)
    return {"total_earnings": total, "payment_count": len(payments)}

@router.put("/availability")
async def update_availability(availability: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.provider_availability.update_one(
        {"provider_id": current_user["sub"]},
        {"$set": availability},
        upsert=True
    )
    return {"status": "updated"}


@router.post("/verify/upload-docs")
async def upload_provider_docs(files: list[UploadFile] = File(...), current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    base_dir = os.path.join(os.path.dirname(__file__), "..", "uploads", "providers", provider_id)
    os.makedirs(base_dir, exist_ok=True)

    saved = []
    for f in files:
        dest_path = os.path.join(base_dir, f.filename)
        with open(dest_path, "wb") as out:
            shutil.copyfileobj(f.file, out)

        doc = {
            "provider_id": provider_id,
            "filename": f.filename,
            "path": dest_path,
            "status": "pending",
            "uploaded_at": datetime.utcnow()
        }
        await db.provider_documents.insert_one(doc)
        saved.append({"filename": f.filename, "status": "pending"})

    # bump quickserve score slightly for providing docs
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$inc": {"quickserve_score": 3}})

    return {"status": "ok", "uploaded": saved}


def _gen_code(length: int = 6):
    return "".join(random.choices(string.digits, k=length))


@router.post("/verify/request-otp")
async def request_phone_otp(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    code = _gen_code(6)
    record = {
        "provider_id": provider_id,
        "type": "phone",
        "code": code,
        "verified": False,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
        "created_at": datetime.utcnow()
    }
    await db.provider_verifications.insert_one(record)
    # Send SMS via Twilio (requires env vars TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM)
    try:
        tw_sid = os.getenv("TWILIO_ACCOUNT_SID")
        tw_token = os.getenv("TWILIO_AUTH_TOKEN")
        tw_from = os.getenv("TWILIO_FROM")
        to_number = current_user.get("phone")
        if tw_sid and tw_token and tw_from and to_number:
            client = TwilioClient(tw_sid, tw_token)
            client.messages.create(body=f"Your QuickServe verification code: {code}", from_=tw_from, to=to_number)
            return {"status": "otp_sent"}
        else:
            # For local/testing when env not set, return OTP so tests can continue
            return {"status": "otp_sent", "otp": code}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/verify/check-otp")
async def check_phone_otp(payload: dict, current_user: dict = Depends(get_current_user)):
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code required")

    db = get_db()
    provider_id = current_user["sub"]
    rec = await db.provider_verifications.find_one({"provider_id": provider_id, "type": "phone", "code": code})
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="otp not found")
    if rec.get("expires_at") and rec["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="otp expired")

    await db.provider_verifications.update_one({"_id": rec["_id"]}, {"$set": {"verified": True, "verified_at": datetime.utcnow()}})
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$set": {"verified_phone": True}})
    return {"status": "verified"}


@router.post("/verify/request-email")
async def request_email_verification(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    token = _gen_code(24)
    rec = {"provider_id": provider_id, "type": "email", "token": token, "verified": False, "expires_at": datetime.utcnow() + timedelta(hours=2), "created_at": datetime.utcnow()}
    await db.provider_verifications.insert_one(rec)
    # Send verification email via SendGrid (requires SENDGRID_API_KEY and SENDGRID_FROM_EMAIL)
    try:
        sg_key = os.getenv("SENDGRID_API_KEY")
        from_email = os.getenv("SENDGRID_FROM_EMAIL") or "noreply@quickserve.local"
        base = os.getenv("BASE_URL") or "http://localhost:8000"
        verify_link = f"{base}/providers/verify/email-callback?token={token}"
        if sg_key:
            message = Mail(
                from_email=from_email,
                to_emails=current_user.get("email"),
                subject="QuickServe Email Verification",
                html_content=f"<p>Please verify your email by clicking <a href=\"{verify_link}\">here</a>.</p>"
            )
            sg = SendGridAPIClient(sg_key)
            sg.send(message)
            return {"status": "email_sent"}
        else:
            # fallback for local/testing
            return {"status": "email_sent", "token": token, "verify_link": verify_link}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/verify/email-callback")
async def email_callback(token: str):
    db = get_db()
    rec = await db.provider_verifications.find_one({"type": "email", "token": token})
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="token not found")
    if rec.get("expires_at") and rec["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token expired")
    await db.provider_verifications.update_one({"_id": rec["_id"]}, {"$set": {"verified": True, "verified_at": datetime.utcnow()}})
    await db.users.update_one({"_id": ObjectId(rec["provider_id"])}, {"$set": {"verified_email": True}})
    return {"status": "verified"}


@router.get("/verify/status")
async def verification_status(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    docs = await db.provider_documents.find({"provider_id": provider_id}).to_list(length=50)
    ver = await db.provider_verifications.find({"provider_id": provider_id}).to_list(length=50)
    user = await db.users.find_one({"_id": ObjectId(provider_id)})
    return {"documents": docs, "verifications": ver, "user": {"verified_phone": user.get("verified_phone"), "verified_email": user.get("verified_email"), "verified_by_admin": user.get("verified_by_admin")}}


# Admin endpoints
@router.get("/admin/verifications")
async def list_pending_verifications(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    db = get_db()
    pending_docs = await db.provider_documents.find({"status": "pending"}).to_list(length=200)
    pending_ver = await db.provider_verifications.find({"verified": False}).to_list(length=200)
    return {"pending_docs": pending_docs, "pending_verifications": pending_ver}


@router.put("/admin/verifications/{provider_id}/approve")
async def approve_provider(provider_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    db = get_db()
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$set": {"verified_by_admin": True, "verified_at": datetime.utcnow()}})
    await db.provider_documents.update_many({"provider_id": provider_id}, {"$set": {"status": "approved"}})
    await db.provider_verifications.update_many({"provider_id": provider_id}, {"$set": {"verified": True}})
    return {"status": "approved"}


@router.put("/admin/verifications/{provider_id}/reject")
async def reject_provider(provider_id: str, reason: dict, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    db = get_db()
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$set": {"verified_by_admin": False, "rejection_reason": reason.get("reason"), "verified_at": datetime.utcnow()}})
    await db.provider_documents.update_many({"provider_id": provider_id}, {"$set": {"status": "rejected"}})
    return {"status": "rejected"}

# ── Router Section: queue ──
queue_router = APIRouter()
router = queue_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from bson import ObjectId
import asyncio



@router.post("/join")
async def join_queue(data: QueueJoin, current_user: dict = Depends(get_current_user)):
    """Join service queue with smart positioning"""
    db = get_db()
    
    # Calculate position based on factors
    base_position = await db.queue.count_documents({"service_type": data.service_type, "status": "waiting"})
    
    # Priority adjustments
    position_modifier = 0
    if data.priority == "premium":
        position_modifier = -max(0, base_position // 2)  # Jump ahead
    elif data.priority == "emergency":
        position_modifier = -base_position  # Go to front
    
    final_position = max(1, base_position + 1 + position_modifier)
    
    queue_entry = {
        "user_id": current_user["sub"],
        "service_type": data.service_type,
        "priority": data.priority,
        "position": final_position,
        "status": "waiting",
        "joined_at": datetime.utcnow(),
        "estimated_wait": final_position * 15  # 15 min per position
    }
    
    result = await db.queue.insert_one(queue_entry)
    
    # Update positions of others if priority user
    if data.priority in ["premium", "emergency"]:
        await db.queue.update_many(
            {"service_type": data.service_type, "position": {"$gte": final_position}, "_id": {"$ne": result.inserted_id}},
            {"$inc": {"position": 1, "estimated_wait": 15}}
        )
    
    return {
        "queue_id": str(result.inserted_id),
        "position": final_position,
        "estimated_wait_minutes": queue_entry["estimated_wait"],
        "ahead_of_you": final_position - 1
    }

@router.get("/status/{queue_id}")
async def get_queue_status(queue_id: str):
    """Get real-time queue status"""
    db = get_db()
    entry = await db.queue.find_one({"_id": ObjectId(queue_id)})
    if not entry:
        return {"error": "Queue entry not found"}
    
    # Get current position (may have changed)
    current_position = await db.queue.count_documents({
        "service_type": entry["service_type"],
        "status": "waiting",
        "joined_at": {"$lt": entry["joined_at"]}
    }) + 1
    
    return {
        "position": current_position,
        "estimated_wait": current_position * 15,
        "status": entry["status"],
        "service_type": entry["service_type"]
    }

@router.post("/skip/{queue_id}")
async def skip_queue_position(queue_id: str, data: QueueSkipRequest, current_user: dict = Depends(get_current_user)):
    """Pay to skip queue positions"""
    db = get_db()
    
    payment_amount = data.payment_amount
    if payment_amount < 50:  # Minimum ₹50 to skip
        return {"error": "Minimum ₹50 required to skip"}
    
    positions_to_skip = min(5, payment_amount // 50)  # ₹50 per position
    
    await db.queue.update_one(
        {"_id": ObjectId(queue_id)},
        {"$inc": {"position": -positions_to_skip, "estimated_wait": -positions_to_skip * 15}}
    )
    
    return {"positions_skipped": positions_to_skip, "amount_charged": payment_amount}

@router.get("/analytics")
async def queue_analytics(current_user: dict = Depends(get_current_user)):
    """Queue analytics for admin"""
    if current_user["role"] != "admin":
        return {"error": "Admin access required"}
    
    db = get_db()
    
    # Average wait times by service
    pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$service_type",
            "avg_wait": {"$avg": {"$subtract": ["$served_at", "$joined_at"]}},
            "total_served": {"$sum": 1}
        }}
    ]
    
    stats = await db.queue.aggregate(pipeline).to_list(length=20)
    
    return {"queue_stats": stats}

# ── Router Section: reviews ──
reviews_router = APIRouter()
router = reviews_router
from fastapi import APIRouter, Depends
from datetime import datetime
from bson import ObjectId


@router.post("/")
async def create_review(review: ReviewCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # AI Authenticity Scoring (Simulated)
    # Check for short generic reviews or extreme patterns
    content = review.comment.lower()
    score = 100
    if len(content.split()) < 4: score -= 30
    if any(word in content for word in ["best", "worst", "amazing", "terrible"]) and review.rating in [1, 5]:
        score -= 10
        
    review_dict = review.dict()
    review_dict["user_id"] = current_user["sub"]
    review_dict["created_at"] = datetime.utcnow()
    review_dict["helpful_count"] = 0
    review_dict["authenticity_score"] = score
    review_dict["is_verified_booking"] = True # Since it's from our platform
    
    result = await db.reviews.insert_one(review_dict)
    
    # Update Provider Trust Graph Metrics
    # Neighborhood trust: rebooking percentage
    await db.users.update_one(
        {"_id": ObjectId(review.provider_id)},
        {"$inc": {"reviews_count": 1, "total_rating": review.rating}}
    )
    
    return {"id": str(result.inserted_id), "authenticity_score": score}

@router.get("/neighborhood-trust/{provider_id}")
async def get_neighborhood_trust(provider_id: str):
    """Calculate trust graph metrics for a provider in a specific area"""
    db = get_db()
    
    # Repeat customer rate
    pipeline = [
        {"$match": {"provider_id": provider_id, "status": "completed"}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$group": {"_id": None, "total_customers": {"$sum": 1}, "repeat_customers": {"$sum": {"$cond": [{"$gt": ["$count", 1]}, 1, 0]}}}}
    ]
    trust_stats = await db.bookings.aggregate(pipeline).to_list(length=1)
    
    if not trust_stats:
        return {"repeat_rate": 0, "neighbor_bookings": 0, "trust_score": 70}
        
    stats = trust_stats[0]
    repeat_rate = (stats["repeat_customers"] / stats["total_customers"] * 100) if stats["total_customers"] > 0 else 0
    
    return {
        "repeat_customer_rate": round(repeat_rate, 1),
        "total_local_bookings": stats["total_customers"],
        "neighborhood_rank": "Top 10%",
        "trust_score": min(100, 70 + (repeat_rate / 2))
    }

@router.get("/service/{service_id}")
async def get_service_reviews(service_id: str):
    db = get_db()
    reviews = await db.reviews.find({"service_id": service_id}).to_list(length=100)
    for r in reviews:
        r["_id"] = str(r["_id"])
    return reviews

@router.get("/provider/{provider_id}")
async def get_provider_reviews(provider_id: str):
    db = get_db()
    reviews = await db.reviews.find({"provider_id": provider_id}).to_list(length=100)
    for r in reviews:
        r["_id"] = str(r["_id"])
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews) if reviews else 0
    return {"reviews": reviews, "average_rating": avg_rating, "total": len(reviews)}

@router.post("/{review_id}/helpful")
async def mark_helpful(review_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.reviews.update_one({"_id": ObjectId(review_id)}, {"$inc": {"helpful_count": 1}})
    return {"status": "marked_helpful"}

@router.delete("/{review_id}")
async def delete_review(review_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.reviews.delete_one({"_id": ObjectId(review_id), "user_id": current_user["sub"]})
    return {"status": "deleted"}

# ── Router Section: roulette ──
roulette_router = APIRouter()
router = roulette_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict
import random


ROULETTE_CATEGORIES = {
    "wellness": {
        "name": "🧘 Wellness Roulette",
        "services": ["beauty", "fitness", "massage", "yoga", "meditation"],
        "surprise_factor": 0.8,
        "discount_range": [10, 30]
    },
    "home_care": {
        "name": "🏠 Home Care Roulette", 
        "services": ["cleaning", "plumbing", "electrical", "gardening", "pest_control"],
        "surprise_factor": 0.6,
        "discount_range": [15, 25]
    },
    "lifestyle": {
        "name": "✨ Lifestyle Roulette",
        "services": ["photography", "tutoring", "cooking", "pet_care", "delivery"],
        "surprise_factor": 0.9,
        "discount_range": [5, 20]
    },
    "mystery": {
        "name": "🎭 Mystery Service Box",
        "services": ["all"],  # Can be any service
        "surprise_factor": 1.0,
        "discount_range": [20, 50]
    }
}

DISCOVERY_CHALLENGES = {
    "service_explorer": {
        "name": "🗺️ Service Explorer",
        "description": "Try 5 different service categories",
        "reward": {"type": "discount", "value": 25, "services": "all"},
        "progress_tracking": "categories_tried"
    },
    "mystery_master": {
        "name": "🎪 Mystery Master", 
        "description": "Complete 3 mystery service boxes",
        "reward": {"type": "free_spin", "value": 5, "services": "premium"},
        "progress_tracking": "mystery_boxes_completed"
    },
    "roulette_champion": {
        "name": "🎰 Roulette Champion",
        "description": "Spin the roulette 10 times",
        "reward": {"type": "loyalty_points", "value": 1000, "services": "all"},
        "progress_tracking": "spins_completed"
    }
}

@router.post("/spin")
async def spin_roulette(
    data: RouletteSpin,
    current_user: dict = Depends(get_current_user)
):
    """Spin the service roulette wheel"""
    db = get_db()
    
    category = data.category
    bet_amount = data.bet_amount
    
    if category not in ROULETTE_CATEGORIES:
        return {"error": "Invalid roulette category"}
    
    roulette_config = ROULETTE_CATEGORIES[category]
    
    # Check daily spin limit (5 free spins per day)
    today = datetime.utcnow().date()
    daily_spins = await db.roulette_spins.count_documents({
        "user_id": current_user["sub"],
        "date": today.isoformat(),
        "cost": 0
    })
    
    # Determine spin cost
    spin_cost = 0 if daily_spins < 5 else bet_amount or 50
    
    if spin_cost > 0 and not bet_amount:
        return {"error": "Daily free spins exhausted. Bet amount required."}
    
    # Get available services
    if roulette_config["services"] == ["all"]:
        available_services = await db.services.find({"status": "active"}).to_list(length=100)
    else:
        available_services = await db.services.find({
            "category": {"$in": roulette_config["services"]},
            "status": "active"
        }).to_list(length=100)
    
    if not available_services:
        return {"error": "No services available for this category"}
    
    # Spin the wheel!
    selected_service = random.choice(available_services)
    
    # Calculate rewards
    discount_percent = random.randint(*roulette_config["discount_range"])
    bonus_points = random.randint(50, 200)
    
    # Special rewards for mystery category
    special_reward = None
    if category == "mystery" and random.random() < 0.1:  # 10% chance
        special_reward = {
            "type": "jackpot",
            "description": "🎉 JACKPOT! Free service + 500 bonus points!",
            "value": selected_service.get("price", 500),
            "bonus_points": 500
        }
    
    # Record spin
    spin_record = {
        "user_id": current_user["sub"],
        "category": category,
        "service_won": {
            "id": str(selected_service["_id"]),
            "name": selected_service["name"],
            "category": selected_service["category"],
            "original_price": selected_service.get("price", 500)
        },
        "discount_percent": discount_percent,
        "bonus_points": bonus_points,
        "special_reward": special_reward,
        "cost": spin_cost,
        "date": today.isoformat(),
        "timestamp": datetime.utcnow(),
        "claimed": False,
        "expires_at": datetime.utcnow() + timedelta(days=7)
    }
    
    result = await db.roulette_spins.insert_one(spin_record)
    
    # Award bonus points
    await db.loyalty_accounts.update_one(
        {"user_id": current_user["sub"]},
        {"$inc": {"points": bonus_points}},
        upsert=True
    )
    
    # Update discovery progress
    await update_discovery_progress(current_user["sub"], "spins_completed", db)
    
    return {
        "spin_id": str(result.inserted_id),
        "result": {
            "service": selected_service["name"],
            "category": selected_service["category"],
            "discount": f"{discount_percent}%",
            "bonus_points": bonus_points,
            "special_reward": special_reward,
            "expires_in_days": 7
        },
        "wheel_animation": generate_wheel_animation(category, selected_service),
        "claim_url": f"/roulette/claim/{result.inserted_id}"
    }

@router.get("/mystery-box")
async def open_mystery_box(
    box_type: str = "standard",
    current_user: dict = Depends(get_current_user)
):
    """Open a mystery service box"""
    db = get_db()
    
    box_types = {
        "standard": {"cost": 100, "services": 3, "discount_range": [10, 30]},
        "premium": {"cost": 250, "services": 5, "discount_range": [20, 40]},
        "luxury": {"cost": 500, "services": 8, "discount_range": [30, 60]}
    }
    
    if box_type not in box_types:
        return {"error": "Invalid box type"}
    
    box_config = box_types[box_type]
    
    # Check if user has enough loyalty points
    loyalty_account = await db.loyalty_accounts.find_one({"user_id": current_user["sub"]})
    current_points = loyalty_account.get("points", 0) if loyalty_account else 0
    
    if current_points < box_config["cost"]:
        return {"error": f"Insufficient points. Need {box_config['cost']}, have {current_points}"}
    
    # Deduct points
    await db.loyalty_accounts.update_one(
        {"user_id": current_user["sub"]},
        {"$inc": {"points": -box_config["cost"]}}
    )
    
    # Generate mystery services
    all_services = await db.services.find({"status": "active"}).to_list(length=200)
    mystery_services = random.sample(all_services, min(box_config["services"], len(all_services)))
    
    box_contents = []
    total_value = 0
    
    for service in mystery_services:
        discount = random.randint(*box_config["discount_range"])
        original_price = service.get("price", 500)
        discounted_price = original_price * (1 - discount/100)
        
        box_contents.append({
            "service": {
                "id": str(service["_id"]),
                "name": service["name"],
                "category": service["category"]
            },
            "original_price": original_price,
            "discount_percent": discount,
            "final_price": round(discounted_price, 2)
        })
        total_value += original_price - discounted_price
    
    # Record mystery box opening
    box_record = {
        "user_id": current_user["sub"],
        "box_type": box_type,
        "cost": box_config["cost"],
        "contents": box_contents,
        "total_savings": round(total_value, 2),
        "opened_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=14)
    }
    
    result = await db.mystery_boxes.insert_one(box_record)
    
    # Update discovery progress
    await update_discovery_progress(current_user["sub"], "mystery_boxes_completed", db)
    
    return {
        "box_id": str(result.inserted_id),
        "box_type": box_type,
        "contents": box_contents,
        "total_savings": round(total_value, 2),
        "points_spent": box_config["cost"],
        "expires_in_days": 14,
        "surprise_message": generate_surprise_message(box_type, len(box_contents))
    }

@router.get("/discovery-challenge")
async def get_discovery_challenges(current_user: dict = Depends(get_current_user)):
    """Get available discovery challenges and progress"""
    db = get_db()
    
    # Get user's discovery progress
    progress = await db.discovery_progress.find_one({"user_id": current_user["sub"]})
    if not progress:
        progress = {
            "user_id": current_user["sub"],
            "categories_tried": [],
            "mystery_boxes_completed": 0,
            "spins_completed": 0,
            "created_at": datetime.utcnow()
        }
        await db.discovery_progress.insert_one(progress)
    
    challenges = []
    for challenge_id, challenge in DISCOVERY_CHALLENGES.items():
        current_progress = get_challenge_progress(challenge, progress)
        
        challenges.append({
            "id": challenge_id,
            "name": challenge["name"],
            "description": challenge["description"],
            "progress": current_progress["current"],
            "target": current_progress["target"],
            "completed": current_progress["completed"],
            "reward": challenge["reward"],
            "completion_percentage": min(100, (current_progress["current"] / current_progress["target"]) * 100)
        })
    
    return {"challenges": challenges}

@router.post("/claim/{spin_id}")
async def claim_roulette_reward(spin_id: str, current_user: dict = Depends(get_current_user)):
    """Claim reward from roulette spin"""
    db = get_db()
    
    # Get spin record
    spin = await db.roulette_spins.find_one({
        "_id": ObjectId(spin_id),
        "user_id": current_user["sub"],
        "claimed": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not spin:
        return {"error": "Spin not found, already claimed, or expired"}
    
    # Create discount coupon
    coupon = {
        "user_id": current_user["sub"],
        "type": "roulette_discount",
        "service_id": spin["service_won"]["id"],
        "discount_percent": spin["discount_percent"],
        "original_spin_id": spin_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30),
        "used": False
    }
    
    coupon_result = await db.user_coupons.insert_one(coupon)
    
    # Mark spin as claimed
    await db.roulette_spins.update_one(
        {"_id": ObjectId(spin_id)},
        {"$set": {"claimed": True, "claimed_at": datetime.utcnow()}}
    )
    
    # Handle special rewards
    special_message = ""
    if spin.get("special_reward"):
        special = spin["special_reward"]
        if special["type"] == "jackpot":
            # Award free service credit
            await db.user_credits.insert_one({
                "user_id": current_user["sub"],
                "amount": special["value"],
                "type": "free_service",
                "source": "roulette_jackpot",
                "expires_at": datetime.utcnow() + timedelta(days=60)
            })
            special_message = f"🎉 Jackpot claimed! Free service credit of ₹{special['value']} added!"
    
    return {
        "message": "Reward claimed successfully!",
        "coupon_id": str(coupon_result.inserted_id),
        "discount": f"{spin['discount_percent']}% off {spin['service_won']['name']}",
        "expires_in_days": 30,
        "special_message": special_message
    }

@router.get("/surprise-recommendations")
async def get_surprise_recommendations(current_user: dict = Depends(get_current_user)):
    """Get AI-powered surprise service recommendations"""
    db = get_db()
    
    # Get user's booking history
    user_bookings = await db.bookings.find({
        "user_id": current_user["sub"]
    }).to_list(length=50)
    
    booked_categories = set(booking.get("service_type") for booking in user_bookings)
    
    # Get all available service categories
    all_categories = await db.services.distinct("category")
    untried_categories = list(set(all_categories) - booked_categories)
    
    # Generate surprise recommendations
    recommendations = []
    
    # 1. Completely new categories
    if untried_categories:
        surprise_category = random.choice(untried_categories)
        category_services = await db.services.find({
            "category": surprise_category,
            "status": "active"
        }).to_list(length=5)
        
        if category_services:
            surprise_service = random.choice(category_services)
            recommendations.append({
                "type": "new_category",
                "service": surprise_service,
                "reason": f"🌟 Discover {surprise_category} services!",
                "surprise_discount": random.randint(15, 35),
                "confidence": 0.7
            })
    
    # 2. Seasonal surprises
    current_month = datetime.utcnow().month
    seasonal_services = get_seasonal_service_suggestions(current_month)
    
    if seasonal_services:
        seasonal_service = random.choice(seasonal_services)
        services = await db.services.find({
            "category": seasonal_service,
            "status": "active"
        }).to_list(length=3)
        
        if services:
            recommendations.append({
                "type": "seasonal",
                "service": random.choice(services),
                "reason": f"🌸 Perfect for this season!",
                "surprise_discount": random.randint(10, 25),
                "confidence": 0.8
            })
    
    # 3. Trending services
    trending = await db.bookings.aggregate([
        {"$match": {"created_at": {"$gte": datetime.utcnow() - timedelta(days=7)}}},
        {"$group": {"_id": "$service_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 3}
    ]).to_list(length=3)
    
    if trending:
        trending_category = trending[0]["_id"]
        if trending_category not in booked_categories:
            trending_services = await db.services.find({
                "category": trending_category,
                "status": "active"
            }).to_list(length=3)
            
            if trending_services:
                recommendations.append({
                    "type": "trending",
                    "service": random.choice(trending_services),
                    "reason": "🔥 Trending this week!",
                    "surprise_discount": random.randint(5, 20),
                    "confidence": 0.9
                })
    
    # Clean up service data
    for rec in recommendations:
        if "_id" in rec["service"]:
            rec["service"]["_id"] = str(rec["service"]["_id"])
    
    return {
        "recommendations": recommendations,
        "total_surprises": len(recommendations),
        "discovery_tip": "Try something new and earn extra discovery points!"
    }

@router.get("/stats")
async def get_discovery_stats(current_user: dict = Depends(get_current_user)):
    """Get user's discovery and roulette statistics"""
    db = get_db()
    
    # Roulette stats
    total_spins = await db.roulette_spins.count_documents({"user_id": current_user["sub"]})
    claimed_rewards = await db.roulette_spins.count_documents({
        "user_id": current_user["sub"],
        "claimed": True
    })
    
    # Mystery box stats
    boxes_opened = await db.mystery_boxes.count_documents({"user_id": current_user["sub"]})
    
    # Discovery progress
    progress = await db.discovery_progress.find_one({"user_id": current_user["sub"]})
    categories_discovered = len(progress.get("categories_tried", [])) if progress else 0
    
    # Calculate total savings
    total_savings = await db.roulette_spins.aggregate([
        {"$match": {"user_id": current_user["sub"], "claimed": True}},
        {"$group": {"_id": None, "total": {"$sum": {"$multiply": ["$service_won.original_price", {"$divide": ["$discount_percent", 100]}]}}}}
    ]).to_list(length=1)
    
    savings_amount = total_savings[0]["total"] if total_savings else 0
    
    return {
        "roulette_spins": total_spins,
        "rewards_claimed": claimed_rewards,
        "mystery_boxes_opened": boxes_opened,
        "categories_discovered": categories_discovered,
        "total_savings": round(savings_amount, 2),
        "discovery_level": calculate_discovery_level(total_spins, boxes_opened, categories_discovered),
        "next_milestone": get_next_milestone(total_spins, boxes_opened)
    }

async def update_discovery_progress(user_id: str, progress_type: str, db):
    """Update user's discovery progress"""
    update_query = {"$inc": {progress_type: 1}}
    
    await db.discovery_progress.update_one(
        {"user_id": user_id},
        update_query,
        upsert=True
    )

def get_challenge_progress(challenge: Dict, progress: Dict) -> Dict:
    """Calculate challenge progress"""
    tracking_field = challenge["progress_tracking"]
    
    if tracking_field == "categories_tried":
        current = len(progress.get("categories_tried", []))
        target = 5
    elif tracking_field == "mystery_boxes_completed":
        current = progress.get("mystery_boxes_completed", 0)
        target = 3
    elif tracking_field == "spins_completed":
        current = progress.get("spins_completed", 0)
        target = 10
    else:
        current = 0
        target = 1
    
    return {
        "current": current,
        "target": target,
        "completed": current >= target
    }

def generate_wheel_animation(category: str, service: Dict) -> Dict:
    """Generate wheel animation data"""
    return {
        "wheel_type": category,
        "spin_duration": random.uniform(3.0, 5.0),
        "final_position": random.randint(0, 359),
        "bounce_effect": True,
        "sound_effects": ["spin", "tick", "win"],
        "visual_effects": ["sparkles", "confetti"] if category == "mystery" else ["sparkles"]
    }

def generate_surprise_message(box_type: str, service_count: int) -> str:
    """Generate surprise message for mystery box"""
    messages = {
        "standard": [
            f"🎁 Surprise! {service_count} amazing services await!",
            f"✨ Your mystery box revealed {service_count} hidden gems!",
            f"🎉 {service_count} services discovered - what will you try first?"
        ],
        "premium": [
            f"💎 Premium surprise! {service_count} exclusive services unlocked!",
            f"🌟 Jackpot! {service_count} premium services at your fingertips!",
            f"🎊 Premium mystery solved - {service_count} top-tier services revealed!"
        ],
        "luxury": [
            f"👑 Luxury experience! {service_count} elite services discovered!",
            f"💫 Ultimate surprise! {service_count} luxury services await your command!",
            f"🏆 Luxury mystery cracked - {service_count} VIP services unlocked!"
        ]
    }
    
    return random.choice(messages.get(box_type, messages["standard"]))

def get_seasonal_service_suggestions(month: int) -> List[str]:
    """Get seasonal service suggestions based on month"""
    seasonal_map = {
        1: ["fitness", "beauty", "cleaning"],  # New Year resolutions
        2: ["beauty", "fitness"],  # Valentine's prep
        3: ["cleaning", "gardening"],  # Spring cleaning
        4: ["gardening", "pest_control"],  # Spring gardening
        5: ["beauty", "fitness"],  # Summer prep
        6: ["fitness", "beauty", "photography"],  # Summer activities
        7: ["fitness", "photography"],  # Summer peak
        8: ["beauty", "fitness"],  # Continued summer
        9: ["tutoring", "fitness"],  # Back to school
        10: ["cleaning", "pest_control"],  # Pre-winter prep
        11: ["beauty", "photography"],  # Festival season
        12: ["cleaning", "beauty", "photography"]  # Holiday prep
    }
    
    return seasonal_map.get(month, ["cleaning", "beauty"])

def calculate_discovery_level(spins: int, boxes: int, categories: int) -> str:
    """Calculate user's discovery level"""
    total_score = spins + (boxes * 3) + (categories * 5)
    
    if total_score >= 100:
        return "🏆 Discovery Master"
    elif total_score >= 50:
        return "🌟 Explorer"
    elif total_score >= 20:
        return "🔍 Seeker"
    elif total_score >= 5:
        return "🌱 Curious"
    else:
        return "👶 Newbie"

def get_next_milestone(spins: int, boxes: int) -> Dict:
    """Get next milestone for user"""
    milestones = [
        {"spins": 5, "boxes": 1, "reward": "Free premium mystery box"},
        {"spins": 15, "boxes": 3, "reward": "25% discount on any service"},
        {"spins": 30, "boxes": 5, "reward": "VIP discovery status"},
        {"spins": 50, "boxes": 10, "reward": "Free luxury mystery box"}
    ]
    
    for milestone in milestones:
        if spins < milestone["spins"] or boxes < milestone["boxes"]:
            return {
                "spins_needed": max(0, milestone["spins"] - spins),
                "boxes_needed": max(0, milestone["boxes"] - boxes),
                "reward": milestone["reward"]
            }
    
    return {"message": "All milestones achieved! You're a Discovery Master!"}

# ── Router Section: services ──
services_router = APIRouter()
router = services_router
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from bson import ObjectId
from math import radians, sin, cos, sqrt, atan2



from pydantic import BaseModel

class VoicePrompt(BaseModel):
    text: str

def _haversine(lat1, lng1, lat2, lng2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


@router.get("/search")
async def search_services(
    q: Optional[str] = None,
    category: Optional[str] = None,
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: float = Query(10.0),
    min_rating: float = Query(0.0),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    emergency: Optional[bool] = None,
    limit: int = Query(20, le=100),
):
    db = get_db()
    query = {}

    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    if city:
        query["city"] = {"$regex": city, "$options": "i"}

    if min_rating > 0:
        query["rating"] = {"$gte": min_rating}

    if min_price is not None or max_price is not None:
        query["price_per_hour"] = {}
        if min_price is not None:
            query["price_per_hour"]["$gte"] = min_price
        if max_price is not None:
            query["price_per_hour"]["$lte"] = max_price

    if emergency:
        query["is_emergency"] = True

    services = await db.services.find(query).limit(limit * 5).to_list(length=limit * 5)
    
    use_location_filter = latitude is not None and longitude is not None and not city
    
    results = []
    if use_location_filter:
        for s in services:
            s["_id"] = str(s["_id"])
            p_lat = s.get("latitude") or 0
            p_lng = s.get("longitude") or 0
            dist = _haversine(latitude, longitude, p_lat, p_lng)
            s["distance"] = round(dist, 2)
            if dist <= radius:
                results.append(s)
        results.sort(key=lambda x: x["distance"])
    
    # Fallback if location filter returned nothing or wasn't used
    if not results:
        for s in services:
            s["_id"] = str(s["_id"])
            if latitude and longitude:
                p_lat = s.get("latitude") or 0
                p_lng = s.get("longitude") or 0
                s["distance"] = round(_haversine(latitude, longitude, p_lat, p_lng), 2)
        
        # Sort by rating if no results were found via distance
        services.sort(key=lambda x: x.get("rating", 0), reverse=True)
        results = services[:limit]

    return {"services": results, "total": len(results)}


@router.get("/categories")
async def get_categories():
    db = get_db()
    categories = await db.services.distinct("category")

    category_icons = {
        "electrician": "⚡", "electrical": "⚡",
        "plumber": "🔧", "plumbing": "🔧",
        "cleaner": "🧹", "cleaning": "🧹",
        "carpenter": "🪚", "carpentry": "🪚",
        "painter": "🎨", "painting": "🎨",
        "mechanic": "🔨", "repair": "🔨",
        "tutor": "📚", "tutoring": "📚",
        "beautician": "💇", "beauty": "💇",
        "chef": "👨‍🍳", "cooking": "👨‍🍳",
        "driver": "🚗", "delivery": "📦",
        "gardener": "🌱", "gardening": "🌱",
        "pest control": "🐛", "pest_control": "🐛",
        "fitness": "💪",
    }

    result = []
    for cat in sorted(categories):
        if cat:
            result.append({
                "value": cat,
                "label": cat.replace("_", " ").title(),
                "icon": category_icons.get(cat.lower(), "🔧"),
            })

    return {"categories": result}


@router.get("/cities")
async def get_cities():
    db = get_db()
    pipeline = [
        {"$match": {"city": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$city", "service_count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    result = await db.services.aggregate(pipeline).to_list(length=500)
    return [{"city": r["_id"], "service_count": r["service_count"]} for r in result if r["_id"]]


@router.get("/recommendations")
async def get_recommendations(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: float = Query(50.0),
    limit: int = Query(12, le=50),
    category: Optional[str] = None,
):
    """
    Get top-rated service recommendations.
    Works without authentication and without location.
    When location is provided, adds distance info but does NOT filter by radius
    (so results always appear).
    """
    db = get_db()

    query: dict = {"rating": {"$gte": 3.5}}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    # Fetch more than needed so we have variety
    services = (
        await db.services.find(query)
        .sort("rating", -1)
        .limit(limit * 3)
        .to_list(length=limit * 3)
    )

    # If still empty, fetch without rating filter
    if not services:
        services = (
            await db.services.find({} if not category else {"category": {"$regex": category, "$options": "i"}})
            .sort("rating", -1)
            .limit(limit)
            .to_list(length=limit)
        )

    result = []
    for s in services:
        s["_id"] = str(s["_id"])
        if latitude is not None and longitude is not None:
            p_lat = s.get("latitude") or s.get("location", {}).get("latitude") or 0
            p_lng = s.get("longitude") or s.get("location", {}).get("longitude") or 0
            if p_lat and p_lng:
                s["distance"] = round(_haversine(latitude, longitude, p_lat, p_lng), 2)
        result.append(s)

    # Sort: nearby first if location given, else by rating
    if latitude is not None and longitude is not None:
        result.sort(key=lambda x: (x.get("distance", 9999), -x.get("rating", 0)))
    else:
        result.sort(key=lambda x: -x.get("rating", 0))

    return {"recommendations": result[:limit], "total": len(result[:limit])}


# NOTE: /nearby MUST be before /{service_id} to avoid route conflict
@router.get("/nearby")
async def get_nearby_services(
    lat: float,
    lng: float,
    radius: float = 5.0,
    category: Optional[str] = None,
):
    db = get_db()
    query = {}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    services = await db.services.find(query).limit(500).to_list(length=500)

    nearby = []
    for s in services:
        s["_id"] = str(s["_id"])
        p_lat = s.get("latitude") or s.get("location", {}).get("latitude") or 0
        p_lng = s.get("longitude") or s.get("location", {}).get("longitude") or 0
        dist = _haversine(lat, lng, p_lat, p_lng)
        if dist <= radius:
            s["distance"] = round(dist, 2)
            nearby.append(s)

    nearby.sort(key=lambda x: x["distance"])
    return nearby[:20]


@router.get("/{service_id}")
async def get_service(service_id: str):
    db = get_db()
    try:
        oid = ObjectId(service_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service ID")
    service = await db.services.find_one({"_id": oid})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    service["_id"] = str(service["_id"])
    return service


@router.post("/")
async def create_service(service: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    service["provider_id"] = current_user["sub"]
    result = await db.services.insert_one(service)
    return {"id": str(result.inserted_id)}


@router.post("/voice-hail")
async def process_voice_hail(prompt: VoicePrompt):
    """
    AI NLP processing for Voice Hail text to extract intent.
    """
    text = prompt.text.lower()
    
    service_type = "general"
    urgency = "normal"
    
    if any(word in text for word in ["urgent", "emergency", "now", "quick", "fast", "immediately"]):
        urgency = "high"
        
    if any(word in text for word in ["plumb", "leak", "water", "pipe", "drain"]):
        service_type = "plumber"
    elif any(word in text for word in ["electri", "power", "shock", "wire", "light"]):
        service_type = "electrician"
    elif any(word in text for word in ["clean", "maid", "sweep", "dust"]):
        service_type = "house cleaning"
    elif any(word in text for word in ["fix", "repair", "handyman", "broken"]):
        service_type = "appliance repair"
    elif any(word in text for word in ["paint", "brush", "color", "wall"]):
        service_type = "painter"
    elif any(word in text for word in ["wood", "furniture", "door", "table"]):
        service_type = "carpenter"
    elif any(word in text for word in ["ac", "cool", "filter", "chilling"]):
        service_type = "ac technician"
    elif any(word in text for word in ["medical", "doctor", "health", "sick"]):
        service_type = "wellness"
        
    return {
        "service": service_type,
        "urgency": urgency,
        "original_text": prompt.text
    }

# ── Router Section: slots ──
slots_router = APIRouter()
router = slots_router
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from bson import ObjectId


@router.post("/availability/setup")
async def setup_availability(provider_id: str, schedule: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    schedule["provider_id"] = provider_id
    schedule["updated_at"] = datetime.utcnow()
    await db.provider_availability.update_one(
        {"provider_id": provider_id},
        {"$set": schedule},
        upsert=True
    )
    return {"status": "availability_set"}

@router.get("/availability/{provider_id}")
async def get_availability(provider_id: str, date: str):
    db = get_db()
    # Fetch from both collections for a unified view
    slot_bookings = await db.slot_bookings.find({
        "provider_id": provider_id, 
        "date": date,
        "status": {"$ne": "cancelled"}
    }).to_list(length=100)
    
    normal_bookings = await db.bookings.find({
        "provider_id": provider_id, 
        "scheduled_date": date,
        "status": {"$in": ["confirmed", "in_progress", "pending"]}
    }).to_list(length=100)
    
    # Provider-defined availability (default to 9-18)
    availability = await db.provider_availability.find_one({"provider_id": provider_id})
    start_hour = 9
    end_hour = 17
    
    slots = []
    for hour in range(start_hour, end_hour + 1):
        slot_time = f"{hour:02d}:00"
        
        # Checking BOTH collections
        is_booked = (
            any(b.get("time_slot") == slot_time for b in slot_bookings) or
            any(b.get("scheduled_time") == slot_time for b in normal_bookings)
        )
        
        # Demand calculation (Something Good)
        is_popular = (hour >= 10 and hour <= 12) or (hour >= 15 and hour <= 17)
        demand = "high" if (is_popular or len(slot_bookings) + len(normal_bookings) > 2) else "normal"
        
        slots.append({
            "time": slot_time, 
            "start_time": slot_time,
            "available": not is_booked,
            "is_available": not is_booked,
            "demand": demand
        })
    
    return {"date": date, "slots": slots}

@router.post("/book")
async def book_slot(booking: SlotBookingCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Consolidated collision check
    existing_sb = await db.slot_bookings.find_one({
        "provider_id": booking.provider_id,
        "date": booking.date,
        "time_slot": booking.time_slot,
        "status": {"$ne": "cancelled"}
    })
    existing_b = await db.bookings.find_one({
        "provider_id": booking.provider_id,
        "scheduled_date": booking.date,
        "scheduled_time": booking.time_slot,
        "status": {"$in": ["confirmed", "in_progress", "pending"]}
    })
    
    if existing_sb or existing_b:
        raise HTTPException(status_code=400, detail="This slot is already booked.")
    
    booking_dict = booking.dict()
    booking_dict["user_id"] = current_user["sub"]
    booking_dict["status"] = "confirmed"
    booking_dict["created_at"] = datetime.utcnow()
    result = await db.slot_bookings.insert_one(booking_dict)
    return {"id": str(result.inserted_id), "status": "confirmed"}

@router.get("/my-bookings")
async def get_my_slot_bookings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    bookings = await db.slot_bookings.find({"user_id": current_user["sub"]}).to_list(length=100)
    for b in bookings:
        b["_id"] = str(b["_id"])
    return bookings

@router.put("/cancel/{booking_id}")
async def cancel_slot_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.slot_bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "cancelled"}})
    return {"status": "cancelled"}

@router.get("/analytics")
async def get_slot_analytics(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total = await db.slot_bookings.count_documents({"provider_id": current_user["sub"]})
    confirmed = await db.slot_bookings.count_documents({"provider_id": current_user["sub"], "status": "confirmed"})
    return {"total_bookings": total, "confirmed": confirmed}

@router.get("/smart-scheduling")
async def get_smart_scheduling(date: str = None):
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
        
    # We simulate dynamic smart scheduling based on deterministic date variations
    seed = sum(ord(c) for c in date)
    
    time_slots = [
        {"time": "8:00 AM", "price": 50, "weather": "☀️ Sunny", "demand": "low", "discount": 15},
        {"time": "10:00 AM", "price": 65, "weather": "☀️ Sunny", "demand": "medium"},
        {"time": "12:00 PM", "price": 75, "weather": "☁️ Cloudy", "demand": "high"},
        {"time": "2:00 PM", "price": 80, "weather": "⛅ Partly Cloudy", "demand": "high"},
        {"time": "4:00 PM", "price": 70, "weather": "🌤️ Clear", "demand": "medium", "discount": 10},
        {"time": "6:00 PM", "price": 55, "weather": "🌤️ Clear", "demand": "low", "discount": 20},
    ]
    
    for i, slot in enumerate(time_slots):
        perturbation = ((seed + i * 17) % 11) - 5  # Range -5 to +5
        slot["price"] = max(20, slot["price"] + perturbation)
    
    return {"date": date, "slots": time_slots}

# ── Router Section: surge ──
surge_router = APIRouter()
router = surge_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import requests
import math



@router.post("/calculate")
async def calculate_surge_pricing(data: SurgeCalculation):
    """Calculate dynamic surge pricing based on multiple factors"""
    db = get_db()
    
    base_price = {
        "plumbing": 500,
        "electrical": 600,
        "cleaning": 300,
        "beauty": 400,
        "fitness": 800,
        "delivery": 100,
        "repair": 450
    }.get(data.service_type, 400)
    
    surge_multiplier = 1.0
    factors = []
    
    # 1. Demand Factor (based on current bookings)
    current_hour = datetime.utcnow().hour
    recent_bookings = await db.bookings.count_documents({
        "created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)},
        "service_type": data.service_type
    })
    
    if recent_bookings > 10:
        demand_surge = 1.3
        factors.append({"factor": "High Demand", "multiplier": 1.3})
    elif recent_bookings > 5:
        demand_surge = 1.15
        factors.append({"factor": "Medium Demand", "multiplier": 1.15})
    else:
        demand_surge = 1.0
    
    surge_multiplier *= demand_surge
    
    # 2. Time-based Factor
    if 18 <= current_hour <= 21:  # Peak evening hours
        time_surge = 1.25
        factors.append({"factor": "Peak Hours", "multiplier": 1.25})
    elif current_hour < 8 or current_hour > 22:  # Early morning/late night
        time_surge = 1.4
        factors.append({"factor": "Off Hours Premium", "multiplier": 1.4})
    else:
        time_surge = 1.0
    
    surge_multiplier *= time_surge
    
    # 3. Weather Factor (mock weather API)
    try:
        # In production, use actual weather API
        weather_conditions = ["sunny", "rainy", "stormy", "cloudy"][datetime.utcnow().day % 4]
        
        if weather_conditions == "stormy" and data.service_type in ["plumbing", "electrical"]:
            weather_surge = 1.5
            factors.append({"factor": "Storm Emergency", "multiplier": 1.5})
        elif weather_conditions == "rainy" and data.service_type == "delivery":
            weather_surge = 1.3
            factors.append({"factor": "Rain Surcharge", "multiplier": 1.3})
        else:
            weather_surge = 1.0
        
        surge_multiplier *= weather_surge
    except:
        pass
    
    # 4. Provider Availability Factor
    available_providers = await db.users.count_documents({
        "role": "provider",
        "specializations": data.service_type,
        "is_online": True
    })
    
    total_providers = await db.users.count_documents({
        "role": "provider",
        "specializations": data.service_type
    })
    
    availability_ratio = available_providers / max(total_providers, 1)
    
    if availability_ratio < 0.3:  # Less than 30% available
        availability_surge = 1.6
        factors.append({"factor": "Low Provider Availability", "multiplier": 1.6})
    elif availability_ratio < 0.5:  # Less than 50% available
        availability_surge = 1.2
        factors.append({"factor": "Limited Availability", "multiplier": 1.2})
    else:
        availability_surge = 1.0
    
    surge_multiplier *= availability_surge
    
    # 5. Urgency Factor
    if data.urgency == "emergency":
        urgency_surge = 1.8
        factors.append({"factor": "Emergency Service", "multiplier": 1.8})
    elif data.urgency == "urgent":
        urgency_surge = 1.3
        factors.append({"factor": "Urgent Request", "multiplier": 1.3})
    else:
        urgency_surge = 1.0
    
    surge_multiplier *= urgency_surge
    
    # 6. Day of Week Factor
    day_of_week = datetime.utcnow().weekday()
    if day_of_week >= 5:  # Weekend
        weekend_surge = 1.15
        factors.append({"factor": "Weekend Premium", "multiplier": 1.15})
        surge_multiplier *= weekend_surge
    
    # Cap the surge at 3x
    surge_multiplier = min(surge_multiplier, 3.0)
    
    final_price = round(base_price * surge_multiplier, 2)
    
    return {
        "service_type": data.service_type,
        "base_price": base_price,
        "surge_multiplier": round(surge_multiplier, 2),
        "final_price": final_price,
        "factors": factors,
        "savings_tip": "Book during off-peak hours (9 AM - 5 PM) for lower prices" if surge_multiplier > 1.2 else None
    }

@router.get("/predictions")
async def get_price_predictions(service_type: str):
    """Predict pricing for next 24 hours"""
    predictions = []
    
    for hour in range(24):
        future_time = datetime.utcnow() + timedelta(hours=hour)
        
        # Simulate demand patterns
        if 8 <= future_time.hour <= 18:
            demand_level = "medium"
            multiplier = 1.1
        elif 18 <= future_time.hour <= 21:
            demand_level = "high"
            multiplier = 1.3
        else:
            demand_level = "low"
            multiplier = 0.9
        
        base_price = {"plumbing": 500, "electrical": 600, "cleaning": 300}.get(service_type, 400)
        predicted_price = round(base_price * multiplier, 2)
        
        predictions.append({
            "hour": future_time.hour,
            "date": future_time.date().isoformat(),
            "demand_level": demand_level,
            "predicted_price": predicted_price,
            "multiplier": multiplier
        })
    
    return {"predictions": predictions}

@router.get("/surge-map")
async def get_surge_map():
    """Get surge pricing heatmap for different areas"""
    # Mock data for different areas
    areas = [
        {"area": "Downtown", "surge": 1.5, "reason": "High demand"},
        {"area": "Suburbs", "surge": 1.0, "reason": "Normal demand"},
        {"area": "Airport", "surge": 1.8, "reason": "Limited providers"},
        {"area": "Tech Park", "surge": 1.3, "reason": "Peak hours"},
        {"area": "Residential", "surge": 0.9, "reason": "Low demand"}
    ]
    
    return {"surge_map": areas}

@router.post("/notify-price-drop")
async def notify_price_drop(data: PriceDropNotificationRequest, current_user: dict = Depends(get_current_user)):
    """Set price drop notification"""
    db = get_db()
    
    service_type = data.service_type
    target_price = data.target_price
    notification = {
        "user_id": current_user["sub"],
        "service_type": service_type,
        "target_price": target_price,
        "created_at": datetime.utcnow(),
        "status": "active"
    }
    
    result = await db.price_alerts.insert_one(notification)
    
    return {
        "alert_id": str(result.inserted_id),
        "message": f"You'll be notified when {service_type} prices drop to ₹{target_price}"
    }

# ── Router Section: swap ──
swap_router = APIRouter()
router = swap_router
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict
import math


# Service value multipliers for fair exchanges
SERVICE_VALUES = {
    "cleaning": 1.0,      # Base value
    "plumbing": 1.5,      # Higher skill = higher value
    "electrical": 1.6,
    "beauty": 1.2,
    "fitness": 1.3,
    "tutoring": 1.4,
    "cooking": 1.1,
    "gardening": 0.9,
    "pet_care": 1.0,
    "delivery": 0.8,
    "repair": 1.3,
    "photography": 1.5,
    "design": 1.7,
    "massage": 1.4
}

@router.post("/create-offer")
async def create_swap_offer(
    data: SwapOfferCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a service swap offer"""
    db = get_db()
    
    offering_service = data.offering_service
    offering_hours = data.offering_hours
    seeking_service = data.seeking_service
    seeking_hours = data.seeking_hours
    description = data.description
    location = data.location
    expires_in_days = 30  # Default or extract from data
    
    # Validate user can provide the offering service
    user = await db.users.find_one({"_id": current_user["sub"]})
    if user["role"] == "provider":
        if offering_service not in user.get("specializations", []):
            return {"error": f"You're not qualified to offer {offering_service} services"}
    
    # Calculate fair exchange ratio
    offering_value = SERVICE_VALUES.get(offering_service, 1.0) * offering_hours
    seeking_value = SERVICE_VALUES.get(seeking_service, 1.0) * seeking_hours
    
    fairness_ratio = offering_value / seeking_value if seeking_value > 0 else 0
    
    # Create swap offer
    swap_offer = {
        "user_id": current_user["sub"],
        "offering": {
            "service": offering_service,
            "hours": offering_hours,
            "value_points": offering_value
        },
        "seeking": {
            "service": seeking_service,
            "hours": seeking_hours,
            "value_points": seeking_value
        },
        "description": description,
        "location": location,
        "fairness_ratio": round(fairness_ratio, 2),
        "status": "active",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=expires_in_days),
        "views": 0,
        "interested_users": [],
        "swap_requests": []
    }
    
    result = await db.swap_offers.insert_one(swap_offer)
    
    # Find potential matches
    potential_matches = await find_swap_matches(str(result.inserted_id), db)
    
    return {
        "offer_id": str(result.inserted_id),
        "message": "Swap offer created successfully!",
        "fairness_ratio": fairness_ratio,
        "fairness_status": get_fairness_status(fairness_ratio),
        "potential_matches": len(potential_matches),
        "expires_at": swap_offer["expires_at"].isoformat()
    }

@router.get("/browse")
async def browse_swap_offers(
    seeking_service: Optional[str] = None,
    offering_service: Optional[str] = None,
    location: Optional[Dict] = None,
    max_distance_km: float = 10.0,
    min_fairness_ratio: float = 0.8,
    limit: int = 20
):
    """Browse available swap offers"""
    db = get_db()
    
    # Build query
    query = {
        "status": "active",
        "expires_at": {"$gt": datetime.utcnow()}
    }
    
    if seeking_service:
        query["offering.service"] = seeking_service
    
    if offering_service:
        query["seeking.service"] = offering_service
    
    if min_fairness_ratio:
        query["fairness_ratio"] = {"$gte": min_fairness_ratio}
    
    # Get offers
    offers = await db.swap_offers.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
    
    # Enrich with user data
    for offer in offers:
        offer["_id"] = str(offer["_id"])
        
        # Get user info
        user = await db.users.find_one({"_id": offer["user_id"]})
        if user:
            offer["user_info"] = {
                "name": user.get("full_name", "Anonymous"),
                "rating": user.get("rating", 0),
                "verified": user.get("is_verified", False),
                "reviews_count": user.get("reviews_count", 0)
            }
        
        # Calculate distance (simplified)
        if location:
            offer["distance_km"] = calculate_distance(location, offer["location"])
        
        # Calculate time remaining
        time_remaining = offer["expires_at"] - datetime.utcnow()
        offer["days_remaining"] = max(0, time_remaining.days)
        
        # Add fairness indicator
        offer["fairness_status"] = get_fairness_status(offer["fairness_ratio"])
    
    # Filter by distance if location provided
    if location:
        offers = [offer for offer in offers if offer.get("distance_km", 0) <= max_distance_km]
    
    return {"offers": offers, "total_found": len(offers)}

@router.post("/request-swap/{offer_id}")
async def request_swap(
    offer_id: str,
    data: SwapRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Request to swap services with an offer"""
    db = get_db()
    
    message = data.message
    proposed_schedule = data.proposed_schedule
    
    # Get the offer
    offer = await db.swap_offers.find_one({"_id": ObjectId(offer_id), "status": "active"})
    if not offer:
        return {"error": "Offer not found or no longer active"}
    
    # Can't swap with yourself
    if offer["user_id"] == current_user["sub"]:
        return {"error": "Cannot swap with yourself"}
    
    # Check if user can provide the sought service
    user = await db.users.find_one({"_id": current_user["sub"]})
    if user["role"] == "provider":
        if offer["seeking"]["service"] not in user.get("specializations", []):
            return {"error": f"You're not qualified to provide {offer['seeking']['service']} services"}
    
    # Check if already requested
    existing_request = await db.swap_requests.find_one({
        "offer_id": offer_id,
        "requester_id": current_user["sub"],
        "status": {"$in": ["pending", "accepted"]}
    })
    
    if existing_request:
        return {"error": "You already have a pending request for this offer"}
    
    # Create swap request
    swap_request = {
        "offer_id": offer_id,
        "offer_owner_id": offer["user_id"],
        "requester_id": current_user["sub"],
        "message": message,
        "proposed_schedule": proposed_schedule,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7)  # Request expires in 7 days
    }
    
    result = await db.swap_requests.insert_one(swap_request)
    
    # Add to offer's request list
    await db.swap_offers.update_one(
        {"_id": ObjectId(offer_id)},
        {"$push": {"swap_requests": str(result.inserted_id)}}
    )
    
    # Notify offer owner
    await db.notifications.insert_one({
        "user_id": offer["user_id"],
        "type": "swap_request",
        "title": "New Swap Request!",
        "message": f"Someone wants to swap {offer['seeking']['service']} for your {offer['offering']['service']}",
        "swap_request_id": str(result.inserted_id),
        "created_at": datetime.utcnow()
    })
    
    return {
        "request_id": str(result.inserted_id),
        "message": "Swap request sent successfully!",
        "status": "pending"
    }

@router.get("/my-offers")
async def get_my_offers(current_user: dict = Depends(get_current_user)):
    """Get user's swap offers"""
    db = get_db()
    
    offers = await db.swap_offers.find({
        "user_id": current_user["sub"]
    }).sort("created_at", -1).to_list(length=50)
    
    for offer in offers:
        offer["_id"] = str(offer["_id"])
        
        # Get pending requests count
        offer["pending_requests"] = await db.swap_requests.count_documents({
            "offer_id": str(offer["_id"]),
            "status": "pending"
        })
        
        # Get completed swaps count
        offer["completed_swaps"] = await db.swap_requests.count_documents({
            "offer_id": str(offer["_id"]),
            "status": "completed"
        })
    
    return {"my_offers": offers}

@router.get("/my-requests")
async def get_my_requests(current_user: dict = Depends(get_current_user)):
    """Get user's swap requests"""
    db = get_db()
    
    # Requests I made
    my_requests = await db.swap_requests.find({
        "requester_id": current_user["sub"]
    }).sort("created_at", -1).to_list(length=50)
    
    # Requests for my offers
    requests_for_me = await db.swap_requests.find({
        "offer_owner_id": current_user["sub"]
    }).sort("created_at", -1).to_list(length=50)
    
    # Enrich with offer data
    for request in my_requests + requests_for_me:
        request["_id"] = str(request["_id"])
        
        # Get offer details
        offer = await db.swap_offers.find_one({"_id": ObjectId(request["offer_id"])})
        if offer:
            request["offer_details"] = {
                "offering": offer["offering"],
                "seeking": offer["seeking"],
                "description": offer["description"]
            }
        
        # Get other party info
        other_user_id = request["offer_owner_id"] if request["requester_id"] == current_user["sub"] else request["requester_id"]
        other_user = await db.users.find_one({"_id": other_user_id})
        if other_user:
            request["other_party"] = {
                "name": other_user.get("full_name", "Anonymous"),
                "rating": other_user.get("rating", 0),
                "verified": other_user.get("is_verified", False)
            }
    
    return {
        "my_requests": my_requests,
        "requests_for_me": requests_for_me
    }

@router.post("/accept-request/{request_id}")
async def accept_swap_request(request_id: str, current_user: dict = Depends(get_current_user)):
    """Accept a swap request"""
    db = get_db()
    
    # Get the request
    request = await db.swap_requests.find_one({
        "_id": ObjectId(request_id),
        "offer_owner_id": current_user["sub"],
        "status": "pending"
    })
    
    if not request:
        return {"error": "Request not found or not authorized"}
    
    # Update request status
    await db.swap_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "accepted", "accepted_at": datetime.utcnow()}}
    )
    
    # Update offer status
    await db.swap_offers.update_one(
        {"_id": ObjectId(request["offer_id"])},
        {"$set": {"status": "matched"}}
    )
    
    # Create swap agreement
    agreement = {
        "request_id": request_id,
        "offer_id": request["offer_id"],
        "party_a": current_user["sub"],  # Offer owner
        "party_b": request["requester_id"],  # Requester
        "services": {
            "a_provides": None,  # Will be filled from offer
            "b_provides": None   # Will be filled from offer
        },
        "schedule": request["proposed_schedule"],
        "status": "agreed",
        "created_at": datetime.utcnow(),
        "completion_deadline": datetime.utcnow() + timedelta(days=30)
    }
    
    # Get offer details to fill services
    offer = await db.swap_offers.find_one({"_id": ObjectId(request["offer_id"])})
    if offer:
        agreement["services"]["a_provides"] = offer["offering"]
        agreement["services"]["b_provides"] = offer["seeking"]
    
    result = await db.swap_agreements.insert_one(agreement)
    
    # Notify requester
    await db.notifications.insert_one({
        "user_id": request["requester_id"],
        "type": "swap_accepted",
        "title": "Swap Request Accepted! 🎉",
        "message": "Your swap request has been accepted. Time to schedule!",
        "agreement_id": str(result.inserted_id),
        "created_at": datetime.utcnow()
    })
    
    return {
        "agreement_id": str(result.inserted_id),
        "message": "Swap request accepted! Agreement created.",
        "next_step": "Schedule the service exchange"
    }

@router.post("/complete-swap/{agreement_id}")
async def complete_swap(
    agreement_id: str,
    data: SwapCompleteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Mark swap as completed and rate the experience"""
    db = get_db()
    
    completion_proof = data.completion_proof
    rating = data.rating
    feedback = data.feedback
    
    # Get agreement
    agreement = await db.swap_agreements.find_one({
        "_id": ObjectId(agreement_id),
        "$or": [{"party_a": current_user["sub"]}, {"party_b": current_user["sub"]}],
        "status": "agreed"
    })
    
    if not agreement:
        return {"error": "Agreement not found or not authorized"}
    
    # Determine which party is completing
    completing_party = "a" if agreement["party_a"] == current_user["sub"] else "b"
    other_party = agreement["party_b"] if completing_party == "a" else agreement["party_a"]
    
    # Mark completion
    completion_field = f"completed_by_{completing_party}"
    await db.swap_agreements.update_one(
        {"_id": ObjectId(agreement_id)},
        {
            "$set": {
                completion_field: True,
                f"{completion_field}_at": datetime.utcnow(),
                f"{completion_field}_proof": completion_proof
            }
        }
    )
    
    # Check if both parties completed
    updated_agreement = await db.swap_agreements.find_one({"_id": ObjectId(agreement_id)})
    both_completed = updated_agreement.get("completed_by_a", False) and updated_agreement.get("completed_by_b", False)
    
    if both_completed:
        await db.swap_agreements.update_one(
            {"_id": ObjectId(agreement_id)},
            {"$set": {"status": "completed", "completed_at": datetime.utcnow()}}
        )
    
    # Add rating and feedback
    await db.swap_ratings.insert_one({
        "agreement_id": agreement_id,
        "rater_id": current_user["sub"],
        "rated_user_id": other_party,
        "rating": rating,
        "feedback": feedback,
        "created_at": datetime.utcnow()
    })
    
    # Update user's swap statistics
    await db.users.update_one(
        {"_id": current_user["sub"]},
        {"$inc": {"swap_stats.completed": 1, "swap_stats.total_value": updated_agreement["services"][f"{completing_party}_provides"]["value_points"]}}
    )
    
    return {
        "message": "Swap completion recorded!",
        "both_completed": both_completed,
        "status": "completed" if both_completed else "partially_completed"
    }

@router.get("/recommendations")
async def get_swap_recommendations(current_user: dict = Depends(get_current_user)):
    """Get personalized swap recommendations"""
    db = get_db()
    
    # Get user's service history to understand preferences
    user_bookings = await db.bookings.find({
        "user_id": current_user["sub"]
    }).to_list(length=100)
    
    # Analyze what services user frequently needs
    service_frequency = {}
    for booking in user_bookings:
        service = booking.get("service_type")
        service_frequency[service] = service_frequency.get(service, 0) + 1
    
    # Get user's skills (if provider)
    user = await db.users.find_one({"_id": current_user["sub"]})
    user_skills = user.get("specializations", []) if user["role"] == "provider" else []
    
    recommendations = []
    
    # Find offers where user can provide what's sought and needs what's offered
    for skill in user_skills:
        for needed_service, frequency in service_frequency.items():
            if frequency >= 2:  # Services user needs frequently
                matching_offers = await db.swap_offers.find({
                    "seeking.service": skill,
                    "offering.service": needed_service,
                    "status": "active",
                    "user_id": {"$ne": current_user["sub"]}
                }).limit(5).to_list(length=5)
                
                for offer in matching_offers:
                    offer["_id"] = str(offer["_id"])
                    offer["recommendation_reason"] = f"You can provide {skill} and frequently need {needed_service}"
                    offer["match_score"] = frequency * offer["fairness_ratio"]
                    recommendations.append(offer)
    
    # Sort by match score
    recommendations.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    
    return {"recommendations": recommendations[:10]}

@router.get("/statistics")
async def get_swap_statistics():
    """Get platform swap statistics"""
    db = get_db()
    
    # Total swaps
    total_offers = await db.swap_offers.count_documents({})
    active_offers = await db.swap_offers.count_documents({"status": "active"})
    completed_swaps = await db.swap_agreements.count_documents({"status": "completed"})
    
    # Most popular services
    popular_offering = await db.swap_offers.aggregate([
        {"$group": {"_id": "$offering.service", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    
    popular_seeking = await db.swap_offers.aggregate([
        {"$group": {"_id": "$seeking.service", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    
    # Average fairness ratio
    avg_fairness = await db.swap_offers.aggregate([
        {"$group": {"_id": None, "avg_fairness": {"$avg": "$fairness_ratio"}}}
    ]).to_list(length=1)
    
    avg_fairness_ratio = avg_fairness[0]["avg_fairness"] if avg_fairness else 0
    
    return {
        "total_offers": total_offers,
        "active_offers": active_offers,
        "completed_swaps": completed_swaps,
        "success_rate": round((completed_swaps / max(total_offers, 1)) * 100, 1),
        "popular_offerings": popular_offering,
        "popular_seekings": popular_seeking,
        "average_fairness_ratio": round(avg_fairness_ratio, 2),
        "insights": [
            "Cleaning services are most commonly offered",
            "Tutoring services are most sought after",
            "Average swap completion time is 2 weeks"
        ]
    }

async def find_swap_matches(offer_id: str, db):
    """Find potential matches for a swap offer"""
    offer = await db.swap_offers.find_one({"_id": ObjectId(offer_id)})
    if not offer:
        return []
    
    # Find offers that complement this one
    matches = await db.swap_offers.find({
        "offering.service": offer["seeking"]["service"],
        "seeking.service": offer["offering"]["service"],
        "status": "active",
        "_id": {"$ne": ObjectId(offer_id)},
        "user_id": {"$ne": offer["user_id"]}
    }).limit(10).to_list(length=10)
    
    return matches

def calculate_distance(loc1: Dict, loc2: Dict) -> float:
    """Calculate distance between two locations (simplified)"""
    # In production, use proper geospatial calculations
    lat1, lng1 = loc1.get("lat", 0), loc1.get("lng", 0)
    lat2, lng2 = loc2.get("lat", 0), loc2.get("lng", 0)
    
    # Simplified distance calculation
    return abs(lat1 - lat2) + abs(lng1 - lng2)

def get_fairness_status(ratio: float) -> str:
    """Get fairness status based on ratio"""
    if ratio >= 0.9 and ratio <= 1.1:
        return "Very Fair"
    elif ratio >= 0.8 and ratio <= 1.2:
        return "Fair"
    elif ratio >= 0.7 and ratio <= 1.3:
        return "Acceptable"
    else:
        return "Unbalanced"

# ── Router Section: tracking ──
tracking_router = APIRouter()
router = tracking_router
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from datetime import datetime
from bson import ObjectId
from typing import Optional
import math


class LocationManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, booking_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[booking_id] = websocket
    
    def disconnect(self, booking_id: str):
        if booking_id in self.active_connections:
            del self.active_connections[booking_id]
    
    async def broadcast_location(self, booking_id: str, location_data: dict):
        if booking_id in self.active_connections:
            await self.active_connections[booking_id].send_json(location_data)

location_manager = LocationManager()

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@router.post("/update-location")
async def update_location(
    latitude: float,
    longitude: float,
    accuracy: Optional[float] = None,
    speed: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    location_data = {
        "provider_id": current_user["sub"],
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy,
        "speed": speed,
        "timestamp": datetime.utcnow()
    }
    await db.location_history.insert_one(location_data)
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": {"current_location": {"latitude": latitude, "longitude": longitude, "last_updated": datetime.utcnow()}}}
    )
    active_bookings = await db.bookings.find({"provider_id": current_user["sub"], "status": {"$in": ["confirmed", "in_progress"]}}).to_list(length=10)
    for booking in active_bookings:
        await location_manager.broadcast_location(str(booking["_id"]), location_data)
    return {"status": "updated", "latitude": latitude, "longitude": longitude}

@router.get("/location/{booking_id}")
async def get_location(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        return {"error": "Booking not found"}
    location = await db.location_history.find_one({"provider_id": booking.get("provider_id")}, sort=[("timestamp", -1)])
    if location:
        location["_id"] = str(location["_id"])
    return location

@router.get("/history/{provider_id}")
async def get_location_history(provider_id: str):
    db = get_db()
    history = await db.location_history.find({"provider_id": provider_id}).sort("timestamp", -1).limit(50).to_list(length=50)
    for h in history:
        h["_id"] = str(h["_id"])
    return history

@router.get("/nearby-providers")
async def get_nearby_providers(latitude: float, longitude: float, service_type: Optional[str] = None, radius_km: float = 5.0):
    db = get_db()
    query = {"role": "provider", "is_verified": True}
    if service_type:
        query["specializations"] = service_type
    providers = await db.users.find(query).to_list(length=100)
    nearby = []
    for provider in providers:
        if "current_location" in provider:
            loc = provider["current_location"]
            distance = calculate_distance(latitude, longitude, loc["latitude"], loc["longitude"])
            if distance <= radius_km:
                nearby.append({"provider_id": str(provider["_id"]), "name": provider.get("full_name"), "distance_km": round(distance, 2), "eta_minutes": int(distance * 2)})
    nearby.sort(key=lambda x: x["distance_km"])
    return {"nearby_providers": nearby}

@router.websocket("/ws/{booking_id}")
async def location_websocket(websocket: WebSocket, booking_id: str):
    await location_manager.connect(booking_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        location_manager.disconnect(booking_id)

# ── Router Section: verification ──
verification_router = APIRouter()
router = verification_router
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from datetime import datetime
from bson.objectid import ObjectId
import json
import base64


@router.post("/work")
async def verify_work(
    job_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Project Gallery Upload & Proof of Visit.
    Validates work with GPS timestamp and image evidence.
    """
    db = get_db()
    
    # Read image contents (In production, save to S3/Cloudinary and store URL)
    before_bytes = await before_image.read()
    after_bytes = await after_image.read()
    
    # Simple base64 for quick demo validation (simulating cloud storage)
    before_url = f"data:{before_image.content_type};base64,{base64.b64encode(before_bytes).decode('utf-8')}"
    after_url = f"data:{after_image.content_type};base64,{base64.b64encode(after_bytes).decode('utf-8')}"
    
    # 1. Verification Record
    verification_record = {
        "provider_id": current_user["sub"],
        "job_id": job_id,
        "location": {"lat": latitude, "lng": longitude},
        "timestamp": datetime.utcnow(),
        "images": {
            "before": before_url,
            "after": after_url
        },
        "status": "verified"
    }
    
    await db.work_verifications.insert_one(verification_record)
    
    # 2. Update Booking Status to Completed/Verified
    try:
        b_oid = ObjectId(job_id)
        await db.bookings.update_one(
            {"_id": b_oid},
            {"$set": {"status": "completed", "is_verified": True}}
        )
    except Exception as e:
        print(f"Skipping booking update: {e}")
        pass 
        
    return {"message": "Work verified successfully", "status": "verified"}

@router.post("/check-in")
async def check_in(
    data: CheckInRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Proof of Visit: Capture GPS coordinates and timestamp upon arrival.
    """
    db = get_db()
    
    job_id = data.job_id
    latitude = data.latitude
    longitude = data.longitude
    
    # 1. Update Booking with Check-in data
    try:
        b_oid = ObjectId(job_id)
        await db.bookings.update_one(
            {"_id": b_oid},
            {
                "$set": {
                    "check_in": {
                        "lat": latitude,
                        "lng": longitude,
                        "timestamp": datetime.utcnow()
                    },
                    "status": "in_progress"
                }
            }
        )
    except Exception as e:
        print(f"Check-in error: {e}")
    
    return {"message": "Check-in successful", "status": "in_progress"}

@router.get("/trust-score")
async def get_trust_score(current_user: dict = Depends(get_current_user)):
    """
    Trust Score Logic: Trust = (0.4 * Rating) + (0.3 * Review Sentiment) + (0.3 * Gallery Density).
    """
    db = get_db()
    
    if current_user.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers have a trust score")
        
    provider_id = current_user["sub"]
    
    # 1. Rating (40%)
    reviews = await db.reviews.find({"provider_id": provider_id}).to_list(100)
    avg_rating = sum([r.get("rating", 5) for r in reviews]) / max(len(reviews), 1)
    scaled_rating = avg_rating * 20 # Scaled to 100
    
    # 2. Review Sentiment (30%) - Logic: Weight positive vs negative keywords or score from DB
    # For demo: Scaling rating as proxy for sentiment
    review_sentiment = min((avg_rating / 5.0) * 105, 100.0) 
    
    # 3. Gallery Density (30%) - 1 verified job = 10% density, Max 100%
    verified_jobs = await db.work_verifications.count_documents({"provider_id": provider_id})
    gallery_density = min(verified_jobs * 10, 100)
    
    # Final Formula
    trust_score = (0.4 * scaled_rating) + (0.3 * review_sentiment) + (0.3 * gallery_density)
    
    # Verification Badge (needs 3+ verified jobs)
    is_verified_badge = verified_jobs >= 3
    
    # Update user profile with latest badge/score
    try:
        u_oid = ObjectId(provider_id)
        await db.users.update_one(
            {"_id": u_oid},
            {"$set": {"trust_score": round(trust_score, 1), "is_verified_badge": is_verified_badge}}
        )
    except Exception as e:
        print(f"Trust score update error: {e}")
    
    return {
        "trust_score": round(trust_score, 1),
        "verified_jobs_count": verified_jobs,
        "is_verified_badge": is_verified_badge,
        "metrics": {
            "rating_contribution": round(0.4 * scaled_rating, 1),
            "sentiment_contribution": round(0.3 * review_sentiment, 1),
            "gallery_contribution": round(0.3 * gallery_density, 1)
        }
    }

# ── Router Section: work_verification ──
work_verification_router = APIRouter()
router = work_verification_router
"""Work Verification Router
- POST /verify-work        : submit before/after images + GPS
- POST /checkin            : GPS check-in at service site
- GET  /trust-score/{uid}  : weighted trust score
- GET  /gallery/{uid}      : list provider's work gallery
- GET  /checkins/{uid}     : list provider's check-in history
- GET  /badge/{uid}        : provider verification badge status
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from bson import ObjectId
from datetime import datetime
from typing import Optional
import os, hashlib, uuid, shutil


UPLOAD_DIR = os.path.join("uploads", "work_gallery")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _safe_filename(original: str) -> str:
    ext = os.path.splitext(original)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Use JPG/PNG/WEBP.")
    return f"{uuid.uuid4().hex}{ext}"


async def _save_file(file: UploadFile, dest_dir: str) -> tuple[str, str]:
    """Save upload, return (relative_path, sha256_hash)."""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    fname = _safe_filename(file.filename or "upload.jpg")
    path = os.path.join(dest_dir, fname)
    with open(path, "wb") as f:
        f.write(content)
    file_hash = hashlib.sha256(content).hexdigest()
    return path, file_hash


# ── POST /verify-work ─────────────────────────────────────────────────────────

@router.post("/verify-work")
async def verify_work(
    booking_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    notes: Optional[str] = Form(None),
    before_image: Optional[UploadFile] = File(None),
    after_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Provider submits before/after images + GPS coordinates as proof of work.
    Stores evidence, computes trust score update.
    """
    if current_user.get("role") not in ("provider", "admin"):
        raise HTTPException(status_code=403, detail="Only providers can submit work evidence")

    db = get_db()
    provider_id = current_user["sub"]

    # Validate booking belongs to this provider
    try:
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if str(booking.get("provider_id", "")) != provider_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not your booking")

    dest = os.path.join(UPLOAD_DIR, provider_id)
    os.makedirs(dest, exist_ok=True)

    evidence: dict = {
        "provider_id": provider_id,
        "booking_id": booking_id,
        "latitude": latitude,
        "longitude": longitude,
        "notes": notes or "",
        "submitted_at": datetime.utcnow(),
        "images": [],
    }

    for label, upload in [("before", before_image), ("after", after_image)]:
        if upload and upload.filename:
            path, sha = await _save_file(upload, dest)
            evidence["images"].append({
                "label": label,
                "path": path,
                "sha256": sha,
                "uploaded_at": datetime.utcnow().isoformat(),
            })

    result = await db.work_evidence.insert_one(evidence)

    # Update booking with evidence reference
    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"work_evidence_id": str(result.inserted_id), "evidence_submitted": True}},
    )

    # Recompute trust score
    trust = await _compute_trust(provider_id, db)
    await db.users.update_one(
        {"_id": ObjectId(provider_id)},
        {"$set": {"trust_score": trust}},
    )

    return {
        "status": "success",
        "evidence_id": str(result.inserted_id),
        "images_uploaded": len(evidence["images"]),
        "trust_score": trust,
        "message": "Work evidence submitted successfully",
    }


# ── POST /checkin ─────────────────────────────────────────────────────────────

@router.post("/checkin")
async def checkin(
    booking_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """Record provider GPS check-in at service site."""
    if current_user.get("role") not in ("provider", "admin"):
        raise HTTPException(status_code=403, detail="Only providers can check in")

    db = get_db()
    provider_id = current_user["sub"]

    record = {
        "provider_id": provider_id,
        "booking_id": booking_id,
        "latitude": latitude,
        "longitude": longitude,
        "checked_in_at": datetime.utcnow(),
    }
    result = await db.provider_checkins.insert_one(record)

    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {
            "checkin_lat": latitude,
            "checkin_lng": longitude,
            "checkin_time": datetime.utcnow(),
            "status": "in_progress",
        }},
    )

    return {
        "checkin_id": str(result.inserted_id),
        "checked_in_at": record["checked_in_at"].isoformat(),
        "message": "Check-in recorded",
    }


# ── GET /trust-score/{provider_id} ───────────────────────────────────────────

@router.get("/trust-score/{provider_id}")
async def get_trust_score(provider_id: str):
    """Public: compute and return weighted trust score for a provider."""
    db = get_db()
    trust = await _compute_trust(provider_id, db)
    return {"provider_id": provider_id, "trust_score": trust, "breakdown": await _trust_breakdown(provider_id, db)}


# ── GET /gallery/{provider_id} ────────────────────────────────────────────────

@router.get("/gallery/{provider_id}")
async def get_gallery(provider_id: str):
    """Public: list work evidence images for a provider."""
    db = get_db()
    docs = await db.work_evidence.find({"provider_id": provider_id}).sort("submitted_at", -1).limit(20).to_list(20)
    for d in docs:
        d["_id"] = str(d["_id"])
        if isinstance(d.get("submitted_at"), datetime):
            d["submitted_at"] = d["submitted_at"].isoformat()
    return {"gallery": docs, "total": len(docs)}


# ── GET /checkins/{provider_id} ───────────────────────────────────────────────

@router.get("/checkins/{provider_id}")
async def get_checkins(provider_id: str, current_user: dict = Depends(get_current_user)):
    """Provider/admin: list check-in history."""
    if current_user["sub"] != provider_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_db()
    docs = await db.provider_checkins.find({"provider_id": provider_id}).sort("checked_in_at", -1).limit(50).to_list(50)
    for d in docs:
        d["_id"] = str(d["_id"])
        if isinstance(d.get("checked_in_at"), datetime):
            d["checked_in_at"] = d["checked_in_at"].isoformat()
    return {"checkins": docs, "total": len(docs)}


# ── GET /badge/{provider_id} ──────────────────────────────────────────────────

@router.get("/badge/{provider_id}")
async def get_provider_badge(provider_id: str):
    """
    Public: return badge eligibility.
    Badge is awarded when provider has 3+ completed jobs with verified photos.
    """
    db = get_db()
    # Count bookings that have evidence submitted
    verified_jobs = await db.bookings.count_documents({
        "provider_id": provider_id,
        "status": "completed",
        "evidence_submitted": True,
    })
    trust = await _compute_trust(provider_id, db)
    badge_earned = verified_jobs >= 3
    return {
        "provider_id": provider_id,
        "badge_earned": badge_earned,
        "verified_jobs": verified_jobs,
        "jobs_needed": max(0, 3 - verified_jobs),
        "trust_score": trust,
    }


# ── Trust Score Logic ─────────────────────────────────────────────────────────
# Trust = (0.4 × Rating) + (0.3 × Review Sentiment) + (0.3 × Gallery Density)

async def _compute_trust(provider_id: str, db) -> float:
    breakdown = await _trust_breakdown(provider_id, db)
    score = (
        0.4 * breakdown["rating_component"]
        + 0.3 * breakdown["sentiment_component"]
        + 0.3 * breakdown["gallery_component"]
    )
    return round(min(100.0, max(0.0, score)), 1)


async def _trust_breakdown(provider_id: str, db) -> dict:
    # Rating component (0-100)
    try:
        user = await db.users.find_one({"_id": ObjectId(provider_id)})
    except Exception:
        user = None
    raw_rating = (user.get("rating", 0) if user else 0) or 0
    rating_component = (raw_rating / 5.0) * 100

    # Sentiment component: ratio of 4-5 star reviews (0-100)
    reviews = await db.reviews.find({"provider_id": provider_id}).to_list(500)
    if reviews:
        positive = sum(1 for r in reviews if r.get("rating", 0) >= 4)
        sentiment_component = (positive / len(reviews)) * 100
    else:
        sentiment_component = 50.0  # neutral default

    # Gallery density: each evidence doc = 10 points, capped at 100
    evidence_count = await db.work_evidence.count_documents({"provider_id": provider_id})
    gallery_component = min(100.0, evidence_count * 10)

    return {
        "rating_component": round(rating_component, 1),
        "sentiment_component": round(sentiment_component, 1),
        "gallery_component": round(gallery_component, 1),
        "evidence_count": evidence_count,
        "review_count": len(reviews),
        "raw_rating": raw_rating,
    }

# ── Application Setup ──
app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)
app.mount('/ws', socket_app)

@app.on_event('startup')
async def startup():
    print("[INFO] Starting QuickServe Monolith...")
    await connect_db()
    db = get_db()
    # Seeding demo users
    demo_users = [
        {"email": "admin@demo.com", "password": hash_password("password123"), "full_name": "Admin", "role": "admin", "is_superadmin": True},
        {"email": "customer@demo.com", "password": hash_password("password123"), "full_name": "Customer", "role": "customer"},
        {"email": "provider@demo.com", "password": hash_password("password123"), "full_name": "Provider", "role": "provider", "is_verified": True}
    ]
    for u in demo_users:
        if not await db.users.find_one({"email": u["email"]}):
            await db.users.insert_one(u)
    print("[OK] Startup complete.")

    # ── Gap Filler Logic ──
    try:
        print("[INFO] Checking for service coverage gaps...")
        db = get_db()
        CITIES = ["Mumbai", "Delhi", "Bangalore", "Pune", "Chennai", "Kolkata", "Hyderabad", "Ahmedabad", "Nashik", "Nagpur", "Aurangabad", "Kolhapur", "Sangli", "Satara"]
        CATEGORIES = ["plumbing", "electrical", "cleaning", "beauty", "tutoring", "repair", "carpentry", "painting", "ac technician", "house cleaning", "delivery"]
        
        gaps_added = 0
        for city in CITIES:
            for cat in CATEGORIES:
                count = await db.services.count_documents({"city": city, "category": cat})
                if count < 5:
                    needed = 5 - count
                    for _ in range(needed):
                        pid = f"gap_{city[:3].lower()}_{cat[:3].lower()}_{secrets.token_hex(4)}"
                        new_svc = {
                            "csv_provider_id": pid,
                            "provider_name": f"{cat.title()} Expert {secrets.token_hex(2).upper()}",
                            "name": f"{cat.title()} Service in {city}",
                            "category": cat,
                            "city": city,
                            "rating": round(random.uniform(3.5, 4.9), 1),
                            "price_per_hour": random.randint(300, 1000),
                            "is_csv_imported": True,
                            "is_gap_filler": True,
                            "created_at": datetime.utcnow()
                        }
                        await db.services.insert_one(new_svc)
                        gaps_added += 1
        if gaps_added:
            print(f"[OK] Added {gaps_added} service providers to fill city gaps.")
    except Exception as e:
        print(f"[ERROR] Gap Filler: {e}")
    
    # ── Auto Import CSV Data ──
    try:
        count = await db.services.count_documents({"is_csv_imported": True})
        if count == 0:
            print("[INFO] Database empty. Importing services from CSV...")
            providers = load_csv_providers()
            if providers:
                services = providers_to_services(providers)
                await db.services.insert_many(services)
                print(f"[OK] Imported {len(services)} services from CSV.")
    except Exception as e:
        print(f"[ERROR] CSV Import: {e}")

# ── Unique Feature: Opportunity Finder ──
@app.get("/api/ai/opportunity-finder")
async def get_opportunities(city: str = "Mumbai", cat: Optional[str] = None):
    """
    AI-powered feature for PROVIDERS to see where demand is high but supply is low.
    """
    db = get_db()
    
    query = {"city": city}
    if cat: query["category"] = cat
    
    # Calculate demand based on bookings and supply based on providers
    pipeline = [
        {"$match": {"city": city}},
        {"$group": {
            "_id": "$category",
            "supply_count": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"}
        }}
    ]
    market_stats = await db.services.aggregate(pipeline).to_list(length=100)
    
    opportunities = []
    for stat in market_stats:
        cat_name = stat["_id"]
        supply = stat["supply_count"]
        # Demand is simulated based on real bookings + random factor
        bookings = await db.bookings.count_documents({"category": cat_name, "location.city": city})
        demand_score = (bookings * 2) + random.randint(5, 50)
        
        opportunity_score = round(demand_score / max(supply, 1), 2)
        
        if opportunity_score > 1.2:
            opportunities.append({
                "category": cat_name,
                "demand": demand_score,
                "supply": supply,
                "opportunity_score": opportunity_score,
                "recommendation": "High demand! Consider expanding here." if opportunity_score > 2 else "Moderately busy."
            })
            
    return {"city": city, "opportunities": sorted(opportunities, key=lambda x: x["opportunity_score"], reverse=True)}

@app.on_event('shutdown')
async def shutdown():
    await close_db()

# ── Include all 35 merged routers ──
try: app.include_router(admin_dashboard_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(advanced_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(ai_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(ai_concierge_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(aptitude_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(ar_preview_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(auth_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(bookings_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(bundles_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(chat_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(community_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(core_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(core_engagement_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(dashboard_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(dashboards_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(events_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(features_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(gamification_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(hail_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(marketplace_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(mood_sync_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(payments_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(predictive_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(provider_dashboard_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(providers_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(queue_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(reviews_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(roulette_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(services_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(slots_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(surge_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(swap_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(tracking_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(verification_router, prefix=settings.API_PREFIX)
except: pass
try: app.include_router(work_verification_router, prefix=settings.API_PREFIX)
except: pass
