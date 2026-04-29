from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional
from datetime import datetime, timedelta
from database.connection import get_db
from middleware.auth import get_current_user
from bson import ObjectId
import random

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

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
        }
    }

@router.get("/bookings")
async def get_all_bookings_admin(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(verify_admin)
):
    """Return all bookings with enriched customer & provider info."""
    db = get_db()
    skip = (page - 1) * limit

    query: dict = {}
    if status:
        query["status"] = status

    total = await db.bookings.count_documents(query)
    raw = await db.bookings.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)

    bookings = []
    for b in raw:
        b["_id"] = str(b["_id"])

        # Enrich customer
        uid = str(b.get("user_id") or b.get("customer_id") or "")
        customer = None
        try:
            customer = await db.users.find_one({"_id": ObjectId(uid)}) if len(uid) == 24 else None
        except Exception:
            pass

        # Enrich provider
        prov_id = str(b.get("provider_id") or "")
        provider = None
        try:
            provider = await db.users.find_one({"_id": ObjectId(prov_id)}) if len(prov_id) == 24 else None
        except Exception:
            pass

        # Enrich payment
        payment = await db.payments.find_one({"booking_id": b["_id"]})

        b["customer_name"]  = customer.get("full_name") if customer else b.get("customer_name", "Customer")
        b["customer_email"] = customer.get("email")    if customer else ""
        b["customer_phone"] = customer.get("phone")    if customer else ""
        b["customer_credits"] = customer.get("quickserve_credits", 0) if customer else 0

        b["provider_name"]   = provider.get("full_name") if provider else b.get("provider_name", "Provider")
        b["provider_email"]  = provider.get("email")     if provider else ""
        b["provider_phone"]  = provider.get("phone")     if provider else ""
        b["provider_rating"] = provider.get("rating", 0) if provider else 0
        b["provider_verified"] = provider.get("verified_by_admin", False) if provider else False

        if payment:
            b["payment_status"]   = payment.get("status", "unpaid")
            b["payment_method"]   = payment.get("payment_method", "")
            b["final_amount"]     = payment.get("final_amount", 0)
            b["gst_amount"]       = payment.get("gst_amount", 0)
            b["discount_amount"]  = payment.get("discount_amount", 0)
            b["platform_fee"]     = payment.get("platform_fee", 0)
            b["escrow_status"]    = payment.get("escrow_status", "")
            b["provider_payout"]  = payment.get("provider_payout", 0)
        else:
            b["payment_status"]   = "unpaid"
            b["final_amount"]     = b.get("final_price") or b.get("amount") or 0

        bookings.append(b)

    return {
        "bookings": bookings,
        "total":    total,
        "page":     page,
        "pages":    (total + limit - 1) // limit,
    }

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
    payload: dict = Body(...),
    admin: dict = Depends(verify_admin)
):
    """
    Grant reward to a user by email.
    Body: { email, amount, type (credits/points/discount), reason }
    """
    db = get_db()
    email = payload.get("email", "")
    amount = int(payload.get("amount", 0))
    reward_type = payload.get("type", payload.get("reward_type", "credits"))
    reason = payload.get("reason", "Admin reward")

    if not email:
        raise HTTPException(400, "Email is required")
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(404, f"User with email '{email}' not found")

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

    new_balance = (user.get("quickserve_credits", 0) + amount) if reward_type == "credits" else None
    return {"success": True, "new_balance": new_balance, "user": user.get("full_name", email)}

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
@router.post("/rewards/grant-by-id")
async def grant_reward_by_id(
    user_id: str,
    reward_type: str,  # credits, badge, discount
    amount: float,
    reason: str,
    admin: dict = Depends(verify_admin)
):
    """Grant reward to a user by their user_id (for internal admin use)."""
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

    data = []

    if period == "daily":
        # Last 30 days from aggregation
        pipeline = [
            {"$match": {"status": "completed"}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$ifNull": ["$completed_at", "$created_at"]}}},
                "revenue": {"$sum": "$amount"},
                "bookings": {"$sum": 1}
            }},
            {"$sort": {"_id": -1}},
            {"$limit": 30}
        ]
        raw = await db.bookings.aggregate(pipeline).to_list(length=30)
        data = [{"date": r["_id"], "revenue": r["revenue"], "bookings": r["bookings"], "commission": round(r["revenue"] * 0.15, 2)} for r in raw]
        data.reverse()

    elif period == "weekly":
        pipeline = [
            {"$match": {"status": "completed"}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-W%U", "date": {"$ifNull": ["$completed_at", "$created_at"]}}},
                "revenue": {"$sum": "$amount"},
                "bookings": {"$sum": 1}
            }},
            {"$sort": {"_id": -1}},
            {"$limit": 12}
        ]
        raw = await db.bookings.aggregate(pipeline).to_list(length=12)
        data = [{"date": r["_id"], "revenue": r["revenue"], "bookings": r["bookings"], "commission": round(r["revenue"] * 0.15, 2)} for r in raw]
        data.reverse()

    else:  # monthly (default)
        pipeline = [
            {"$match": {"status": "completed"}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m", "date": {"$ifNull": ["$completed_at", "$created_at"]}}},
                "revenue": {"$sum": "$amount"},
                "bookings": {"$sum": 1}
            }},
            {"$sort": {"_id": -1}},
            {"$limit": 12}
        ]
        raw = await db.bookings.aggregate(pipeline).to_list(length=12)
        data = [{"date": r["_id"], "revenue": r["revenue"], "bookings": r["bookings"], "commission": round(r["revenue"] * 0.15, 2)} for r in raw]
        data.reverse()

    # If no data for the period, return at least one zero entry
    if not data:
        data = [{"date": datetime.utcnow().strftime("%Y-%m"), "revenue": 0, "bookings": 0, "commission": 0}]

    return {"period": period, "data": data}

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


