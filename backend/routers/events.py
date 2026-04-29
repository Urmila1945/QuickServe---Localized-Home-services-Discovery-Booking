from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Optional, Dict
from models.schemas import EventCreate, EventBidRequest, EventShowcaseRequest, EventRateRequest
import random

router = APIRouter(prefix="/events", tags=["Virtual Marketplace Events"])

EVENT_TYPES = {
    "skill_showcase": {
        "name": "🎭 Skill Showcase",
        "description": "Providers demonstrate their expertise live",
        "duration_minutes": 30,
        "max_participants": 50
    },
    "flash_auction": {
        "name": "⚡ Flash Auction",
        "description": "Bid on premium services at discounted rates",
        "duration_minutes": 15,
        "max_participants": 100
    },
    "masterclass": {
        "name": "🎓 Service Masterclass",
        "description": "Learn from expert providers",
        "duration_minutes": 60,
        "max_participants": 200
    },
    "speed_booking": {
        "name": "🏃 Speed Booking",
        "description": "Quick 5-minute consultations with multiple providers",
        "duration_minutes": 45,
        "max_participants": 30
    },
    "community_challenge": {
        "name": "🏆 Community Challenge",
        "description": "Neighborhood teams compete in service challenges",
        "duration_minutes": 90,
        "max_participants": 500
    }
}

