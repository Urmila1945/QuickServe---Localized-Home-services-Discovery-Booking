from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime
from bson import ObjectId
from typing import Optional
import math

router = APIRouter(prefix="/tracking", tags=["Location Tracking"])

class LocationManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, booking_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[booking_id] = websocket
    
    def disconnect(self, booking_id: str):
        if booking_id in self.active_connections:
            del self.active_connections[booking_id]
    
    async def broadcast_location(self, booking_id: str, location_data: dict):
        if booking_id in self.active_connections:
            await self.active_connections[booking_id].send_json(location_data)

location_manager = LocationManager()

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@router.post("/update-location")
async def update_location(
    latitude: float,
    longitude: float,
    accuracy: Optional[float] = None,
    speed: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    location_data = {
        "provider_id": current_user["sub"],
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy,
        "speed": speed,
        "timestamp": datetime.utcnow()
    }
    await db.location_history.insert_one(location_data)
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": {"current_location": {"latitude": latitude, "longitude": longitude, "last_updated": datetime.utcnow()}}}
    )
    active_bookings = await db.bookings.find({"provider_id": current_user["sub"], "status": {"$in": ["confirmed", "in_progress"]}}).to_list(length=10)
    for booking in active_bookings:
        await location_manager.broadcast_location(str(booking["_id"]), location_data)
    return {"status": "updated", "latitude": latitude, "longitude": longitude}

@router.get("/location/{booking_id}")
async def get_location(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        return {"error": "Booking not found"}
    location = await db.location_history.find_one({"provider_id": booking.get("provider_id")}, sort=[("timestamp", -1)])
    if location:
        location["_id"] = str(location["_id"])
    return location

@router.get("/history/{provider_id}")
async def get_location_history(provider_id: str):
    db = get_db()
    history = await db.location_history.find({"provider_id": provider_id}).sort("timestamp", -1).limit(50).to_list(length=50)
    for h in history:
        h["_id"] = str(h["_id"])
    return history

@router.get("/nearby-providers")
async def get_nearby_providers(latitude: float, longitude: float, service_type: Optional[str] = None, radius_km: float = 5.0):
    db = get_db()
    query = {"role": "provider", "is_verified": True}
    if service_type:
        query["specializations"] = service_type
    providers = await db.users.find(query).to_list(length=100)
    nearby = []
    for provider in providers:
        if "current_location" in provider:
            loc = provider["current_location"]
            distance = calculate_distance(latitude, longitude, loc["latitude"], loc["longitude"])
            if distance <= radius_km:
                nearby.append({"provider_id": str(provider["_id"]), "name": provider.get("full_name"), "distance_km": round(distance, 2), "eta_minutes": int(distance * 2)})
    nearby.sort(key=lambda x: x["distance_km"])
    return {"nearby_providers": nearby}

@router.websocket("/ws/{booking_id}")
async def location_websocket(websocket: WebSocket, booking_id: str):
    await location_manager.connect(booking_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        location_manager.disconnect(booking_id)
