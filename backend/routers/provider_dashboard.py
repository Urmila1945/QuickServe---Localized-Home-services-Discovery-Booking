from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime, timedelta
from database.connection import get_db
from middleware.auth import get_current_user
from bson import ObjectId
import random

router = APIRouter(prefix="/provider", tags=["Provider Dashboard"])

# 1. Active Job HUD
@router.get("/active-job")
async def get_active_job(current_user: dict = Depends(get_current_user)):
    db = get_db()
    active_job = await db.bookings.find_one({
        "provider_id": current_user["sub"],
        "status": "in_progress"
    })
    
    if not active_job:
        return {"active_job": None}
    
    active_job["_id"] = str(active_job["_id"])
    return {"active_job": active_job}

# 2. Biometric Check-in/Out
@router.post("/checkin")
async def biometric_checkin(
    booking_id: str,
    latitude: float,
    longitude: float,
    photo: str,  # base64 encoded
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Verify booking exists and belongs to provider
    booking = await db.bookings.find_one({
        "_id": ObjectId(booking_id),
        "provider_id": current_user["sub"]
    })
    
    if not booking:
        raise HTTPException(404, "Booking not found")
    
    # Store proof of presence
    checkin_data = {
        "booking_id": booking_id,
        "provider_id": current_user["sub"],
        "timestamp": datetime.utcnow(),
        "location": {"latitude": latitude, "longitude": longitude},
        "photo": photo,
        "type": "checkin"
    }
    
    await db.provider_checkins.insert_one(checkin_data)
    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "in_progress", "started_at": datetime.utcnow()}}
    )
    
    return {"success": True, "message": "Checked in successfully"}

@router.post("/checkout")
async def biometric_checkout(
    booking_id: str,
    latitude: float,
    longitude: float,
    photo: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    checkout_data = {
        "booking_id": booking_id,
        "provider_id": current_user["sub"],
        "timestamp": datetime.utcnow(),
        "location": {"latitude": latitude, "longitude": longitude},
        "photo": photo,
        "type": "checkout"
    }
    
    await db.provider_checkins.insert_one(checkout_data)
    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "completed", "completed_at": datetime.utcnow()}}
    )
    
    return {"success": True, "message": "Checked out successfully"}

# 3. Pheromone Live Mode
@router.post("/live-mode/toggle")
async def toggle_live_mode(
    enabled: bool,
    latitude: float,
    longitude: float,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": {
            "live_mode": enabled,
            "live_location": {"latitude": latitude, "longitude": longitude} if enabled else None,
            "live_mode_updated": datetime.utcnow()
        }}
    )
    
    return {"success": True, "live_mode": enabled}

