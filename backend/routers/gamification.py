from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
import random

router = APIRouter(prefix="/gamification", tags=["Gamification"])

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

from models.schemas import GamificationProgressUpdate

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