from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict
from models.schemas import SwapOfferCreate, SwapRequestCreate, SwapCompleteRequest
import math

router = APIRouter(prefix="/swap", tags=["Service Swap Marketplace"])

# Service value multipliers for fair exchanges
SERVICE_VALUES = {
    "cleaning": 1.0,      # Base value
    "plumbing": 1.5,      # Higher skill = higher value
    "electrical": 1.6,
    "beauty": 1.2,
    "fitness": 1.3,
    "tutoring": 1.4,
    "cooking": 1.1,
    "gardening": 0.9,
    "pet_care": 1.0,
    "delivery": 0.8,
    "repair": 1.3,
    "photography": 1.5,
    "design": 1.7,
    "massage": 1.4
}

@router.post("/create-offer")
async def create_swap_offer(
    data: SwapOfferCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a service swap offer"""
    db = get_db()
    
    offering_service = data.offering_service
    offering_hours = data.offering_hours
    seeking_service = data.seeking_service
    seeking_hours = data.seeking_hours
    description = data.description
    location = data.location
    expires_in_days = 30  # Default or extract from data
    
    # Validate user can provide the offering service
    user = await db.users.find_one({"_id": current_user["sub"]})
    if user["role"] == "provider":
        if offering_service not in user.get("specializations", []):
            return {"error": f"You're not qualified to offer {offering_service} services"}
    
    # Calculate fair exchange ratio
    offering_value = SERVICE_VALUES.get(offering_service, 1.0) * offering_hours
    seeking_value = SERVICE_VALUES.get(seeking_service, 1.0) * seeking_hours
    
    fairness_ratio = offering_value / seeking_value if seeking_value > 0 else 0
    
    # Create swap offer
    swap_offer = {
        "user_id": current_user["sub"],
        "offering": {
            "service": offering_service,
            "hours": offering_hours,
            "value_points": offering_value
        },
        "seeking": {
            "service": seeking_service,
            "hours": seeking_hours,
            "value_points": seeking_value
        },
        "description": description,
        "location": location,
        "fairness_ratio": round(fairness_ratio, 2),
        "status": "active",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=expires_in_days),
        "views": 0,
        "interested_users": [],
        "swap_requests": []
    }
    
    result = await db.swap_offers.insert_one(swap_offer)
    
    # Find potential matches
    potential_matches = await find_swap_matches(str(result.inserted_id), db)
    
    return {
        "offer_id": str(result.inserted_id),
        "message": "Swap offer created successfully!",
        "fairness_ratio": fairness_ratio,
        "fairness_status": get_fairness_status(fairness_ratio),
        "potential_matches": len(potential_matches),
        "expires_at": swap_offer["expires_at"].isoformat()
    }

@router.get("/browse")
async def browse_swap_offers(
    seeking_service: Optional[str] = None,
    offering_service: Optional[str] = None,
    location: Optional[Dict] = None,
    max_distance_km: float = 10.0,
    min_fairness_ratio: float = 0.8,
    limit: int = 20
):
    """Browse available swap offers"""
    db = get_db()
    
    # Build query
    query = {
        "status": "active",
        "expires_at": {"$gt": datetime.utcnow()}
    }
    
    if seeking_service:
        query["offering.service"] = seeking_service
    
    if offering_service:
        query["seeking.service"] = offering_service
    
    if min_fairness_ratio:
        query["fairness_ratio"] = {"$gte": min_fairness_ratio}
    
    # Get offers
    offers = await db.swap_offers.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
    
    # Enrich with user data
    for offer in offers:
        offer["_id"] = str(offer["_id"])
        
        # Get user info
        user = await db.users.find_one({"_id": offer["user_id"]})
        if user:
            offer["user_info"] = {
                "name": user.get("full_name", "Anonymous"),
                "rating": user.get("rating", 0),
                "verified": user.get("is_verified", False),
                "reviews_count": user.get("reviews_count", 0)
            }
        
        # Calculate distance (simplified)
        if location:
            offer["distance_km"] = calculate_distance(location, offer["location"])
        
        # Calculate time remaining
        time_remaining = offer["expires_at"] - datetime.utcnow()
        offer["days_remaining"] = max(0, time_remaining.days)
        
        # Add fairness indicator
        offer["fairness_status"] = get_fairness_status(offer["fairness_ratio"])
    
    # Filter by distance if location provided
    if location:
        offers = [offer for offer in offers if offer.get("distance_km", 0) <= max_distance_km]
    
    return {"offers": offers, "total_found": len(offers)}

@router.post("/request-swap/{offer_id}")
async def request_swap(
    offer_id: str,
    data: SwapRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Request to swap services with an offer"""
    db = get_db()
    
    message = data.message
    proposed_schedule = data.proposed_schedule
    
    # Get the offer
    offer = await db.swap_offers.find_one({"_id": ObjectId(offer_id), "status": "active"})
    if not offer:
        return {"error": "Offer not found or no longer active"}
    
    # Can't swap with yourself
    if offer["user_id"] == current_user["sub"]:
        return {"error": "Cannot swap with yourself"}
    
    # Check if user can provide the sought service
    user = await db.users.find_one({"_id": current_user["sub"]})
    if user["role"] == "provider":
        if offer["seeking"]["service"] not in user.get("specializations", []):
            return {"error": f"You're not qualified to provide {offer['seeking']['service']} services"}
    
    # Check if already requested
    existing_request = await db.swap_requests.find_one({
        "offer_id": offer_id,
        "requester_id": current_user["sub"],
        "status": {"$in": ["pending", "accepted"]}
    })
    
    if existing_request:
        return {"error": "You already have a pending request for this offer"}
    
    # Create swap request
    swap_request = {
        "offer_id": offer_id,
        "offer_owner_id": offer["user_id"],
        "requester_id": current_user["sub"],
        "message": message,
        "proposed_schedule": proposed_schedule,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7)  # Request expires in 7 days
    }
    
    result = await db.swap_requests.insert_one(swap_request)
    
    # Add to offer's request list
    await db.swap_offers.update_one(
        {"_id": ObjectId(offer_id)},
        {"$push": {"swap_requests": str(result.inserted_id)}}
    )
    
    # Notify offer owner
    await db.notifications.insert_one({
        "user_id": offer["user_id"],
        "type": "swap_request",
        "title": "New Swap Request!",
        "message": f"Someone wants to swap {offer['seeking']['service']} for your {offer['offering']['service']}",
        "swap_request_id": str(result.inserted_id),
        "created_at": datetime.utcnow()
    })
    
    return {
        "request_id": str(result.inserted_id),
        "message": "Swap request sent successfully!",
        "status": "pending"
    }

