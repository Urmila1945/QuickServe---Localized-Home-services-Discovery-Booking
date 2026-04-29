from fastapi import APIRouter, Depends, HTTPException
from database.connection import get_db
from middleware.auth import get_current_user, check_role
from datetime import datetime, timedelta
from bson import ObjectId
import random

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

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