@router.get("/live-mode/status")
async def get_live_mode_status(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    return {
        "live_mode": user.get("live_mode", False),
        "live_location": user.get("live_location")
    }

# 4. AI Neighborhood Skill-Gap Alerts
@router.get("/skill-gap-alerts")
async def get_skill_gap_alerts(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Get provider's location
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user or not user.get("location"):
        return {"alerts": []}
    
    user_lat = user["location"]["latitude"]
    user_lng = user["location"]["longitude"]
    
    # Analyze demand vs supply in 5-mile radius
    categories = await db.services.distinct("category")
    alerts = []
    
    for category in categories[:10]:  # Top 10 categories
        # Count providers in area
        providers = await db.services.count_documents({
            "category": category,
            "latitude": {"$gte": user_lat - 0.1, "$lte": user_lat + 0.1},
            "longitude": {"$gte": user_lng - 0.1, "$lte": user_lng + 0.1}
        })
        
        # Count recent searches (simulated)
        demand = random.randint(50, 200)
        
        if providers < demand * 0.3:  # Supply shortage
            shortage_pct = int((1 - providers / (demand * 0.3)) * 100)
            alerts.append({
                "category": category,
                "shortage_percentage": shortage_pct,
                "message": f"There is a {shortage_pct}% shortage of '{category.title()}' in your 5-mile radius. Add this skill to increase leads.",
                "potential_earnings": f"₹{random.randint(5000, 15000)}/month"
            })
    
    return {"alerts": sorted(alerts, key=lambda x: x["shortage_percentage"], reverse=True)[:5]}

# 5. Dynamic Surge Pricing
@router.get("/surge-pricing")
async def get_surge_pricing(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Get provider's category
    service = await db.services.find_one({"provider_id": current_user["sub"]})
    if not service:
        return {"surge_active": False}
    
    # Simulate surge detection based on category and time
    hour = datetime.utcnow().hour
    category = service["category"]
    
    surge_conditions = {
        "plumber": hour in [7, 8, 9, 18, 19, 20],  # Morning/evening rush
        "electrician": hour in [10, 11, 17, 18],
        "cleaner": hour in [9, 10, 11, 15, 16]
    }
    
    is_surge = surge_conditions.get(category, False)
    surge_multiplier = 1.3 if is_surge else 1.0
    
    return {
        "surge_active": is_surge,
        "surge_multiplier": surge_multiplier,
        "suggested_price": round(service["price_per_hour"] * surge_multiplier, 2),
        "reason": "High demand period" if is_surge else "Normal demand"
    }

@router.post("/surge-pricing/apply")
async def apply_surge_pricing(
    multiplier: float,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    service = await db.services.find_one({"provider_id": current_user["sub"]})
    new_price = round(service["base_price"] * multiplier, 2)
    
    await db.services.update_one(
        {"provider_id": current_user["sub"]},
        {"$set": {
            "price_per_hour": new_price,
            "surge_multiplier": multiplier,
            "surge_applied_at": datetime.utcnow()
        }}
    )
    
    return {"success": True, "new_price": new_price}

# 6. Smart Route Density Scheduling
@router.get("/route-density")
async def get_route_density(
    date: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Get all bookings for the date
    target_date = datetime.fromisoformat(date)
    bookings = await db.bookings.find({
        "provider_id": current_user["sub"],
        "scheduled_date": {
            "$gte": target_date,
            "$lt": target_date + timedelta(days=1)
        }
    }).to_list(length=100)
    
    # Calculate density for each hour
    density_map = {}
    for hour in range(8, 20):  # 8 AM to 8 PM
        nearby_count = 0
        for booking in bookings:
            booking_hour = booking.get("scheduled_time", "09:00").split(":")[0]
            if int(booking_hour) == hour:
                nearby_count += 1
        
        density_map[f"{hour:02d}:00"] = {
            "density": "high" if nearby_count >= 2 else "medium" if nearby_count == 1 else "low",
            "color": "green" if nearby_count >= 2 else "yellow" if nearby_count == 1 else "gray",
            "nearby_jobs": nearby_count,
            "fuel_savings": f"₹{nearby_count * 50}" if nearby_count > 0 else "₹0"
        }
    
    return {"date": date, "density_map": density_map}

# 7. AI Portfolio Generator
@router.post("/portfolio/generate")
async def generate_portfolio_caption(
    photo: str,  # base64
    job_type: str,
    current_user: dict = Depends(get_current_user)
):
    # Simulate AI caption generation
    captions = {
        "plumbing": [
            "Restored vintage copper piping in a heritage property – Precision soldering technique used.",
            "Installed modern tankless water heater system – 40% energy savings guaranteed.",
            "Emergency leak repair completed in under 2 hours – Zero water damage achieved."
        ],
        "electrical": [
            "Upgraded entire home electrical panel to 200A service – Smart home ready installation.",
            "Installed energy-efficient LED lighting throughout – Reduced power consumption by 60%.",
            "Rewired vintage property maintaining original aesthetics – Code compliant restoration."
        ],
        "carpentry": [
            "Restored vintage hardwood flooring in a 1920s bungalow – Dustless sanding technique used.",
            "Custom-built oak kitchen cabinets with soft-close hinges – Handcrafted perfection.",
            "Repaired antique furniture maintaining original joinery – Traditional craftsmanship preserved."
        ]
    }
    
    category = job_type.lower()
    caption = random.choice(captions.get(category, ["Professional service completed to highest standards."]))
    
    # Store in portfolio
    db = get_db()
    portfolio_item = {
        "provider_id": current_user["sub"],
        "photo": photo,
        "caption": caption,
        "job_type": job_type,
        "created_at": datetime.utcnow(),
        "likes": 0,
        "views": 0
    }
    
    result = await db.provider_portfolio.insert_one(portfolio_item)
    
    return {
        "success": True,
        "caption": caption,
        "portfolio_id": str(result.inserted_id)
    }

@router.get("/portfolio")
async def get_portfolio(current_user: dict = Depends(get_current_user)):
    db = get_db()
    portfolio = await db.provider_portfolio.find({
        "provider_id": current_user["sub"]
    }).sort("created_at", -1).limit(20).to_list(length=20)
    
    for item in portfolio:
        item["_id"] = str(item["_id"])
    
    return {"portfolio": portfolio}

# 8. Provider Dashboard Stats
@router.get("/stats")
async def get_provider_stats(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    
    # Basic counts
    total_bookings = await db.bookings.count_documents({"provider_id": provider_id})
    completed = await db.bookings.count_documents({"provider_id": provider_id, "status": "completed"})
    active = await db.bookings.count_documents({"provider_id": provider_id, "status": "in_progress"})
    pending = await db.bookings.count_documents({"provider_id": provider_id, "status": "pending"})
    
    # Earnings pipeline
    earnings_pipeline = [
        {"$match": {"provider_id": provider_id, "status": "completed"}},
        {"$group": {
            "_id": None,
            "total_earnings": {"$sum": "$amount"},
            "total_jobs": {"$sum": 1},
            "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}},
            "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}}
        }}
    ]
    earnings = await db.bookings.aggregate(earnings_pipeline).to_list(length=1)
    earnings_data = earnings[0] if earnings else {}
    
    total_earnings = earnings_data.get("total_earnings", 0)
    
    # Today's earnings
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_pipeline = [
        {"$match": {"provider_id": provider_id, "status": "completed", "completed_at": {"$gte": today_start}}},
        {"$group": {"_id": None, "earnings_today": {"$sum": "$amount"}}}
    ]
    today_earnings = await db.bookings.aggregate(today_pipeline).to_list(length=1)
    earnings_today = today_earnings[0].get("earnings_today", 0) if today_earnings else 0
    
    # Service rating
    service = await db.services.find_one({"provider_id": provider_id})
    rating = service.get("rating", 0) if service else 0
    
    user = await db.users.find_one({"_id": ObjectId(provider_id)})
    
    # Competitor rank (local market position) - percentile among providers
    all_providers_pipeline = [  # noqa: C408
        {"$match": {"role": "provider"}},
        {"$lookup": {
            "from": "bookings",
            "let": {"prov_id": {"$toString": "$_id"}},
            "pipeline": [
                {"$match": {
                    "$expr": {"$eq": ["$provider_id", "$$prov_id"]},
                    "status": "completed"
                }},
                {"$group": {"_id": None, "prov_earnings": {"$sum": "$amount"}}}
            ],
            "as": "prov_stats"
        }},
        {"$addFields": {"prov_earnings": {
            "$arrayElemAt": ["$prov_stats.prov_earnings", 0]
        }}},
        {"$addFields": {"prov_earnings": {"$ifNull": ["$prov_earnings", 0]}}},
        {"$sort": {"prov_earnings": -1}},
        {"$group": {
            "_id": None,
            "providers": {"$push": "$$ROOT"},
            "total_providers": {"$sum": 1}
        }},
        {"$addFields": {"percentile_rank": {
            "$indexOfArray": [{
                "$map": {
                    "input": "$providers",
                    "as": "p",
                    "in": {"$indexOfArray": ["$providers", "$$ROOT"]}
                }
            }, 0]
        }}}
    ]
    all_stats = await db.users.aggregate(all_providers_pipeline).to_list(length=1)
    rank = 1  # default
    percentile = 0.0
    if all_stats and all_stats[0].get("providers"):
        providers_list = all_stats[0]["providers"]
        total_prov = all_stats[0]["total_providers"]
        for idx, prov in enumerate(providers_list):
            if str(prov["_id"]) == provider_id:
                rank = idx + 1
                percentile = round((1 - (idx / total_prov)) * 100, 1)
                break
    
    # Route efficiency score: earnings per km
    route_efficiency = round(
        total_earnings / max(earnings_data.get("total_distance", 1), 1), 2
    )
    
    user_live_mode = user.get("live_mode", False) if user else False
    
    market_pos = (
        f"#{rank} of {all_stats[0].get('total_providers', 'N/A')} "
        f"({percentile} percentile)"
    )
    
    return {
        "total_bookings": total_bookings,
        "completed_bookings": completed,
        "completed_jobs": completed,
        "active_bookings": active,
        "pending_bookings": pending,
        "total_earnings": total_earnings,
        "earnings_today": earnings_today,
        "average_rating": rating,
        "live_mode": user_live_mode,
        "local_market_position": market_pos,
        "route_efficiency_score": route_efficiency,
        "profit_per_hour": round(
            total_earnings / (earnings_data.get("total_duration", 60) / 60), 2
        ),
        "avg_job_value": round(
            total_earnings / max(earnings_data.get("total_jobs", 1), 1), 2
        )
    }


# 9. Geospatial Territory Management
@router.post("/territory/boundary")
async def save_service_boundary(
    polygon: List[dict],  # [{lat, lng}, ...]
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": {
            "service_boundary": polygon,
            "boundary_updated": datetime.utcnow()
        }}
    )
    
    return {"success": True, "message": "Service boundary saved"}

@router.get("/territory/boundary")
async def get_service_boundary(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    return {"boundary": user.get("service_boundary", [])}

@router.post("/territory/no-go-zones")
async def add_no_go_zone(
    zone: dict,  # {name, coordinates: [{lat, lng}]}
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$push": {"no_go_zones": zone}}
    )
    
    return {"success": True, "message": "No-go zone added"}

@router.delete("/territory/no-go-zones/{zone_name}")
async def remove_no_go_zone(
    zone_name: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$pull": {"no_go_zones": {"name": zone_name}}}
    )
    
    return {"success": True, "message": "No-go zone removed"}

@router.get("/territory/no-go-zones")
async def get_no_go_zones(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    return {"zones": user.get("no_go_zones", [])}

@router.get("/territory/demand-heatmap")
async def get_demand_heatmap(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Get provider's service area
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user or not user.get("location"):
        return {"heatmap": []}
    
    # Generate heatmap data (simulated demand)
    center_lat = user["location"]["latitude"]
    center_lng = user["location"]["longitude"]
    
    heatmap_points = []
    for i in range(20):
        lat_offset = (random.random() - 0.5) * 0.1
        lng_offset = (random.random() - 0.5) * 0.1
        intensity = random.randint(1, 100)
        
        heatmap_points.append({
            "lat": center_lat + lat_offset,
            "lng": center_lng + lng_offset,
            "intensity": intensity
        })
    
    return {"heatmap": heatmap_points}

# 10. Financial & Trust Analytics
@router.get("/analytics/earnings-pulse")
async def get_earnings_pulse(
    period: str = "weekly",  # daily, weekly, monthly
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    provider_id = current_user["sub"]
    
    match_stage = {
        "provider_id": provider_id,
        "status": "completed"
    }
    
    if period == "daily":
        group_stage = {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$completed_at"}},
                "revenue": {"$sum": "$amount"},
                "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}},
                "jobs": {"$sum": 1},
                "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}}
            }
        }
        time_filter = {"$gte": datetime.utcnow() - timedelta(days=30)}
        sort_desc = {"$sort": {"_id": -1}}
        limit_docs = 30
        
    elif period == "weekly":
        group_stage = {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-W%U", "date": "$completed_at"}
                },
                "revenue": {"$sum": "$amount"},
                "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}},
                "jobs": {"$sum": 1},
                "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}}
            }
        }
        time_filter = {"$gte": datetime.utcnow() - timedelta(weeks=12)}
        sort_desc = {"$sort": {"_id": -1}}
        limit_docs = 12
        
    else:  # monthly
        group_stage = {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m", "date": "$completed_at"}
                },
                "revenue": {"$sum": "$amount"},
                "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}},
                "jobs": {"$sum": 1},
                "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}}
            }
        }
        time_filter = {"$gte": datetime.utcnow() - timedelta(days=365)}
        sort_desc = {"$sort": {"_id": -1}}
        limit_docs = 12
    
    pipeline = [  # noqa: C408
        {"$match": match_stage},
        {"$match": {"completed_at": time_filter}},
        group_stage,
        sort_desc,
        {"$limit": limit_docs}
    ]
    
    earnings_data = await db.bookings.aggregate(pipeline).to_list(length=limit_docs)
    
    # Add calculated metrics
    for item in earnings_data:
        item["date"] = item["_id"]
        item["profit_per_hour"] = round(item["revenue"] / (item["total_duration"] / 60), 2) if item["total_duration"] > 0 else 0
        item["avg_job_value"] = round(item["revenue"] / item["jobs"], 2) if item["jobs"] > 0 else 0
        item["route_efficiency"] = round(item["revenue"] / max(item["total_distance"], 1), 2) if item["total_distance"] > 0 else 0
        del item["_id"]
    
    # Overall stats
    overall_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$amount"},
            "total_jobs": {"$sum": 1},
            "total_duration": {"$sum": {"$ifNull": ["$duration", 60]}},
            "total_distance": {"$sum": {"$ifNull": ["$distance", 0]}}
        }}
    ]
    overall = await db.bookings.aggregate(overall_pipeline).to_list(length=1)
    overall_stats = overall[0] if overall else {}
    
    return {
        "period": period,
        "data": earnings_data,
        "overall": {
            "total_revenue": overall_stats.get("total_revenue", 0),
            "avg_profit_per_hour": round(overall_stats.get("total_revenue", 0) / (overall_stats.get("total_duration", 60) / 60), 2),
            "avg_job_value": round(overall_stats.get("total_revenue", 0) / overall_stats.get("total_jobs", 1), 2),
            "route_efficiency_score": round(overall_stats.get("total_revenue", 0) / max(overall_stats.get("total_distance", 1), 1), 2)
        }
    }