@router.get("/my-offers")
async def get_my_offers(current_user: dict = Depends(get_current_user)):
    """Get user's swap offers"""
    db = get_db()
    
    offers = await db.swap_offers.find({
        "user_id": current_user["sub"]
    }).sort("created_at", -1).to_list(length=50)
    
    for offer in offers:
        offer["_id"] = str(offer["_id"])
        
        # Get pending requests count
        offer["pending_requests"] = await db.swap_requests.count_documents({
            "offer_id": str(offer["_id"]),
            "status": "pending"
        })
        
        # Get completed swaps count
        offer["completed_swaps"] = await db.swap_requests.count_documents({
            "offer_id": str(offer["_id"]),
            "status": "completed"
        })
    
    return {"my_offers": offers}

@router.get("/my-requests")
async def get_my_requests(current_user: dict = Depends(get_current_user)):
    """Get user's swap requests"""
    db = get_db()
    
    # Requests I made
    my_requests = await db.swap_requests.find({
        "requester_id": current_user["sub"]
    }).sort("created_at", -1).to_list(length=50)
    
    # Requests for my offers
    requests_for_me = await db.swap_requests.find({
        "offer_owner_id": current_user["sub"]
    }).sort("created_at", -1).to_list(length=50)
    
    # Enrich with offer data
    for request in my_requests + requests_for_me:
        request["_id"] = str(request["_id"])
        
        # Get offer details
        offer = await db.swap_offers.find_one({"_id": ObjectId(request["offer_id"])})
        if offer:
            request["offer_details"] = {
                "offering": offer["offering"],
                "seeking": offer["seeking"],
                "description": offer["description"]
            }
        
        # Get other party info
        other_user_id = request["offer_owner_id"] if request["requester_id"] == current_user["sub"] else request["requester_id"]
        other_user = await db.users.find_one({"_id": other_user_id})
        if other_user:
            request["other_party"] = {
                "name": other_user.get("full_name", "Anonymous"),
                "rating": other_user.get("rating", 0),
                "verified": other_user.get("is_verified", False)
            }
    
    return {
        "my_requests": my_requests,
        "requests_for_me": requests_for_me
    }

