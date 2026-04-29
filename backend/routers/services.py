from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from database.connection import get_db
from middleware.auth import get_current_user
from bson import ObjectId
from math import radians, sin, cos, sqrt, atan2

router = APIRouter(prefix="/services", tags=["Services"])


from pydantic import BaseModel

class VoicePrompt(BaseModel):
    text: str

def _haversine(lat1, lng1, lat2, lng2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


@router.get("/search")
async def search_services(
    q: Optional[str] = None,
    category: Optional[str] = None,
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: float = Query(10.0),
    min_rating: float = Query(0.0),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    emergency: Optional[bool] = None,
    limit: int = Query(20, le=100),
):
    db = get_db()
    query = {}

    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    if city:
        query["city"] = {"$regex": city, "$options": "i"}

    if min_rating > 0:
        query["rating"] = {"$gte": min_rating}

    if min_price is not None or max_price is not None:
        query["price_per_hour"] = {}
        if min_price is not None:
            query["price_per_hour"]["$gte"] = min_price
        if max_price is not None:
            query["price_per_hour"]["$lte"] = max_price

    if emergency:
        query["is_emergency"] = True

    services = await db.services.find(query).limit(limit * 5).to_list(length=limit * 5)
    
    use_location_filter = latitude is not None and longitude is not None and not city
    
    results = []
    if use_location_filter:
        for s in services:
            s["_id"] = str(s["_id"])
            p_lat = s.get("latitude") or 0
            p_lng = s.get("longitude") or 0
            dist = _haversine(latitude, longitude, p_lat, p_lng)
            s["distance"] = round(dist, 2)
            if dist <= radius:
                results.append(s)
        results.sort(key=lambda x: x["distance"])
    
    # Fallback if location filter returned nothing or wasn't used
    if not results:
        for s in services:
            s["_id"] = str(s["_id"])
            if latitude and longitude:
                p_lat = s.get("latitude") or 0
                p_lng = s.get("longitude") or 0
                s["distance"] = round(_haversine(latitude, longitude, p_lat, p_lng), 2)
        
        # Sort by rating if no results were found via distance
        services.sort(key=lambda x: x.get("rating", 0), reverse=True)
        results = services[:limit]

    return {"services": results, "total": len(results)}


@router.get("/categories")
async def get_categories():
    db = get_db()
    categories = await db.services.distinct("category")

    category_icons = {
        "electrician": "⚡", "electrical": "⚡",
        "plumber": "🔧", "plumbing": "🔧",
        "cleaner": "🧹", "cleaning": "🧹",
        "carpenter": "🪚", "carpentry": "🪚",
        "painter": "🎨", "painting": "🎨",
        "mechanic": "🔨", "repair": "🔨",
        "tutor": "📚", "tutoring": "📚",
        "beautician": "💇", "beauty": "💇",
        "chef": "👨‍🍳", "cooking": "👨‍🍳",
        "driver": "🚗", "delivery": "📦",
        "gardener": "🌱", "gardening": "🌱",
        "pest control": "🐛", "pest_control": "🐛",
        "fitness": "💪",
    }

    result = []
    for cat in sorted(categories):
        if cat:
            result.append({
                "value": cat,
                "label": cat.replace("_", " ").title(),
                "icon": category_icons.get(cat.lower(), "🔧"),
            })

    return {"categories": result}


@router.get("/cities")
async def get_cities():
    db = get_db()
    pipeline = [
        {"$match": {"city": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$city", "service_count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    result = await db.services.aggregate(pipeline).to_list(length=500)
    return [{"city": r["_id"], "service_count": r["service_count"]} for r in result if r["_id"]]


@router.get("/recommendations")
async def get_recommendations(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: float = Query(50.0),
    limit: int = Query(12, le=50),
    category: Optional[str] = None,
):
    """
    Get top-rated service recommendations.
    Works without authentication and without location.
    When location is provided, adds distance info but does NOT filter by radius
    (so results always appear).
    """
    db = get_db()

    query: dict = {"rating": {"$gte": 3.5}}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    # Fetch more than needed so we have variety
    services = (
        await db.services.find(query)
        .sort("rating", -1)
        .limit(limit * 10)
        .to_list(length=limit * 10)
    )

    # If still empty, fetch without rating filter
    if not services:
        services = (
            await db.services.find({} if not category else {"category": {"$regex": category, "$options": "i"}})
            .sort("rating", -1)
            .limit(limit * 5)
            .to_list(length=limit * 5)
        )

    import random
    # Shuffle slightly to ensure we don't always see the exact same top people every time
    # but keep top-rated mostly at the top by slicing top 50 and shuffling
    top_services = services[:50]
    random.shuffle(top_services)
    services = top_services + services[50:]

    result = []
    seen_categories = {}

    for s in services:
        s["_id"] = str(s["_id"])
        if latitude is not None and longitude is not None:
            p_lat = s.get("latitude") or s.get("location", {}).get("latitude") or 0
            p_lng = s.get("longitude") or s.get("location", {}).get("longitude") or 0
            if p_lat and p_lng:
                s["distance"] = round(_haversine(latitude, longitude, p_lat, p_lng), 2)
        
        # Enforce diversity if no specific category was requested
        if not category:
            cat = s.get("category", "other").lower()
            if seen_categories.get(cat, 0) >= 2:
                continue
            seen_categories[cat] = seen_categories.get(cat, 0) + 1

        result.append(s)

    # Sort: nearby first if location given, else by rating
    if latitude is not None and longitude is not None:
        result.sort(key=lambda x: (x.get("distance", 9999), -x.get("rating", 0)))
    else:
        # Since we randomized earlier, we just keep the randomized order for variety,
        # but you can sort by rating if strict ordering is desired.
        pass

    return {"recommendations": result[:limit], "total": len(result[:limit])}


# NOTE: /nearby MUST be before /{service_id} to avoid route conflict
@router.get("/nearby")
async def get_nearby_services(
    lat: float,
    lng: float,
    radius: float = 5.0,
    category: Optional[str] = None,
):
    db = get_db()
    query = {}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    services = await db.services.find(query).limit(500).to_list(length=500)

    nearby = []
    for s in services:
        s["_id"] = str(s["_id"])
        p_lat = s.get("latitude") or s.get("location", {}).get("latitude") or 0
        p_lng = s.get("longitude") or s.get("location", {}).get("longitude") or 0
        dist = _haversine(lat, lng, p_lat, p_lng)
        if dist <= radius:
            s["distance"] = round(dist, 2)
            nearby.append(s)

    nearby.sort(key=lambda x: x["distance"])
    return nearby[:20]


@router.get("/{service_id}")
async def get_service(service_id: str):
    db = get_db()
    try:
        oid = ObjectId(service_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service ID")
    service = await db.services.find_one({"_id": oid})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    service["_id"] = str(service["_id"])
    return service


@router.post("/")
async def create_service(service: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    service["provider_id"] = current_user["sub"]
    result = await db.services.insert_one(service)
    return {"id": str(result.inserted_id)}


@router.post("/voice-hail")
async def process_voice_hail(prompt: VoicePrompt):
    """
    AI NLP processing for Voice Hail text to extract intent.
    """
    text = prompt.text.lower()
    
    service_type = "general"
    urgency = "normal"
    
    if any(word in text for word in ["urgent", "emergency", "now", "quick", "fast", "immediately"]):
        urgency = "high"
        
    if any(word in text for word in ["plumb", "leak", "water", "pipe", "drain"]):
        service_type = "plumber"
    elif any(word in text for word in ["electri", "power", "shock", "wire", "light"]):
        service_type = "electrician"
    elif any(word in text for word in ["clean", "maid", "sweep", "dust"]):
        service_type = "house cleaning"
    elif any(word in text for word in ["fix", "repair", "handyman", "broken"]):
        service_type = "appliance repair"
    elif any(word in text for word in ["paint", "brush", "color", "wall"]):
        service_type = "painter"
    elif any(word in text for word in ["wood", "furniture", "door", "table"]):
        service_type = "carpenter"
    elif any(word in text for word in ["ac", "cool", "filter", "chilling"]):
        service_type = "ac technician"
    elif any(word in text for word in ["medical", "doctor", "health", "sick"]):
        service_type = "wellness"
        
    return {
        "service": service_type,
        "urgency": urgency,
        "original_text": prompt.text
    }