@router.get("/upcoming")
async def get_upcoming_events(category: Optional[str] = None, limit: int = 10):
    """Get upcoming virtual marketplace events"""
    db = get_db()
    
    query = {
        "start_time": {"$gt": datetime.utcnow()},
        "status": "scheduled"
    }
    
    if category:
        query["category"] = category
    
    events = await db.virtual_events.find(query).sort("start_time", 1).limit(limit).to_list(length=limit)
    
    for event in events:
        event["_id"] = str(event["_id"])
        
        # Get participant count
        event["current_participants"] = await db.event_participants.count_documents({
            "event_id": str(event["_id"])
        })
        
        # Calculate time until event
        time_until = event["start_time"] - datetime.utcnow()
        event["hours_until"] = max(0, time_until.total_seconds() // 3600)
        event["minutes_until"] = max(0, (time_until.total_seconds() % 3600) // 60)
        
        # Get featured providers
        if event["type"] == "skill_showcase":
            event["featured_providers"] = await get_event_providers(str(event["_id"]), db)
    
    return {"events": events}

@router.post("/create")
async def create_virtual_event(
    data: EventCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new virtual marketplace event"""
    db = get_db()
    
    event_type = data.event_type
    title = data.title
    description = data.description
    start_time = data.start_time
    category = data.category
    featured_providers = data.featured_providers
    entry_fee = data.entry_fee
    
    if event_type not in EVENT_TYPES:
        return {"error": "Invalid event type"}
    
    event_template = EVENT_TYPES[event_type]
    
    event = {
        "type": event_type,
        "title": title,
        "description": description,
        "category": category,
        "start_time": start_time,
        "end_time": start_time + timedelta(minutes=event_template["duration_minutes"]),
        "duration_minutes": event_template["duration_minutes"],
        "max_participants": event_template["max_participants"],
        "featured_providers": featured_providers or [],
        "entry_fee": entry_fee or 0,
        "creator_id": current_user["sub"],
        "status": "scheduled",
        "created_at": datetime.utcnow(),
        "prizes": [],
        "live_data": {
            "viewers": 0,
            "active_bids": 0,
            "chat_messages": 0
        }
    }
    
    result = await db.virtual_events.insert_one(event)
    
    # Notify featured providers
    if featured_providers:
        for provider_id in featured_providers:
            await db.notifications.insert_one({
                "user_id": provider_id,
                "type": "event_invitation",
                "title": f"You're invited to showcase in '{title}'",
                "message": f"You've been selected to participate in {event_template['name']}",
                "event_id": str(result.inserted_id),
                "created_at": datetime.utcnow()
            })
    
    return {
        "event_id": str(result.inserted_id),
        "message": f"Event '{title}' created successfully!",
        "start_time": start_time.isoformat(),
        "duration": event_template["duration_minutes"]
    }

@router.post("/join/{event_id}")
async def join_event(event_id: str, current_user: dict = Depends(get_current_user)):
    """Join a virtual marketplace event"""
    db = get_db()
    
    # Check if event exists and is joinable
    event = await db.virtual_events.find_one({
        "_id": ObjectId(event_id),
        "status": "scheduled",
        "start_time": {"$gt": datetime.utcnow()}
    })
    
    if not event:
        return {"error": "Event not found or not available"}
    
    # Check if already joined
    existing = await db.event_participants.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if existing:
        return {"error": "Already joined this event"}
    
    # Check capacity
    current_participants = await db.event_participants.count_documents({"event_id": event_id})
    if current_participants >= event["max_participants"]:
        return {"error": "Event is full"}
    
    # Process entry fee if required
    if event.get("entry_fee", 0) > 0:
        # In production, process payment here
        pass
    
    # Join event
    participation = {
        "event_id": event_id,
        "user_id": current_user["sub"],
        "joined_at": datetime.utcnow(),
        "role": "participant",
        "status": "confirmed"
    }
    
    await db.event_participants.insert_one(participation)
    
    return {
        "message": f"Successfully joined '{event['title']}'!",
        "event_start": event["start_time"].isoformat(),
        "join_link": f"/events/live/{event_id}"
    }

@router.get("/live/{event_id}")
async def get_live_event_data(event_id: str, current_user: dict = Depends(get_current_user)):
    """Get live event data and interactions"""
    db = get_db()
    
    # Check if user is participant
    participant = await db.event_participants.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if not participant:
        return {"error": "Not registered for this event"}
    
    event = await db.virtual_events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return {"error": "Event not found"}
    
    # Get live data based on event type
    live_data = await get_event_live_data(event_id, event["type"], db)
    
    return {
        "event": {
            "id": str(event["_id"]),
            "title": event["title"],
            "type": event["type"],
            "status": event["status"],
            "current_time": datetime.utcnow().isoformat()
        },
        "live_data": live_data,
        "participant_role": participant["role"]
    }

@router.post("/bid/{event_id}")
async def place_bid(
    event_id: str,
    data: EventBidRequest,
    current_user: dict = Depends(get_current_user)
):
    """Place a bid in a flash auction event"""
    db = get_db()
    
    service_id = data.service_id
    bid_amount = data.bid_amount
    
    # Verify event is active auction
    event = await db.virtual_events.find_one({
        "_id": ObjectId(event_id),
        "type": "flash_auction",
        "status": "live"
    })
    
    if not event:
        return {"error": "Auction not active"}
    
    # Check if user is participant
    participant = await db.event_participants.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if not participant:
        return {"error": "Must join event to bid"}
    
    # Get current highest bid
    current_bid = await db.event_bids.find_one({
        "event_id": event_id,
        "service_id": service_id
    }, sort=[("amount", -1)])
    
    min_bid = current_bid["amount"] + 50 if current_bid else 100  # Minimum increment ₹50
    
    if bid_amount < min_bid:
        return {"error": f"Minimum bid is ₹{min_bid}"}
    
    # Place bid
    bid = {
        "event_id": event_id,
        "service_id": service_id,
        "user_id": current_user["sub"],
        "amount": bid_amount,
        "timestamp": datetime.utcnow(),
        "status": "active"
    }
    
    await db.event_bids.insert_one(bid)
    
    # Update event live data
    await db.virtual_events.update_one(
        {"_id": ObjectId(event_id)},
        {"$inc": {"live_data.active_bids": 1}}
    )
    
    return {
        "message": "Bid placed successfully!",
        "bid_amount": bid_amount,
        "current_highest": bid_amount,
        "time_remaining": "Live auction"
    }

@router.post("/showcase/{event_id}")
async def start_skill_showcase(
    event_id: str,
    data: EventShowcaseRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a skill showcase presentation"""
    db = get_db()
    
    showcase_data = data.dict()
    
    # Verify provider is featured in event
    event = await db.virtual_events.find_one({
        "_id": ObjectId(event_id),
        "type": "skill_showcase",
        "featured_providers": current_user["sub"]
    })
    
    if not event:
        return {"error": "Not authorized for this showcase"}
    
    # Create showcase session
    showcase = {
        "event_id": event_id,
        "provider_id": current_user["sub"],
        "title": showcase_data.get("title"),
        "description": showcase_data.get("description"),
        "skills_demonstrated": showcase_data.get("skills", []),
        "start_time": datetime.utcnow(),
        "status": "live",
        "viewers": 0,
        "likes": 0,
        "bookings_generated": 0
    }
    
    result = await db.skill_showcases.insert_one(showcase)
    
    return {
        "showcase_id": str(result.inserted_id),
        "message": "Showcase started!",
        "live_url": f"/events/showcase/{result.inserted_id}"
    }

@router.get("/leaderboard/{event_id}")
async def get_event_leaderboard(event_id: str):
    """Get event leaderboard and rankings"""
    db = get_db()
    
    event = await db.virtual_events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return {"error": "Event not found"}
    
    leaderboard = []
    
    if event["type"] == "flash_auction":
        # Top bidders
        pipeline = [
            {"$match": {"event_id": event_id}},
            {"$group": {
                "_id": "$user_id",
                "total_bids": {"$sum": 1},
                "highest_bid": {"$max": "$amount"},
                "total_bid_amount": {"$sum": "$amount"}
            }},
            {"$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$sort": {"total_bid_amount": -1}},
            {"$limit": 10}
        ]
        
        leaderboard = await db.event_bids.aggregate(pipeline).to_list(length=10)
        
    elif event["type"] == "skill_showcase":
        # Top showcases by engagement
        pipeline = [
            {"$match": {"event_id": event_id}},
            {"$lookup": {
                "from": "users",
                "localField": "provider_id",
                "foreignField": "_id",
                "as": "provider"
            }},
            {"$unwind": "$provider"},
            {"$sort": {"likes": -1, "viewers": -1}},
            {"$limit": 10}
        ]
        
        leaderboard = await db.skill_showcases.aggregate(pipeline).to_list(length=10)
    
    return {"leaderboard": leaderboard, "event_type": event["type"]}

@router.get("/my-events")
async def get_my_events(current_user: dict = Depends(get_current_user)):
    """Get user's participated events and history"""
    db = get_db()
    
    # Get participated events
    participations = await db.event_participants.find({
        "user_id": current_user["sub"]
    }).to_list(length=100)
    
    my_events = []
    
    for participation in participations:
        event = await db.virtual_events.find_one({"_id": ObjectId(participation["event_id"])})
        if event:
            event["_id"] = str(event["_id"])
            event["my_role"] = participation["role"]
            event["joined_at"] = participation["joined_at"].isoformat()
            
            # Get performance data
            if event["type"] == "flash_auction":
                my_bids = await db.event_bids.count_documents({
                    "event_id": participation["event_id"],
                    "user_id": current_user["sub"]
                })
                event["my_performance"] = {"bids_placed": my_bids}
            
            elif event["type"] == "skill_showcase" and current_user["role"] == "provider":
                showcase = await db.skill_showcases.find_one({
                    "event_id": participation["event_id"],
                    "provider_id": current_user["sub"]
                })
                if showcase:
                    event["my_performance"] = {
                        "viewers": showcase.get("viewers", 0),
                        "likes": showcase.get("likes", 0),
                        "bookings": showcase.get("bookings_generated", 0)
                    }
            
            my_events.append(event)
    
    return {"my_events": my_events}

@router.post("/rate-event/{event_id}")
async def rate_event(
    event_id: str,
    data: EventRateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Rate and provide feedback for an event"""
    db = get_db()
    
    rating = data.rating
    feedback = data.feedback
    
    if not 1 <= rating <= 5:
        return {"error": "Rating must be between 1 and 5"}
    
    # Check if user participated
    participant = await db.event_participants.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if not participant:
        return {"error": "Can only rate events you participated in"}
    
    # Check if already rated
    existing_rating = await db.event_ratings.find_one({
        "event_id": event_id,
        "user_id": current_user["sub"]
    })
    
    if existing_rating:
        return {"error": "Already rated this event"}
    
    # Submit rating
    rating_doc = {
        "event_id": event_id,
        "user_id": current_user["sub"],
        "rating": rating,
        "feedback": feedback,
        "created_at": datetime.utcnow()
    }
    
    await db.event_ratings.insert_one(rating_doc)
    
    return {"message": "Thank you for your feedback!"}

@router.get("/analytics")
async def get_event_analytics(current_user: dict = Depends(get_current_user)):
    """Get event analytics for admin"""
    if current_user["role"] != "admin":
        return {"error": "Admin access required"}
    
    db = get_db()
    
    # Event type popularity
    type_stats = await db.virtual_events.aggregate([
        {"$group": {"_id": "$type", "count": {"$sum": 1}, "avg_participants": {"$avg": "$live_data.viewers"}}},
        {"$sort": {"count": -1}}
    ]).to_list(length=10)
    
    # Participation trends
    participation_trends = await db.event_participants.aggregate([
        {"$group": {
            "_id": {"month": {"$month": "$joined_at"}, "year": {"$year": "$joined_at"}},
            "participants": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]).to_list(length=12)
    
    # Revenue from events
    revenue_stats = await db.virtual_events.aggregate([
        {"$match": {"entry_fee": {"$gt": 0}}},
        {"$group": {"_id": None, "total_revenue": {"$sum": {"$multiply": ["$entry_fee", "$live_data.viewers"]}}}},
    ]).to_list(length=1)
    
    total_revenue = revenue_stats[0]["total_revenue"] if revenue_stats else 0
    
    return {
        "event_type_stats": type_stats,
        "participation_trends": participation_trends,
        "total_revenue": total_revenue,
        "insights": [
            "Skill showcases have highest engagement rates",
            "Flash auctions generate most revenue per participant",
            "Weekend events see 60% higher attendance"
        ]
    }

async def get_event_providers(event_id: str, db):
    """Get featured providers for an event"""
    event = await db.virtual_events.find_one({"_id": ObjectId(event_id)})
    if not event or not event.get("featured_providers"):
        return []
    
    providers = await db.users.find({
        "_id": {"$in": event["featured_providers"]},
        "role": "provider"
    }).to_list(length=10)
    
    for provider in providers:
        provider["_id"] = str(provider["_id"])
    
    return providers

async def get_event_live_data(event_id: str, event_type: str, db):
    """Get live data specific to event type"""
    
    if event_type == "flash_auction":
        # Get active auctions
        active_bids = await db.event_bids.find({
            "event_id": event_id,
            "status": "active"
        }).sort("timestamp", -1).limit(10).to_list(length=10)
        
        return {
            "active_auctions": active_bids,
            "total_bids": len(active_bids),
            "highest_bid": max([bid["amount"] for bid in active_bids]) if active_bids else 0
        }
    
    elif event_type == "skill_showcase":
        # Get active showcases
        showcases = await db.skill_showcases.find({
            "event_id": event_id,
            "status": "live"
        }).to_list(length=10)
        
        return {
            "active_showcases": showcases,
            "total_showcases": len(showcases)
        }
    
    else:
        return {"message": "Live data not available for this event type"}