@router.get("/analytics/advanced")
async def get_advanced_analytics(current_user: dict = Depends(get_current_user)):
    """Return all remaining analytics (peak hours, radar, competitors, etc.)"""
    # 1. Peak Hours (Simulated based on historical volume)
    peak_hours = [
        {"hour": "6AM", "requests": 8}, {"hour": "8AM", "requests": 22}, {"hour": "10AM", "requests": 45},
        {"hour": "12PM", "requests": 30}, {"hour": "2PM", "requests": 28}, {"hour": "4PM", "requests": 50},
        {"hour": "6PM", "requests": 48}, {"hour": "8PM", "requests": 18}, {"hour": "10PM", "requests": 6},
    ]

    # 2. Radar Data (Route Efficiency Metrics)
    radar_data = [
        {"subject": "Speed",     "score": 85},
        {"subject": "Distance",  "score": 72},
        {"subject": "Fuel",      "score": 68},
        {"subject": "On-Time",   "score": 90},
        {"subject": "Revisits",  "score": 60},
    ]

    # 3. Competitor Rank (Simulated based on nearby providers)
    competitor_rank = [
        {"name": "Rajesh K.",  "jobs": 142, "price": 650, "rating": 4.9},
        {"name": "You",        "jobs": 118, "price": 600, "rating": 4.8},
        {"name": "Suresh M.",  "jobs": 95,  "price": 700, "rating": 4.6},
        {"name": "Anil P.",    "jobs": 80,  "price": 550, "rating": 4.4},
    ]

    # 4. Route Efficiency by Zone
    route_efficiency_data = [
        {"zone": "Indiranagar",  "effScore": 88},
        {"zone": "Koramangala",  "effScore": 74},
        {"zone": "HSR Layout",   "effScore": 65},
        {"zone": "JP Nagar",     "effScore": 80},
    ]

    # 5. Demand Heatmap Zones
    heatmap_zones = [
        {"zone": "Koramangala",  "demand": 87, "color": "#ef4444"},
        {"zone": "Indiranagar",  "demand": 72, "color": "#f97316"},
        {"zone": "HSR Layout",   "demand": 55, "color": "#eab308"},
        {"zone": "Whitefield",   "demand": 38, "color": "#22c55e"},
        {"zone": "JP Nagar",     "demand": 61, "color": "#f97316"},
    ]

    # 6. Competitor Alerts
    competitor_alerts = [
        {"provider": "Vikram Electricals", "change": "+8%", "newRate": "₹1,079/hr", "area": "Koramangala",  "type": "up"},
        {"provider": "RapidFix Services",  "change": "-12%", "newRate": "₹747/hr",   "area": "Whitefield",   "type": "down"},
        {"provider": "PowerPro Bangalore", "change": "+5%",  "newRate": "₹996/hr",   "area": "Indiranagar",  "type": "up"},
    ]

    # 7. Seasonal Rules
    seasonal_rules = [
        {"name": "Summer AC Rush (Apr–Jun)",    "adjustment": "+25%", "category": "AC Technician", "status": "scheduled"},
        {"name": "Monsoon Plumbing Surge",      "adjustment": "+18%", "category": "Plumber",       "status": "active"},
        {"name": "Festive Deep Cleaning",       "adjustment": "+15%", "category": "Cleaner",       "status": "scheduled"},
        {"name": "Year-End Electrical Audit",   "adjustment": "+10%", "category": "Electrician",   "status": "active"},
    ]

    # 8. Recurring Customers
    recurring_customers = [
        {"name": "Anjali Singh",  "service": "Annual Wiring Inspection", "lastDate": "Dec 10 2023", "dueDate": "Dec 10 2024", "potential": 2490},
        {"name": "Meera Nair",    "service": "AC Pre-Summer Tune-up",    "lastDate": "Mar 15 2024", "dueDate": "Mar 15 2025", "potential": 1660},
        {"name": "Ramesh Gupta",  "service": "Quarterly Check",          "lastDate": "Sep 28 2024", "dueDate": "Dec 28 2024", "potential": 1245},
    ]

    return {
        "peak_hours": peak_hours,
        "radar_data": radar_data,
        "competitor_rank": competitor_rank,
        "route_efficiency_data": route_efficiency_data,
        "heatmap_zones": heatmap_zones,
        "competitor_alerts": competitor_alerts,
        "seasonal_rules": seasonal_rules,
        "recurring_customers": recurring_customers
    }

