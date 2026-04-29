import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import settings
from database.connection import connect_db, close_db, get_db
from middleware.auth import hash_password
from datetime import datetime
import os

# ── Import all routers ────────────────────────────────────────────────────
from routers import core                    # /auth/*, /verify/*, /providers/*, /profile
from routers import dashboards              # /dashboard/*
from routers import dashboard               # New /dashboard/* routes
from routers import features                # /ai/*, /chat/conversations, /community/*, /gamification/leaderboard, /mood-sync/*, /predictive/*
from routers import services as services_router  # /services/* (full: search, cities, categories, recommendations, nearby, CRUD)
from routers import bookings as bookings_router  # /bookings/*
from routers import payments as payments_router  # /payments/*
from routers import slots as slots_router        # /slots/*
from routers import reviews as reviews_router    # /reviews/*
from routers import tracking as tracking_router  # /tracking/*
from routers import chat as chat_router          # /chat/*  (full chat endpoints)
from routers import providers as providers_router  # /providers/* (extended)
from routers import surge as surge_router        # /surge/*
from routers import gamification as gamification_router  # /gamification/*
from routers import predictive as predictive_router      # /predictive/*
from routers import mood_sync as mood_sync_router        # /mood-sync/*
from routers import community as community_router        # /community/*
from routers import bundles as bundles_router            # /bundles/*
from routers import events as events_router              # /events/*
from routers import swap as swap_router                  # /swap/*
from routers import ar_preview as ar_router              # /ar-preview/*
from routers import roulette as roulette_router          # /roulette/*
from routers import ai_concierge as ai_concierge_router  # /ai-concierge/*
from routers import work_verification as wv_router       # /work-verification/*
from routers import aptitude as aptitude_router          # /aptitude/*
from routers import advanced as advanced_router          # advanced features
from routers import ai as ai_router                      # /ai/*
from routers import queue as queue_router                # /queue/*
from routers import admin_dashboard as admin_router      # /admin/*
from routers.core_engagement import loyalty_router, notifications_router, users_router, subscriptions_router, analytics_router, health_router

from database.csv_loader import load_csv_providers, providers_to_services

# ── Socket.IO ────────────────────────────────────────────────────────────
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)

# ── FastAPI app ───────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="QuickServe – Local Services Marketplace API",
)

# ── CORS (must be added before any route registration) ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount socket.io ───────────────────────────────────────────────────────
app.mount("/ws", socket_app)

