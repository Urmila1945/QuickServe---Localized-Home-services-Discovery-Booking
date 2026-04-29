from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
import math
from typing import List, Dict

router = APIRouter(prefix="/predictive", tags=["Predictive Maintenance"])

# Service intervals and patterns
SERVICE_PATTERNS = {
    "cleaning": {"interval_days": 14, "seasonal_factor": 1.2, "usage_decay": 0.1},
    "plumbing": {"interval_days": 90, "seasonal_factor": 1.5, "usage_decay": 0.05},
    "electrical": {"interval_days": 180, "seasonal_factor": 1.1, "usage_decay": 0.03},
    "beauty": {"interval_days": 30, "seasonal_factor": 0.9, "usage_decay": 0.15},
    "fitness": {"interval_days": 7, "seasonal_factor": 0.8, "usage_decay": 0.2},
    "pest_control": {"interval_days": 120, "seasonal_factor": 2.0, "usage_decay": 0.02},
    "gardening": {"interval_days": 21, "seasonal_factor": 1.8, "usage_decay": 0.08}
}

@router.get("/predictions")
async def get_service_predictions(current_user: dict = Depends(get_current_user)):
    """Get AI-powered service predictions for user"""
    db = get_db()
    
    # Get user's booking history
    bookings = await db.bookings.find({
        "user_id": current_user["sub"],
        "status": "completed"
    }).sort("created_at", -1).to_list(length=100)
    
    predictions = []
    
    for service_type, pattern in SERVICE_PATTERNS.items():
        service_bookings = [b for b in bookings if b.get("service_type") == service_type]
        
        if len(service_bookings) >= 2:  # Need at least 2 bookings for prediction
            prediction = await calculate_service_prediction(service_type, service_bookings, pattern, db)
            if prediction:
                predictions.append(prediction)
    
    # Sort by urgency (days until predicted need)
    predictions.sort(key=lambda x: x["days_until_needed"])
    
    return {"predictions": predictions}

@router.get("/maintenance-calendar")
async def get_maintenance_calendar(current_user: dict = Depends(get_current_user)):
    """Get personalized maintenance calendar"""
    db = get_db()
    
    predictions = await get_service_predictions(current_user)
    calendar_events = []
    
    for pred in predictions["predictions"]:
        event_date = datetime.utcnow() + timedelta(days=pred["days_until_needed"])
        
        calendar_events.append({
            "date": event_date.date().isoformat(),
            "service_type": pred["service_type"],
            "title": f"{pred['service_type'].title()} Maintenance Due",
            "description": pred["reason"],
            "urgency": pred["urgency"],
            "estimated_cost": pred["estimated_cost"],
            "recommended_providers": pred.get("recommended_providers", [])
        })
    
    return {"calendar": calendar_events}

@router.post("/set-reminder")
async def set_maintenance_reminder(
    service_type: str, 
    reminder_days: int, 
    current_user: dict = Depends(get_current_user)
):
    """Set custom maintenance reminder"""
    db = get_db()
    
    reminder = {
        "user_id": current_user["sub"],
        "service_type": service_type,
        "reminder_date": datetime.utcnow() + timedelta(days=reminder_days),
        "created_at": datetime.utcnow(),
        "status": "active",
        "custom": True
    }
    
    result = await db.maintenance_reminders.insert_one(reminder)
    
    return {
        "reminder_id": str(result.inserted_id),
        "message": f"Reminder set for {service_type} in {reminder_days} days"
    }

@router.get("/health-score")
async def get_home_health_score(current_user: dict = Depends(get_current_user)):
    """Calculate overall home/service health score"""
    db = get_db()
    
    # Get recent service history
    recent_bookings = await db.bookings.find({
        "user_id": current_user["sub"],
        "created_at": {"$gte": datetime.utcnow() - timedelta(days=365)},
        "status": "completed"
    }).to_list(length=100)
    
    health_scores = {}
    overall_score = 0
    
    for service_type, pattern in SERVICE_PATTERNS.items():
        service_bookings = [b for b in recent_bookings if b.get("service_type") == service_type]
        
        if service_bookings:
            last_service = max(service_bookings, key=lambda x: x["created_at"])
            days_since = (datetime.utcnow() - last_service["created_at"]).days
            
            # Calculate health score (0-100)
            optimal_interval = pattern["interval_days"]
            if days_since <= optimal_interval:
                score = 100
            elif days_since <= optimal_interval * 1.5:
                score = 80
            elif days_since <= optimal_interval * 2:
                score = 60
            else:
                score = max(20, 100 - (days_since - optimal_interval * 2))
            
            health_scores[service_type] = {
                "score": score,
                "last_service": last_service["created_at"].date().isoformat(),
                "days_since": days_since,
                "status": "excellent" if score >= 90 else "good" if score >= 70 else "needs_attention" if score >= 50 else "urgent"
            }
        else:
            health_scores[service_type] = {
                "score": 50,  # Neutral for never used
                "last_service": None,
                "days_since": None,
                "status": "no_history"
            }
    
    # Calculate overall score
    scores = [s["score"] for s in health_scores.values() if s["score"] is not None]
    overall_score = sum(scores) / len(scores) if scores else 50
    
    return {
        "overall_score": round(overall_score, 1),
        "grade": get_health_grade(overall_score),
        "service_scores": health_scores,
        "recommendations": generate_health_recommendations(health_scores)
    }