# ── Login Activity ──────────────────────────────────────────────────────────
@router.get("/login-activity")
async def get_login_activity(
    page: int = 1,
    limit: int = 50,
    role: Optional[str] = None,
    status: Optional[str] = None,
    admin: dict = Depends(verify_admin)
):
    """Return paginated login history from the login_activity collection."""
    db = get_db()
    query: dict = {}
    if role:
        query["role"] = role
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    total = await db.login_activity.count_documents(query)
    raw = await db.login_activity.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)

    logs = []
    for item in raw:
        item["_id"] = str(item["_id"])
        ts = item.get("timestamp")
        item["timestamp_str"] = ts.strftime("%Y-%m-%d %H:%M:%S UTC") if ts else ""
        logs.append(item)

    # Summary counts
    total_logins   = await db.login_activity.count_documents({"status": "success"})
    failed_logins  = await db.login_activity.count_documents({"status": "failed"})
    customer_logins = await db.login_activity.count_documents({"role": "customer", "status": "success"})
    provider_logins = await db.login_activity.count_documents({"role": "provider", "status": "success"})
    admin_logins    = await db.login_activity.count_documents({"role": "admin",    "status": "success"})

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "summary": {
            "total_logins":     total_logins,
            "failed_logins":    failed_logins,
            "customer_logins":  customer_logins,
            "provider_logins":  provider_logins,
            "admin_logins":     admin_logins,
        }
    }


# ── Full User Detail + Activity ─────────────────────────────────────────────
@router.get("/users/{user_id}/full")
async def get_full_user_profile(user_id: str, admin: dict = Depends(verify_admin)):
    """Return complete profile: user details, bookings, payments, reviews, login history."""
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    user.pop("password_hash", None)

    role = user.get("role", "customer")

    # Bookings
    if role == "customer":
        bookings_raw = await db.bookings.find({"user_id": user_id}).sort("created_at", -1).limit(50).to_list(50)
    else:
        bookings_raw = await db.bookings.find({"provider_id": user_id}).sort("created_at", -1).limit(50).to_list(50)

    bookings = []
    for b in bookings_raw:
        b["_id"] = str(b["_id"])
        payment = await db.payments.find_one({"booking_id": b["_id"]})
        if payment:
            b["payment_status"] = payment.get("status", "unpaid")
            b["final_amount"]   = payment.get("final_amount", 0)
        bookings.append(b)

    # Payments / transactions
    if role == "customer":
        payments_raw = await db.payments.find({"user_id": user_id}).sort("created_at", -1).limit(50).to_list(50)
    else:
        payments_raw = await db.payments.find({"provider_id": user_id}).sort("created_at", -1).limit(50).to_list(50)
    payments = []
    for p in payments_raw:
        p["_id"] = str(p["_id"])
        payments.append(p)

    # Reviews
    if role == "customer":
        reviews_raw = await db.reviews.find({"user_id": user_id}).sort("created_at", -1).limit(20).to_list(20)
    else:
        reviews_raw = await db.reviews.find({"provider_id": user_id}).sort("created_at", -1).limit(20).to_list(20)
    reviews = []
    for r in reviews_raw:
        r["_id"] = str(r["_id"])
        reviews.append(r)

    # Login activity
    login_logs = await db.login_activity.find({"user_id": user_id}).sort("timestamp", -1).limit(20).to_list(20)
    for l in login_logs:
        l["_id"] = str(l["_id"])
        ts = l.get("timestamp")
        l["timestamp_str"] = ts.strftime("%Y-%m-%d %H:%M:%S UTC") if ts else ""

    # Aggregate stats
    total_spent = sum(b.get("final_amount") or b.get("amount") or 0 for b in bookings if b.get("status") == "completed")
    total_bookings_count = len(bookings)
    completed_count = sum(1 for b in bookings if b.get("status") == "completed")

    return {
        "user": user,
        "bookings": bookings,
        "payments": payments,
        "reviews": reviews,
        "login_history": login_logs,
        "stats": {
            "total_bookings": total_bookings_count,
            "completed_bookings": completed_count,
            "total_spent_earned": round(total_spent, 2),
            "login_count": len(login_logs),
        }
    }
