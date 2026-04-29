from fastapi import APIRouter, Depends, UploadFile, File
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime
from bson import ObjectId
from typing import List, Optional, Dict
import base64
import json
from models.schemas import ARPreviewGenerateRequest, ARBookingRequest, ARShareRequest

router = APIRouter(prefix="/ar-preview", tags=["AR Service Preview"])

AR_SUPPORTED_SERVICES = {
    "interior_design": {
        "name": "Interior Design",
        "ar_features": ["furniture_placement", "color_schemes", "lighting", "room_layout"],
        "preview_types": ["3d_model", "color_overlay", "furniture_catalog"]
    },
    "gardening": {
        "name": "Gardening & Landscaping", 
        "ar_features": ["plant_placement", "garden_layout", "seasonal_preview", "growth_simulation"],
        "preview_types": ["plant_catalog", "layout_design", "seasonal_changes"]
    },
    "painting": {
        "name": "Painting Services",
        "ar_features": ["color_preview", "texture_overlay", "before_after"],
        "preview_types": ["color_palette", "texture_samples", "finish_preview"]
    },
    "renovation": {
        "name": "Home Renovation",
        "ar_features": ["structural_changes", "material_preview", "progress_simulation"],
        "preview_types": ["blueprint_overlay", "material_samples", "renovation_stages"]
    }
}