@router.get("/analytics/trust-score")
async def get_trust_score(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Get all bookings
    total_bookings = await db.bookings.count_documents({"provider_id": current_user["sub"]})
    completed = await db.bookings.count_documents({"provider_id": current_user["sub"], "status": "completed"})
    cancelled = await db.bookings.count_documents({"provider_id": current_user["sub"], "status": "cancelled"})
    
    # Calculate reliability (0-40 points)
    reliability = 0 if total_bookings == 0 else min(40, int((completed / total_bookings) * 40))
    
    # Calculate punctuality (0-30 points) - simulated
    punctuality = random.randint(20, 30)
    
    # Get reviews for quality (0-30 points)
    service = await db.services.find_one({"provider_id": current_user["sub"]})
    rating = service.get("rating", 0) if service else 0
    quality = int((rating / 5.0) * 30)
    
    trust_score = reliability + punctuality + quality
    
    return {
        "trust_score": trust_score,
        "breakdown": {
            "reliability": reliability,
            "punctuality": punctuality,
            "quality": quality
        },
        "metrics": {
            "completion_rate": f"{(completed/total_bookings*100):.1f}%" if total_bookings > 0 else "0%",
            "cancellation_rate": f"{(cancelled/total_bookings*100):.1f}%" if total_bookings > 0 else "0%",
            "average_rating": f"{rating:.1f}"
        }
    }

@router.post("/financial/instant-payout")
async def request_instant_payout(
    amount: float,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Check available balance
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    available_balance = user.get("available_balance", 0)
    
    if amount > available_balance:
        raise HTTPException(400, "Insufficient balance")
    
    # Create payout request
    payout = {
        "provider_id": current_user["sub"],
        "amount": amount,
        "status": "pending",
        "requested_at": datetime.utcnow(),
        "stripe_transfer_id": f"tr_{random.randint(100000, 999999)}"  # Simulated
    }
    
    await db.payouts.insert_one(payout)
    
    # Update balance
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$inc": {"available_balance": -amount}}
    )
    
    return {"success": True, "message": "Payout initiated", "transfer_id": payout["stripe_transfer_id"]}

@router.get("/financial/balance")
async def get_balance(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    
    # Calculate from completed payments (provider_payout field)
    payments_data = await db.payments.find({
        "provider_id": current_user["sub"],
        "status": "completed"
    }).to_list(length=1000)
    
    total_earned = sum(p.get("provider_payout") or p.get("amount", 0) for p in payments_data)
    
    # Get withdrawn amount
    payouts = await db.payouts.find({
        "provider_id": current_user["sub"],
        "status": {"$in": ["completed", "pending"]}
    }).to_list(length=1000)
    
    total_withdrawn = sum(p.get("amount", 0) for p in payouts)
    
    available = total_earned - total_withdrawn
    
    return {
        "available": available,               # frontend alias
        "available_balance": available,
        "total_earned": total_earned,
        "total_withdrawn": total_withdrawn,
        "pending_payouts": sum(p.get("amount", 0) for p in payouts if p.get("status") == "pending")
    }

# 11. Administrative & Compliance
@router.post("/compliance/documents")
async def upload_document(
    doc_type: str,  # license, insurance, background_check
    expiry_date: str,
    file: str,  # base64
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    document = {
        "provider_id": current_user["sub"],
        "type": doc_type,
        "expiry_date": datetime.fromisoformat(expiry_date),
        "file": file,
        "uploaded_at": datetime.utcnow(),
        "status": "active"
    }
    
    result = await db.provider_documents.insert_one(document)
    
    return {"success": True, "document_id": str(result.inserted_id)}

@router.get("/compliance/documents")
async def get_documents(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    docs = await db.provider_documents.find({
        "provider_id": current_user["sub"]
    }).sort("uploaded_at", -1).to_list(length=100)
    
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        # Check if expiring soon
        days_until_expiry = (doc["expiry_date"] - datetime.utcnow()).days
        doc["days_until_expiry"] = days_until_expiry
        doc["expiring_soon"] = days_until_expiry <= 30
    
    return {"documents": docs}

@router.get("/compliance/expiring-alerts")
async def get_expiring_alerts(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    thirty_days_from_now = datetime.utcnow() + timedelta(days=30)
    
    expiring_docs = await db.provider_documents.find({
        "provider_id": current_user["sub"],
        "expiry_date": {"$lte": thirty_days_from_now},
        "status": "active"
    }).to_list(length=100)
    
    alerts = []
    for doc in expiring_docs:
        days_left = (doc["expiry_date"] - datetime.utcnow()).days
        alerts.append({
            "type": doc["type"],
            "expiry_date": doc["expiry_date"].strftime("%Y-%m-%d"),
            "days_left": days_left,
            "urgency": "critical" if days_left <= 7 else "warning"
        })
    
    return {"alerts": alerts}

@router.get("/compliance/jury-cases")
async def get_jury_cases(current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Check if provider is eligible (rating > 4.5)
    service = await db.services.find_one({"provider_id": current_user["sub"]})
    if not service or service.get("rating", 0) < 4.5:
        return {"eligible": False, "cases": []}
    
    # Get open dispute cases
    cases = await db.disputes.find({
        "status": "pending_jury",
        "jury_members": {"$ne": current_user["sub"]}
    }).limit(5).to_list(length=5)
    
    for case in cases:
        case["_id"] = str(case["_id"])
    
    return {"eligible": True, "cases": cases}

@router.post("/compliance/jury-vote")
async def submit_jury_vote(
    case_id: str,
    verdict: str,  # customer_favor, provider_favor
    reasoning: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    vote = {
        "case_id": case_id,
        "juror_id": current_user["sub"],
        "verdict": verdict,
        "reasoning": reasoning,
        "voted_at": datetime.utcnow()
    }
    
    await db.jury_votes.insert_one(vote)
    
    # Award credits
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$inc": {"quickserve_credits": 50, "jury_reputation": 1}}
    )
    
    return {"success": True, "credits_earned": 50}

@router.get("/financial/tax-export")
async def export_tax_data(
    year: int,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    
    # Get all completed bookings for the year
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    
    bookings = await db.bookings.find({
        "provider_id": current_user["sub"],
        "status": "completed",
        "completed_at": {"$gte": start_date, "$lte": end_date}
    }).to_list(length=10000)
    
    # Generate CSV data
    csv_data = []
    total_earnings = 0
    total_commission = 0
    total_mileage = 0
    
    for booking in bookings:
        earnings = booking.get("total_amount", 0)
        commission = earnings * 0.15  # 15% platform fee
        mileage = booking.get("distance", 0) * 2  # Round trip
        
        total_earnings += earnings
        total_commission += commission
        total_mileage += mileage
        
        csv_data.append({
            "Date": booking.get("completed_at", datetime.utcnow()).strftime("%Y-%m-%d"),
            "Booking ID": str(booking.get("_id", "")),
            "Service": booking.get("service_name", ""),
            "Gross Earnings": f"₹{earnings:.2f}",
            "Platform Commission": f"₹{commission:.2f}",
            "Net Earnings": f"₹{(earnings - commission):.2f}",
            "Mileage (km)": f"{mileage:.1f}"
        })
    
    # Add summary row
    csv_data.append({
        "Date": "TOTAL",
        "Booking ID": "",
        "Service": "",
        "Gross Earnings": f"₹{total_earnings:.2f}",
        "Platform Commission": f"₹{total_commission:.2f}",
        "Net Earnings": f"₹{(total_earnings - total_commission):.2f}",
        "Mileage (km)": f"{total_mileage:.1f}"
    })
    
    return {
        "year": year,
        "data": csv_data,
        "summary": {
            "total_earnings": total_earnings,
            "total_commission": total_commission,
            "net_earnings": total_earnings - total_commission,
            "total_mileage": total_mileage
        }
    }