# ── Serve uploaded files ──────────────────────────────────────────────────
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ── Socket events ─────────────────────────────────────────────────────────
@sio.event
async def connect(sid, environ):
    print(f"[WS] Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"[WS] Client disconnected: {sid}")

@sio.on("join_room")
async def join_room(sid, data):
    room = data.get("room")
    await sio.enter_room(sid, room)

@sio.on("update_location")
async def handle_location_update(sid, data):
    room = data.get("booking_id")
    await sio.emit("location_update", data, room=room)

# ── Startup ───────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    print("[INFO] Starting QuickServe server...")
    await connect_db()
    print("[OK] DB connected.")

    db = get_db()

    # ── Seed demo users ──────────────────────────────────────────────────
    demo_users = [
        {
            "email": "customer@demo.com",
            "password": hash_password("password123"),
            "full_name": "Demo Customer",
            "phone": "+91-9999999999",
            "role": "customer",
            "created_at": datetime.utcnow(),
            "verified_email": True,
            "verified_by_admin": True,
            "quickserve_credits": 350,
        },
        {
            "email": "provider@demo.com",
            "password": hash_password("password123"),
            "full_name": "Demo Provider",
            "phone": "+91-8888888888",
            "role": "provider",
            "created_at": datetime.utcnow(),
            "verified_email": True,
            "verified_by_admin": True,
            "is_verified": True,
            "specializations": ["plumbing", "electrical"],
            "rating": 4.5,
            "reviews_count": 100,
        },
        {
            "email": "admin@demo.com",
            "password": hash_password("password123"),
            "full_name": "Demo Admin",
            "phone": "+91-7777777777",
            "role": "admin",
            "created_at": datetime.utcnow(),
            "verified_email": True,
            "verified_by_admin": True,
            "is_superadmin": True,
        },
    ]

    for user_data in demo_users:
        try:
            existing = await db.users.find_one({"email": user_data["email"]})
            if not existing:
                await db.users.insert_one(user_data)
                print(f"[OK] Created demo user: {user_data['email']}")
            else:
                await db.users.update_one(
                    {"email": user_data["email"]},
                    {"$set": {
                        "password": user_data["password"],
                        "role": user_data["role"],
                        "full_name": user_data["full_name"],
                        "verified_email": True,
                        "verified_by_admin": True,
                    }},
                )
        except Exception as e:
            print(f"[ERROR] Demo user {user_data['email']}: {e}")

    # ── Import CSV provider data ─────────────────────────────────────────
    try:
        csv_count = await db.services.count_documents({"is_csv_imported": True})
        if csv_count == 0:
            csv_providers = load_csv_providers()
            if csv_providers:
                service_docs = providers_to_services(csv_providers)
                if service_docs:
                    await db.services.insert_many(service_docs)
                    print(f"[OK] Imported {len(service_docs)} services from CSV")
                imported_users = 0
                for p in csv_providers:
                    existing = await db.users.find_one({"csv_provider_id": p["csv_provider_id"]})
                    if not existing:
                        user_doc = {
                            **p,
                            "role": "provider",
                            "is_csv_provider": True,
                            "created_at": datetime.utcnow(),
                            "verified_by_admin": p["is_verified"],
                            "specializations": [p["category"].lower()],
                            "quickserve_score": min(100, int(p["rating"] * 20)),
                        }
                        await db.users.insert_one(user_doc)
                        imported_users += 1
                if imported_users:
                    print(f"[OK] Imported {imported_users} provider accounts from CSV")
    except Exception as e:
        print(f"[ERROR] CSV import: {e}")

    print(f"[OK] {settings.APP_NAME} v{settings.VERSION} ready on http://127.0.0.1:{settings.PORT}")


@app.on_event("shutdown")
async def shutdown():
    await close_db()


# ── Register all routers ──────────────────────────────────────────────────
PREFIX = settings.API_PREFIX  # "/api"

# Core: auth, verify, providers, profile
app.include_router(core.router, prefix=PREFIX)

# Dashboards
app.include_router(dashboards.router, prefix=PREFIX)
app.include_router(dashboard.router, prefix=PREFIX)

# Services (full implementation – cities, categories, search, recommendations, nearby, CRUD)
app.include_router(services_router.router, prefix=PREFIX)

# Bookings (full: create, list, detail, status, cancel, emergency)
app.include_router(bookings_router.router, prefix=PREFIX)

# Payments (full: create-intent, confirm, refund, history, wallet, escrow, receipts)
app.include_router(payments_router.router, prefix=PREFIX)

# Slots
app.include_router(slots_router.router, prefix=PREFIX)

# Reviews
app.include_router(reviews_router.router, prefix=PREFIX)

# Tracking
app.include_router(tracking_router.router, prefix=PREFIX)

# Chat (full conversations, messages, unread, quick-replies, search)
app.include_router(chat_router.router, prefix=PREFIX)

# Providers (extended profile, onboarding, active-job, etc.)
app.include_router(providers_router.router, prefix=PREFIX)

# AI features
app.include_router(ai_router.router, prefix=PREFIX)

# Surge pricing
app.include_router(surge_router.router, prefix=PREFIX)

# Gamification
app.include_router(gamification_router.router, prefix=PREFIX)

# Predictive maintenance
app.include_router(predictive_router.router, prefix=PREFIX)

# Mood Sync
app.include_router(mood_sync_router.router, prefix=PREFIX)

# Community
app.include_router(community_router.router, prefix=PREFIX)

# Bundles
app.include_router(bundles_router.router, prefix=PREFIX)

# Events
app.include_router(events_router.router, prefix=PREFIX)

# Skill/Service Swap
app.include_router(swap_router.router, prefix=PREFIX)

# AR Preview
app.include_router(ar_router.router, prefix=PREFIX)

# Lucky Roulette
app.include_router(roulette_router.router, prefix=PREFIX)

# AI Concierge
app.include_router(ai_concierge_router.router, prefix=PREFIX)

# Work Verification
app.include_router(wv_router.router, prefix=PREFIX)

# Aptitude tests
app.include_router(aptitude_router.router, prefix=PREFIX)

# Advanced features
app.include_router(advanced_router.router, prefix=PREFIX)

# Queue
app.include_router(queue_router.router, prefix=PREFIX)

# Admin dashboard (full)
app.include_router(admin_router.router, prefix=PREFIX)

# Features router (legacy catchall for any routes not yet in specialized routers)
app.include_router(features.router, prefix=PREFIX)

# Loyalty, notifications, users, subscriptions, analytics from core_engagement
app.include_router(loyalty_router, prefix=PREFIX)
app.include_router(notifications_router, prefix=PREFIX)
app.include_router(users_router, prefix=PREFIX)
app.include_router(subscriptions_router, prefix=PREFIX)
app.include_router(analytics_router, prefix=PREFIX)
app.include_router(health_router)


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "api_prefix": PREFIX,
    }

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
