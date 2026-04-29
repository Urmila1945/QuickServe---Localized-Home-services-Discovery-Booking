from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict
from models.schemas import RouletteSpin
import random

router = APIRouter(prefix="/roulette", tags=["Service Roulette & Discovery"])

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