from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict
from models.schemas import NeighborhoodBattleRequest
import random

router = APIRouter(prefix="/community", tags=["Community Challenges"])

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