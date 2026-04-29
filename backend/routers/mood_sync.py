from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
from typing import Optional

router = APIRouter(prefix="/mood-sync", tags=["Provider Mood & Availability"])

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

from models.schemas import MoodUpdate, MoodBasedPricingRequest

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