from models.schemas import PredictiveReminder, PredictiveScheduleRequest

@router.get("/get-calendar")
async def get_maintenance_calendar(current_user: dict = Depends(get_current_user)):
    """Get personalized maintenance calendar for the next 12 months"""
    db = get_db()
    
    # Analyze history and generate predictions
    predictions = await get_service_predictions(current_user)
    
    calendar = []
    # Fill calendar for each month
    for i in range(12):
        month_date = datetime.utcnow() + timedelta(days=i * 30)
        month_name = month_date.strftime("%B %Y")
        
        # Simplified prediction check
        month_tasks = [p for p in predictions if datetime.fromisoformat(p["predicted_date"]).month == month_date.month]
        
        calendar.append({
            "month": month_name,
            "tasks": month_tasks,
            "task_count": len(month_tasks)
        })
    
    return {"calendar": calendar}

@router.post("/set-reminder")
async def set_service_reminder(data: PredictiveReminder, current_user: dict = Depends(get_current_user)):
    """Set a proactive service reminder"""
    db = get_db()
    
    reminder = {
        "user_id": current_user["sub"],
        "service_id": data.service_id,
        "reminder_date": data.date,
        "notes": data.notes,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    result = await db.predictive_reminders.insert_one(reminder)
    
    return {
        "message": "Reminder set successfully!",
        "reminder_id": str(result.inserted_id),
        "notification_scheduled": data.date
    }

@router.get("/seasonal-insights")
async def get_seasonal_insights():
    """Get seasonal service insights and recommendations"""
    current_month = datetime.utcnow().month
    
    seasonal_insights = {
        "winter": {
            "months": [12, 1, 2],
            "high_demand": ["plumbing", "electrical", "cleaning"],
            "tips": [
                "Pipe freezing prevention - schedule plumbing check",
                "Heating system maintenance",
                "Indoor air quality cleaning"
            ]
        },
        "spring": {
            "months": [3, 4, 5],
            "high_demand": ["cleaning", "gardening", "pest_control"],
            "tips": [
                "Deep spring cleaning",
                "Garden preparation and landscaping",
                "Pest prevention before summer"
            ]
        },
        "summer": {
            "months": [6, 7, 8],
            "high_demand": ["beauty", "fitness", "cleaning"],
            "tips": [
                "AC maintenance and cleaning",
                "Outdoor fitness activities",
                "Regular beauty treatments for summer"
            ]
        },
        "autumn": {
            "months": [9, 10, 11],
            "high_demand": ["plumbing", "electrical", "gardening"],
            "tips": [
                "Winter preparation for plumbing",
                "Electrical safety checks",
                "Garden winterization"
            ]
        }
    }
    
    current_season = None
    for season, data in seasonal_insights.items():
        if current_month in data["months"]:
            current_season = season
            break
    
    return {
        "current_season": current_season,
        "insights": seasonal_insights[current_season] if current_season else None,
        "all_seasons": seasonal_insights
    }

@router.post("/smart-schedule")
async def create_smart_schedule(
    data: PredictiveScheduleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create optimized service schedule based on budget and timeframe"""
    db = get_db()
    
    services = data.services
    budget = data.max_budget
    timeframe_days = 30  # Default or extract from data if added
    
    # Get service priorities and costs
    service_priorities = []
    
    for service_type in services:
        # Get average cost
        avg_cost = await get_average_service_cost(service_type, db)
        
        # Get urgency based on last booking
        last_booking = await db.bookings.find_one({
            "user_id": current_user["sub"],
            "service_type": service_type,
            "status": "completed"
        }, sort=[("created_at", -1)])
        
        urgency = 1.0
        if last_booking:
            days_since = (datetime.utcnow() - last_booking["created_at"]).days
            pattern = SERVICE_PATTERNS.get(service_type, {"interval_days": 30})
            urgency = min(2.0, days_since / pattern["interval_days"])
        
        service_priorities.append({
            "service_type": service_type,
            "cost": avg_cost,
            "urgency": urgency,
            "priority_score": urgency / avg_cost  # Higher urgency, lower cost = higher priority
        })
    
    # Sort by priority score
    service_priorities.sort(key=lambda x: x["priority_score"], reverse=True)
    
    # Create schedule within budget
    schedule = []
    remaining_budget = budget
    days_per_service = timeframe_days // len(services) if services else 1
    
    for i, service in enumerate(service_priorities):
        if remaining_budget >= service["cost"]:
            schedule_date = datetime.utcnow() + timedelta(days=i * days_per_service)
            schedule.append({
                "service_type": service["service_type"],
                "scheduled_date": schedule_date.date().isoformat(),
                "estimated_cost": service["cost"],
                "urgency": service["urgency"],
                "reason": f"Optimized scheduling based on urgency and budget"
            })
            remaining_budget -= service["cost"]
    
    return {
        "schedule": schedule,
        "total_cost": budget - remaining_budget,
        "remaining_budget": remaining_budget,
        "optimization_score": len(schedule) / len(services) * 100 if services else 0
    }

async def calculate_service_prediction(service_type: str, bookings: List[Dict], pattern: Dict, db) -> Dict:
    """Calculate when user will likely need a service next"""
    if len(bookings) < 2:
        return None
    
    # Calculate average interval between bookings
    intervals = []
    for i in range(len(bookings) - 1):
        interval = (bookings[i]["created_at"] - bookings[i + 1]["created_at"]).days
        intervals.append(interval)
    
    avg_interval = sum(intervals) / len(intervals)
    
    # Apply seasonal and usage factors
    seasonal_factor = pattern.get("seasonal_factor", 1.0)
    current_month = datetime.utcnow().month
    
    # Adjust for season (simplified)
    if current_month in [6, 7, 8] and service_type in ["beauty", "fitness"]:  # Summer
        seasonal_factor *= 1.2
    elif current_month in [12, 1, 2] and service_type in ["plumbing", "electrical"]:  # Winter
        seasonal_factor *= 1.3
    
    predicted_interval = avg_interval * seasonal_factor
    last_booking_date = bookings[0]["created_at"]
    days_since_last = (datetime.utcnow() - last_booking_date).days
    days_until_needed = max(0, predicted_interval - days_since_last)
    
    # Determine urgency
    if days_until_needed <= 3:
        urgency = "urgent"
    elif days_until_needed <= 7:
        urgency = "high"
    elif days_until_needed <= 14:
        urgency = "medium"
    else:
        urgency = "low"
    
    # Estimate cost based on historical data
    avg_cost = sum(b.get("amount", 0) for b in bookings) / len(bookings)
    
    return {
        "service_type": service_type,
        "days_until_needed": int(days_until_needed),
        "predicted_date": (datetime.utcnow() + timedelta(days=days_until_needed)).date().isoformat(),
        "confidence": min(95, len(bookings) * 20),  # More bookings = higher confidence
        "urgency": urgency,
        "reason": f"Based on your {len(bookings)} previous bookings (avg {int(avg_interval)} days apart)",
        "estimated_cost": round(avg_cost * 1.1, 2),  # Slight inflation
        "last_service": last_booking_date.date().isoformat()
    }

async def get_average_service_cost(service_type: str, db) -> float:
    """Get average cost for a service type"""
    pipeline = [
        {"$match": {"service_type": service_type, "status": "completed"}},
        {"$group": {"_id": None, "avg_cost": {"$avg": "$amount"}}}
    ]
    
    result = await db.bookings.aggregate(pipeline).to_list(length=1)
    return result[0]["avg_cost"] if result else SERVICE_PATTERNS.get(service_type, {}).get("base_cost", 500)

def get_health_grade(score: float) -> str:
    """Convert health score to letter grade"""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"

def generate_health_recommendations(health_scores: Dict) -> List[str]:
    """Generate recommendations based on health scores"""
    recommendations = []
    
    for service_type, data in health_scores.items():
        if data["status"] == "urgent":
            recommendations.append(f"🚨 Urgent: Schedule {service_type} service immediately")
        elif data["status"] == "needs_attention":
            recommendations.append(f"⚠️ Consider scheduling {service_type} service soon")
        elif data["status"] == "no_history":
            recommendations.append(f"💡 Consider trying our {service_type} services")
    
    if not recommendations:
        recommendations.append("✅ All services are up to date! Great job maintaining your home.")
    
    return recommendations