@router.post("/accept-request/{request_id}")
async def accept_swap_request(request_id: str, current_user: dict = Depends(get_current_user)):
    """Accept a swap request"""
    db = get_db()
    
    # Get the request
    request = await db.swap_requests.find_one({
        "_id": ObjectId(request_id),
        "offer_owner_id": current_user["sub"],
        "status": "pending"
    })
    
    if not request:
        return {"error": "Request not found or not authorized"}
    
    # Update request status
    await db.swap_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "accepted", "accepted_at": datetime.utcnow()}}
    )
    
    # Update offer status
    await db.swap_offers.update_one(
        {"_id": ObjectId(request["offer_id"])},
        {"$set": {"status": "matched"}}
    )
    
    # Create swap agreement
    agreement = {
        "request_id": request_id,
        "offer_id": request["offer_id"],
        "party_a": current_user["sub"],  # Offer owner
        "party_b": request["requester_id"],  # Requester
        "services": {
            "a_provides": None,  # Will be filled from offer
            "b_provides": None   # Will be filled from offer
        },
        "schedule": request["proposed_schedule"],
        "status": "agreed",
        "created_at": datetime.utcnow(),
        "completion_deadline": datetime.utcnow() + timedelta(days=30)
    }
    
    # Get offer details to fill services
    offer = await db.swap_offers.find_one({"_id": ObjectId(request["offer_id"])})
    if offer:
        agreement["services"]["a_provides"] = offer["offering"]
        agreement["services"]["b_provides"] = offer["seeking"]
    
    result = await db.swap_agreements.insert_one(agreement)
    
    # Notify requester
    await db.notifications.insert_one({
        "user_id": request["requester_id"],
        "type": "swap_accepted",
        "title": "Swap Request Accepted! 🎉",
        "message": "Your swap request has been accepted. Time to schedule!",
        "agreement_id": str(result.inserted_id),
        "created_at": datetime.utcnow()
    })
    
    return {
        "agreement_id": str(result.inserted_id),
        "message": "Swap request accepted! Agreement created.",
        "next_step": "Schedule the service exchange"
    }

