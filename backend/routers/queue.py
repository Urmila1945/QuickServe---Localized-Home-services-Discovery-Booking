from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
import asyncio

from models.schemas import QueueJoin, QueueSkipRequest

router = APIRouter(prefix="/queue", tags=["Smart Queue"])

@router.post("/join")
async def join_queue(data: QueueJoin, current_user: dict = Depends(get_current_user)):
    """Join service queue with smart positioning"""
    db = get_db()
    
    # Calculate position based on factors
    base_position = await db.queue.count_documents({"service_type": data.service_type, "status": "waiting"})
    
    # Priority adjustments
    position_modifier = 0
    if data.priority == "premium":
        position_modifier = -max(0, base_position // 2)  # Jump ahead
    elif data.priority == "emergency":
        position_modifier = -base_position  # Go to front
    
    final_position = max(1, base_position + 1 + position_modifier)
    
    queue_entry = {
        "user_id": current_user["sub"],
        "service_type": data.service_type,
        "priority": data.priority,
        "position": final_position,
        "status": "waiting",
        "joined_at": datetime.utcnow(),
        "estimated_wait": final_position * 15  # 15 min per position
    }
    
    result = await db.queue.insert_one(queue_entry)
    
    # Update positions of others if priority user
    if data.priority in ["premium", "emergency"]:
        await db.queue.update_many(
            {"service_type": data.service_type, "position": {"$gte": final_position}, "_id": {"$ne": result.inserted_id}},
            {"$inc": {"position": 1, "estimated_wait": 15}}
        )
    
    return {
        "queue_id": str(result.inserted_id),
        "position": final_position,
        "estimated_wait_minutes": queue_entry["estimated_wait"],
        "ahead_of_you": final_position - 1
    }

@router.get("/status/{queue_id}")
async def get_queue_status(queue_id: str):
    """Get real-time queue status"""
    db = get_db()
    entry = await db.queue.find_one({"_id": ObjectId(queue_id)})
    if not entry:
        return {"error": "Queue entry not found"}
    
    # Get current position (may have changed)
    current_position = await db.queue.count_documents({
        "service_type": entry["service_type"],
        "status": "waiting",
        "joined_at": {"$lt": entry["joined_at"]}
    }) + 1
    
    return {
        "position": current_position,
        "estimated_wait": current_position * 15,
        "status": entry["status"],
        "service_type": entry["service_type"]
    }

@router.post("/skip/{queue_id}")
async def skip_queue_position(queue_id: str, data: QueueSkipRequest, current_user: dict = Depends(get_current_user)):
    """Pay to skip queue positions"""
    db = get_db()
    
    payment_amount = data.payment_amount
    if payment_amount < 50:  # Minimum ₹50 to skip
        return {"error": "Minimum ₹50 required to skip"}
    
    positions_to_skip = min(5, payment_amount // 50)  # ₹50 per position
    
    await db.queue.update_one(
        {"_id": ObjectId(queue_id)},
        {"$inc": {"position": -positions_to_skip, "estimated_wait": -positions_to_skip * 15}}
    )
    
    return {"positions_skipped": positions_to_skip, "amount_charged": payment_amount}

@router.get("/analytics")
async def queue_analytics(current_user: dict = Depends(get_current_user)):
    """Queue analytics for admin"""
    if current_user["role"] != "admin":
        return {"error": "Admin access required"}
    
    db = get_db()
    
    # Average wait times by service
    pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$service_type",
            "avg_wait": {"$avg": {"$subtract": ["$served_at", "$joined_at"]}},
            "total_served": {"$sum": 1}
        }}
    ]
    
    stats = await db.queue.aggregate(pipeline).to_list(length=20)
    
    return {"queue_stats": stats}