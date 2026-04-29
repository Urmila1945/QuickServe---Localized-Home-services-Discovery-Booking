from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime
from bson import ObjectId
from typing import Optional
import random

router = APIRouter(prefix="/advanced", tags=["Advanced Features"])

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