@router.post("/complete-swap/{agreement_id}")
async def complete_swap(
    agreement_id: str,
    data: SwapCompleteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Mark swap as completed and rate the experience"""
    db = get_db()
    
    completion_proof = data.completion_proof
    rating = data.rating
    feedback = data.feedback
    
    # Get agreement
    agreement = await db.swap_agreements.find_one({
        "_id": ObjectId(agreement_id),
        "$or": [{"party_a": current_user["sub"]}, {"party_b": current_user["sub"]}],
        "status": "agreed"
    })
    
    if not agreement:
        return {"error": "Agreement not found or not authorized"}
    
    # Determine which party is completing
    completing_party = "a" if agreement["party_a"] == current_user["sub"] else "b"
    other_party = agreement["party_b"] if completing_party == "a" else agreement["party_a"]
    
    # Mark completion
    completion_field = f"completed_by_{completing_party}"
    await db.swap_agreements.update_one(
        {"_id": ObjectId(agreement_id)},
        {
            "$set": {
                completion_field: True,
                f"{completion_field}_at": datetime.utcnow(),
                f"{completion_field}_proof": completion_proof
            }
        }
    )
    
    # Check if both parties completed
    updated_agreement = await db.swap_agreements.find_one({"_id": ObjectId(agreement_id)})
    both_completed = updated_agreement.get("completed_by_a", False) and updated_agreement.get("completed_by_b", False)
    
    if both_completed:
        await db.swap_agreements.update_one(
            {"_id": ObjectId(agreement_id)},
            {"$set": {"status": "completed", "completed_at": datetime.utcnow()}}
        )
    
    # Add rating and feedback
    await db.swap_ratings.insert_one({
        "agreement_id": agreement_id,
        "rater_id": current_user["sub"],
        "rated_user_id": other_party,
        "rating": rating,
        "feedback": feedback,
        "created_at": datetime.utcnow()
    })
    
    # Update user's swap statistics
    await db.users.update_one(
        {"_id": current_user["sub"]},
        {"$inc": {"swap_stats.completed": 1, "swap_stats.total_value": updated_agreement["services"][f"{completing_party}_provides"]["value_points"]}}
    )
    
    return {
        "message": "Swap completion recorded!",
        "both_completed": both_completed,
        "status": "completed" if both_completed else "partially_completed"
    }

@router.get("/recommendations")
async def get_swap_recommendations(current_user: dict = Depends(get_current_user)):
    """Get personalized swap recommendations"""
    db = get_db()
    
    # Get user's service history to understand preferences
    user_bookings = await db.bookings.find({
        "user_id": current_user["sub"]
    }).to_list(length=100)
    
    # Analyze what services user frequently needs
    service_frequency = {}
    for booking in user_bookings:
        service = booking.get("service_type")
        service_frequency[service] = service_frequency.get(service, 0) + 1
    
    # Get user's skills (if provider)
    user = await db.users.find_one({"_id": current_user["sub"]})
    user_skills = user.get("specializations", []) if user["role"] == "provider" else []
    
    recommendations = []
    
    # Find offers where user can provide what's sought and needs what's offered
    for skill in user_skills:
        for needed_service, frequency in service_frequency.items():
            if frequency >= 2:  # Services user needs frequently
                matching_offers = await db.swap_offers.find({
                    "seeking.service": skill,
                    "offering.service": needed_service,
                    "status": "active",
                    "user_id": {"$ne": current_user["sub"]}
                }).limit(5).to_list(length=5)
                
                for offer in matching_offers:
                    offer["_id"] = str(offer["_id"])
                    offer["recommendation_reason"] = f"You can provide {skill} and frequently need {needed_service}"
                    offer["match_score"] = frequency * offer["fairness_ratio"]
                    recommendations.append(offer)
    
    # Sort by match score
    recommendations.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    
    return {"recommendations": recommendations[:10]}

@router.get("/statistics")
async def get_swap_statistics():
    """Get platform swap statistics"""
    db = get_db()
    
    # Total swaps
    total_offers = await db.swap_offers.count_documents({})
    active_offers = await db.swap_offers.count_documents({"status": "active"})
    completed_swaps = await db.swap_agreements.count_documents({"status": "completed"})
    
    # Most popular services
    popular_offering = await db.swap_offers.aggregate([
        {"$group": {"_id": "$offering.service", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    
    popular_seeking = await db.swap_offers.aggregate([
        {"$group": {"_id": "$seeking.service", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]).to_list(length=5)
    
    # Average fairness ratio
    avg_fairness = await db.swap_offers.aggregate([
        {"$group": {"_id": None, "avg_fairness": {"$avg": "$fairness_ratio"}}}
    ]).to_list(length=1)
    
    avg_fairness_ratio = avg_fairness[0]["avg_fairness"] if avg_fairness else 0
    
    return {
        "total_offers": total_offers,
        "active_offers": active_offers,
        "completed_swaps": completed_swaps,
        "success_rate": round((completed_swaps / max(total_offers, 1)) * 100, 1),
        "popular_offerings": popular_offering,
        "popular_seekings": popular_seeking,
        "average_fairness_ratio": round(avg_fairness_ratio, 2),
        "insights": [
            "Cleaning services are most commonly offered",
            "Tutoring services are most sought after",
            "Average swap completion time is 2 weeks"
        ]
    }

async def find_swap_matches(offer_id: str, db):
    """Find potential matches for a swap offer"""
    offer = await db.swap_offers.find_one({"_id": ObjectId(offer_id)})
    if not offer:
        return []
    
    # Find offers that complement this one
    matches = await db.swap_offers.find({
        "offering.service": offer["seeking"]["service"],
        "seeking.service": offer["offering"]["service"],
        "status": "active",
        "_id": {"$ne": ObjectId(offer_id)},
        "user_id": {"$ne": offer["user_id"]}
    }).limit(10).to_list(length=10)
    
    return matches

def calculate_distance(loc1: Dict, loc2: Dict) -> float:
    """Calculate distance between two locations (simplified)"""
    # In production, use proper geospatial calculations
    lat1, lng1 = loc1.get("lat", 0), loc1.get("lng", 0)
    lat2, lng2 = loc2.get("lat", 0), loc2.get("lng", 0)
    
    # Simplified distance calculation
    return abs(lat1 - lat2) + abs(lng1 - lng2)

def get_fairness_status(ratio: float) -> str:
    """Get fairness status based on ratio"""
    if ratio >= 0.9 and ratio <= 1.1:
        return "Very Fair"
    elif ratio >= 0.8 and ratio <= 1.2:
        return "Fair"
    elif ratio >= 0.7 and ratio <= 1.3:
        return "Acceptable"
    else:
        return "Unbalanced"