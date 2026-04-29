from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from bson import ObjectId
from database.connection import get_db
from middleware.auth import get_current_user
import random
import uuid

router = APIRouter(tags=["AI, Social & Smart Features"])

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
