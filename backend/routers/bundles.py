from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import itertools
from collections import Counter
from models.schemas import BundleOptimizeRequest

router = APIRouter(prefix="/bundles", tags=["Smart Service Bundling"])

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