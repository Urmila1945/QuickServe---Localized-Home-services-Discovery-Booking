from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
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

@notifications_router.delete("/{notification_id}")
async def delete_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.notifications.delete_one({"_id": ObjectId(notification_id), "user_id": current_user["sub"]})
    return {"status": "deleted"}

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
