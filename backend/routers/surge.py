from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
import requests
import math

from models.schemas import SurgeCalculation, PriceDropNotificationRequest

router = APIRouter(prefix="/surge", tags=["Dynamic Pricing"])

@router.post("/calculate")
async def calculate_surge_pricing(data: SurgeCalculation):
    """Calculate dynamic surge pricing based on multiple factors"""
    db = get_db()
    
    base_price = {
        "plumbing": 500,
        "electrical": 600,
        "cleaning": 300,
        "beauty": 400,
        "fitness": 800,
        "delivery": 100,
        "repair": 450
    }.get(data.service_type, 400)
    
    surge_multiplier = 1.0
    factors = []
    
    # 1. Demand Factor (based on current bookings)
    current_hour = datetime.utcnow().hour
    recent_bookings = await db.bookings.count_documents({
        "created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)},
        "service_type": data.service_type
    })
    
    if recent_bookings > 10:
        demand_surge = 1.3
        factors.append({"factor": "High Demand", "multiplier": 1.3})
    elif recent_bookings > 5:
        demand_surge = 1.15
        factors.append({"factor": "Medium Demand", "multiplier": 1.15})
    else:
        demand_surge = 1.0
    
    surge_multiplier *= demand_surge
    
    # 2. Time-based Factor
    if 18 <= current_hour <= 21:  # Peak evening hours
        time_surge = 1.25
        factors.append({"factor": "Peak Hours", "multiplier": 1.25})
    elif current_hour < 8 or current_hour > 22:  # Early morning/late night
        time_surge = 1.4
        factors.append({"factor": "Off Hours Premium", "multiplier": 1.4})
    else:
        time_surge = 1.0
    
    surge_multiplier *= time_surge
    
    # 3. Weather Factor (mock weather API)
    try:
        # In production, use actual weather API
        weather_conditions = ["sunny", "rainy", "stormy", "cloudy"][datetime.utcnow().day % 4]
        
        if weather_conditions == "stormy" and data.service_type in ["plumbing", "electrical"]:
            weather_surge = 1.5
            factors.append({"factor": "Storm Emergency", "multiplier": 1.5})
        elif weather_conditions == "rainy" and data.service_type == "delivery":
            weather_surge = 1.3
            factors.append({"factor": "Rain Surcharge", "multiplier": 1.3})
        else:
            weather_surge = 1.0
        
        surge_multiplier *= weather_surge
    except:
        pass
    
    # 4. Provider Availability Factor
    available_providers = await db.users.count_documents({
        "role": "provider",
        "specializations": data.service_type,
        "is_online": True
    })
    
    total_providers = await db.users.count_documents({
        "role": "provider",
        "specializations": data.service_type
    })
    
    availability_ratio = available_providers / max(total_providers, 1)
    
    if availability_ratio < 0.3:  # Less than 30% available
        availability_surge = 1.6
        factors.append({"factor": "Low Provider Availability", "multiplier": 1.6})
    elif availability_ratio < 0.5:  # Less than 50% available
        availability_surge = 1.2
        factors.append({"factor": "Limited Availability", "multiplier": 1.2})
    else:
        availability_surge = 1.0
    
    surge_multiplier *= availability_surge
    
    # 5. Urgency Factor
    if data.urgency == "emergency":
        urgency_surge = 1.8
        factors.append({"factor": "Emergency Service", "multiplier": 1.8})
    elif data.urgency == "urgent":
        urgency_surge = 1.3
        factors.append({"factor": "Urgent Request", "multiplier": 1.3})
    else:
        urgency_surge = 1.0
    
    surge_multiplier *= urgency_surge
    
    # 6. Day of Week Factor
    day_of_week = datetime.utcnow().weekday()
    if day_of_week >= 5:  # Weekend
        weekend_surge = 1.15
        factors.append({"factor": "Weekend Premium", "multiplier": 1.15})
        surge_multiplier *= weekend_surge
    
    # Cap the surge at 3x
    surge_multiplier = min(surge_multiplier, 3.0)
    
    final_price = round(base_price * surge_multiplier, 2)
    
    return {
        "service_type": data.service_type,
        "base_price": base_price,
        "surge_multiplier": round(surge_multiplier, 2),
        "final_price": final_price,
        "factors": factors,
        "savings_tip": "Book during off-peak hours (9 AM - 5 PM) for lower prices" if surge_multiplier > 1.2 else None
    }

@router.get("/predictions")
async def get_price_predictions(service_type: str = "cleaning"):
    """Predict pricing for next 24 hours"""
    predictions = []
    
    for hour in range(24):
        future_time = datetime.utcnow() + timedelta(hours=hour)
        
        # Simulate demand patterns
        if 8 <= future_time.hour <= 18:
            demand_level = "medium"
            multiplier = 1.1
        elif 18 <= future_time.hour <= 21:
            demand_level = "high"
            multiplier = 1.3
        else:
            demand_level = "low"
            multiplier = 0.9
        
        base_price = {"plumbing": 500, "electrical": 600, "cleaning": 300}.get(service_type, 400)
        predicted_price = round(base_price * multiplier, 2)
        
        predictions.append({
            "hour": future_time.hour,
            "date": future_time.date().isoformat(),
            "demand_level": demand_level,
            "predicted_price": predicted_price,
            "multiplier": multiplier
        })
    
    return {"predictions": predictions}

@router.get("/surge-map")
async def get_surge_map():
    """Get surge pricing heatmap for different areas"""
    # Mock data for different areas
    areas = [
        {"area": "Downtown", "surge": 1.5, "reason": "High demand"},
        {"area": "Suburbs", "surge": 1.0, "reason": "Normal demand"},
        {"area": "Airport", "surge": 1.8, "reason": "Limited providers"},
        {"area": "Tech Park", "surge": 1.3, "reason": "Peak hours"},
        {"area": "Residential", "surge": 0.9, "reason": "Low demand"}
    ]
    
    return {"surge_map": areas}

@router.post("/notify-price-drop")
async def notify_price_drop(data: PriceDropNotificationRequest, current_user: dict = Depends(get_current_user)):
    """Set price drop notification"""
    db = get_db()
    
    service_type = data.service_type
    target_price = data.target_price
    notification = {
        "user_id": current_user["sub"],
        "service_type": service_type,
        "target_price": target_price,
        "created_at": datetime.utcnow(),
        "status": "active"
    }
    
    result = await db.price_alerts.insert_one(notification)
    
    return {
        "alert_id": str(result.inserted_id),
        "message": f"You'll be notified when {service_type} prices drop to ₹{target_price}"
    }