@router.post("/upload-space")
async def upload_space_image(
    file: UploadFile = File(...),
    space_type: str = "room",
    dimensions: Optional[Dict] = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload space image for AR preview"""
    db = get_db()
    
    # Read and encode image
    image_data = await file.read()
    image_base64 = base64.b64encode(image_data).decode()
    
    # Store space data
    space_record = {
        "user_id": current_user["sub"],
        "filename": file.filename,
        "space_type": space_type,
        "dimensions": dimensions or {"width": 10, "height": 10, "length": 12},
        "image_data": image_base64,
        "uploaded_at": datetime.utcnow(),
        "ar_anchors": [],  # Will be populated by AR processing
        "processed": False
    }
    
    result = await db.ar_spaces.insert_one(space_record)
    
    # Mock AR processing (in production, use actual AR/ML services)
    ar_anchors = generate_mock_ar_anchors(space_type, dimensions)
    
    await db.ar_spaces.update_one(
        {"_id": result.inserted_id},
        {"$set": {"ar_anchors": ar_anchors, "processed": True}}
    )
    
    return {
        "space_id": str(result.inserted_id),
        "message": "Space uploaded and processed for AR",
        "ar_anchors": ar_anchors,
        "supported_services": list(AR_SUPPORTED_SERVICES.keys())
    }

@router.get("/preview/{service_type}")
async def get_ar_preview_options(service_type: str):
    """Get AR preview options for a service type"""
    
    if service_type not in AR_SUPPORTED_SERVICES:
        return {"error": "AR preview not supported for this service"}
    
    service_config = AR_SUPPORTED_SERVICES[service_type]
    
    # Mock catalog data
    preview_catalog = generate_preview_catalog(service_type)
    
    return {
        "service": service_config["name"],
        "ar_features": service_config["ar_features"],
        "preview_types": service_config["preview_types"],
        "catalog": preview_catalog,
        "instructions": f"Point your camera at the space to preview {service_type} options"
    }

@router.post("/generate-preview")
async def generate_ar_preview(
    data: ARPreviewGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate AR preview for specific service"""
    db = get_db()
    
    space_id = data.space_id
    service_type = data.service_type
    preview_config = data.preview_config
    
    # Get space data
    space = await db.ar_spaces.find_one({
        "_id": ObjectId(space_id),
        "user_id": current_user["sub"]
    })
    
    if not space:
        return {"error": "Space not found"}
    
    if service_type not in AR_SUPPORTED_SERVICES:
        return {"error": "Service not supported for AR preview"}
    
    # Generate AR preview based on service type
    ar_preview = await create_ar_preview(space, service_type, preview_config, db)
    
    # Save preview
    preview_record = {
        "space_id": space_id,
        "user_id": current_user["sub"],
        "service_type": service_type,
        "preview_config": preview_config,
        "ar_data": ar_preview,
        "created_at": datetime.utcnow(),
        "shared": False,
        "bookings_generated": 0
    }
    
    result = await db.ar_previews.insert_one(preview_record)
    
    return {
        "preview_id": str(result.inserted_id),
        "ar_preview": ar_preview,
        "share_url": f"/ar-preview/view/{result.inserted_id}",
        "estimated_cost": calculate_service_cost(service_type, preview_config)
    }

@router.get("/my-previews")
async def get_my_ar_previews(current_user: dict = Depends(get_current_user)):
    """Get user's AR previews"""
    db = get_db()
    
    previews = await db.ar_previews.find({
        "user_id": current_user["sub"]
    }).sort("created_at", -1).to_list(length=50)
    
    for preview in previews:
        preview["_id"] = str(preview["_id"])
        
        # Get space info
        space = await db.ar_spaces.find_one({"_id": ObjectId(preview["space_id"])})
        if space:
            preview["space_info"] = {
                "space_type": space["space_type"],
                "dimensions": space["dimensions"]
            }
    
    return {"previews": previews}

@router.post("/book-from-preview/{preview_id}")
async def book_service_from_preview(
    preview_id: str,
    data: ARBookingRequest,
    current_user: dict = Depends(get_current_user)
):
    """Book service directly from AR preview"""
    db = get_db()
    
    provider_id = data.provider_id
    scheduled_time = data.scheduled_time
    notes = data.notes
    
    # Get preview
    preview = await db.ar_previews.find_one({
        "_id": ObjectId(preview_id),
        "user_id": current_user["sub"]
    })
    
    if not preview:
        return {"error": "Preview not found"}
    
    # Create booking with AR preview data
    booking = {
        "user_id": current_user["sub"],
        "provider_id": provider_id,
        "service_type": preview["service_type"],
        "scheduled_time": scheduled_time,
        "ar_preview_id": preview_id,
        "ar_specifications": preview["preview_config"],
        "notes": notes or "Booked from AR preview",
        "status": "pending",
        "created_at": datetime.utcnow(),
        "estimated_cost": calculate_service_cost(preview["service_type"], preview["preview_config"])
    }
    
    result = await db.bookings.insert_one(booking)
    
    # Update preview stats
    await db.ar_previews.update_one(
        {"_id": ObjectId(preview_id)},
        {"$inc": {"bookings_generated": 1}}
    )
    
    return {
        "booking_id": str(result.inserted_id),
        "message": "Service booked from AR preview!",
        "ar_specifications_included": True
    }

@router.post("/share-preview/{preview_id}")
async def share_ar_preview(
    preview_id: str,
    data: ARShareRequest,
    current_user: dict = Depends(get_current_user)
):
    """Share AR preview with others"""
    db = get_db()
    
    share_with = data.share_with
    
    # Update preview sharing
    await db.ar_previews.update_one(
        {"_id": ObjectId(preview_id), "user_id": current_user["sub"]},
        {
            "$set": {
                "shared": True,
                "shared_with": share_with,
                "shared_at": datetime.utcnow()
            }
        }
    )
    
    # Create notifications for shared users
    if "public" not in share_with:
        for user_id in share_with:
            await db.notifications.insert_one({
                "user_id": user_id,
                "type": "ar_preview_shared",
                "title": "AR Preview Shared With You",
                "message": "Someone shared an AR service preview with you",
                "preview_id": preview_id,
                "created_at": datetime.utcnow()
            })
    
    return {
        "message": "AR preview shared successfully!",
        "share_url": f"/ar-preview/view/{preview_id}",
        "shared_with": len(share_with) if "public" not in share_with else "public"
    }

@router.get("/trending")
async def get_trending_ar_previews():
    """Get trending AR previews and popular configurations"""
    db = get_db()
    
    # Most popular preview configurations
    popular_configs = await db.ar_previews.aggregate([
        {"$match": {"shared": True}},
        {"$group": {
            "_id": {
                "service_type": "$service_type",
                "config": "$preview_config"
            },
            "usage_count": {"$sum": 1},
            "bookings": {"$sum": "$bookings_generated"}
        }},
        {"$sort": {"usage_count": -1}},
        {"$limit": 10}
    ]).to_list(length=10)
    
    # Most booked AR previews
    top_converting = await db.ar_previews.find({
        "bookings_generated": {"$gt": 0}
    }).sort("bookings_generated", -1).limit(5).to_list(length=5)
    
    for preview in top_converting:
        preview["_id"] = str(preview["_id"])
    
    return {
        "popular_configurations": popular_configs,
        "top_converting_previews": top_converting,
        "insights": [
            "Interior design previews have 40% higher booking rates",
            "Garden layout previews are most shared",
            "Color preview features are most popular"
        ]
    }

@router.get("/analytics")
async def get_ar_analytics(current_user: dict = Depends(get_current_user)):
    """Get AR preview analytics for admin"""
    if current_user["role"] != "admin":
        return {"error": "Admin access required"}
    
    db = get_db()
    
    # Usage statistics
    total_previews = await db.ar_previews.count_documents({})
    total_bookings_from_ar = await db.bookings.count_documents({"ar_preview_id": {"$exists": True}})
    
    # Service type breakdown
    service_breakdown = await db.ar_previews.aggregate([
        {"$group": {"_id": "$service_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]).to_list(length=10)
    
    # Conversion rates
    conversion_rate = (total_bookings_from_ar / max(total_previews, 1)) * 100
    
    return {
        "total_ar_previews": total_previews,
        "bookings_from_ar": total_bookings_from_ar,
        "conversion_rate": round(conversion_rate, 2),
        "service_breakdown": service_breakdown,
        "insights": [
            f"AR previews have {conversion_rate:.1f}% conversion rate",
            "Interior design AR is most popular",
            "Users spend 3x more time on AR-enabled services"
        ]
    }

async def create_ar_preview(space: Dict, service_type: str, config: Dict, db) -> Dict:
    """Create AR preview data based on service type and configuration"""
    
    ar_preview = {
        "service_type": service_type,
        "space_dimensions": space["dimensions"],
        "ar_objects": [],
        "overlays": [],
        "animations": []
    }
    
    if service_type == "interior_design":
        ar_preview["ar_objects"] = [
            {
                "type": "furniture",
                "item": config.get("furniture_type", "sofa"),
                "position": {"x": 2, "y": 0, "z": 3},
                "rotation": {"x": 0, "y": 45, "z": 0},
                "scale": {"x": 1, "y": 1, "z": 1},
                "color": config.get("color", "#8B4513")
            }
        ]
        ar_preview["overlays"] = [
            {
                "type": "color_scheme",
                "colors": config.get("colors", ["#FFFFFF", "#F0F0F0", "#E0E0E0"]),
                "opacity": 0.7
            }
        ]
    
    elif service_type == "gardening":
        ar_preview["ar_objects"] = [
            {
                "type": "plant",
                "species": config.get("plant_type", "rose_bush"),
                "position": {"x": 1, "y": 0, "z": 2},
                "growth_stage": config.get("growth_stage", "mature"),
                "seasonal_colors": ["#228B22", "#32CD32", "#90EE90"]
            }
        ]
        ar_preview["animations"] = [
            {
                "type": "growth_simulation",
                "duration": "12_months",
                "stages": ["seedling", "growing", "mature", "flowering"]
            }
        ]
    
    elif service_type == "painting":
        ar_preview["overlays"] = [
            {
                "type": "paint_color",
                "color": config.get("paint_color", "#FF6B6B"),
                "finish": config.get("finish", "matte"),
                "coverage_area": "walls"
            }
        ]
    
    return ar_preview

def generate_mock_ar_anchors(space_type: str, dimensions: Dict) -> List[Dict]:
    """Generate mock AR anchor points for space"""
    anchors = []
    
    if space_type == "room":
        anchors = [
            {"id": "floor_center", "position": {"x": 0, "y": 0, "z": 0}, "type": "floor"},
            {"id": "wall_north", "position": {"x": 0, "y": 1.5, "z": dimensions.get("length", 10)/2}, "type": "wall"},
            {"id": "wall_south", "position": {"x": 0, "y": 1.5, "z": -dimensions.get("length", 10)/2}, "type": "wall"},
            {"id": "corner_nw", "position": {"x": -dimensions.get("width", 10)/2, "y": 0, "z": dimensions.get("length", 10)/2}, "type": "corner"}
        ]
    elif space_type == "garden":
        anchors = [
            {"id": "ground_center", "position": {"x": 0, "y": 0, "z": 0}, "type": "ground"},
            {"id": "border_north", "position": {"x": 0, "y": 0, "z": dimensions.get("length", 10)/2}, "type": "border"},
            {"id": "border_south", "position": {"x": 0, "y": 0, "z": -dimensions.get("length", 10)/2}, "type": "border"}
        ]
    
    return anchors

def generate_preview_catalog(service_type: str) -> Dict:
    """Generate mock catalog for AR previews"""
    
    catalogs = {
        "interior_design": {
            "furniture": [
                {"id": "sofa_modern", "name": "Modern Sofa", "colors": ["#8B4513", "#654321", "#D2691E"]},
                {"id": "table_coffee", "name": "Coffee Table", "materials": ["wood", "glass", "metal"]},
                {"id": "chair_accent", "name": "Accent Chair", "styles": ["contemporary", "vintage", "minimalist"]}
            ],
            "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
            "styles": ["modern", "traditional", "minimalist", "bohemian"]
        },
        "gardening": {
            "plants": [
                {"id": "rose_bush", "name": "Rose Bush", "seasons": ["spring", "summer"], "colors": ["red", "pink", "white"]},
                {"id": "lavender", "name": "Lavender", "seasons": ["summer"], "colors": ["purple"]},
                {"id": "maple_tree", "name": "Maple Tree", "seasons": ["all"], "colors": ["green", "red", "orange"]}
            ],
            "layouts": ["formal", "cottage", "zen", "wildflower"],
            "features": ["pathway", "fountain", "gazebo", "flower_bed"]
        },
        "painting": {
            "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"],
            "finishes": ["matte", "satin", "semi-gloss", "gloss"],
            "textures": ["smooth", "textured", "stucco", "brick_pattern"]
        }
    }
    
    return catalogs.get(service_type, {})

def calculate_service_cost(service_type: str, config: Dict) -> float:
    """Calculate estimated cost based on AR preview configuration"""
    
    base_costs = {
        "interior_design": 5000,
        "gardening": 3000,
        "painting": 2000,
        "renovation": 15000
    }
    
    base_cost = base_costs.get(service_type, 1000)
    
    # Add complexity multipliers based on configuration
    multiplier = 1.0
    
    if service_type == "interior_design":
        furniture_count = len(config.get("furniture_items", []))
        multiplier += furniture_count * 0.2
    
    elif service_type == "gardening":
        plant_count = len(config.get("plants", []))
        multiplier += plant_count * 0.1
    
    elif service_type == "painting":
        room_count = config.get("room_count", 1)
        multiplier += (room_count - 1) * 0.3
    
    return round(base_cost * multiplier, 2)