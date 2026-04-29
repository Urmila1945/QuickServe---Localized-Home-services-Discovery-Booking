# -*- coding: utf-8 -*-
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import random

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "QuickServe"

CATEGORIES = [
    {"name": "Plumbing", "icon": "🔧", "description": "Professional plumbing services"},
    {"name": "Electrical", "icon": "⚡", "description": "Licensed electricians"},
    {"name": "Cleaning", "icon": "🧹", "description": "Home and office cleaning"},
    {"name": "Beauty & Salon", "icon": "💇", "description": "Beauty and grooming services"},
    {"name": "Fitness Training", "icon": "💪", "description": "Personal fitness trainers"},
    {"name": "Delivery Services", "icon": "🚚", "description": "Fast delivery services"},
    {"name": "Appliance Repair", "icon": "🔨", "description": "Repair all appliances"},
    {"name": "Home Tutoring", "icon": "📚", "description": "Expert tutors"},
    {"name": "Carpentry", "icon": "🪚", "description": "Skilled carpenters"},
    {"name": "Painting", "icon": "🎨", "description": "Professional painters"},
    {"name": "Gardening", "icon": "🌱", "description": "Garden maintenance"},
    {"name": "Pest Control", "icon": "🐛", "description": "Pest elimination"}
]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]

async def init_database():
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        
        print("=" * 50)
        print("  Initializing QuickServe Database")
        print("=" * 50)
        
        # Create categories
        print("\n[1/3] Creating categories...")
        await db.categories.delete_many({})
        await db.categories.insert_many(CATEGORIES)
        print(f"Created {len(CATEGORIES)} categories")
        
        # Create sample services
        print("\n[2/3] Creating sample services...")
        await db.services.delete_many({})
        services = []
        for i in range(100):
            category = random.choice(CATEGORIES)
            city = random.choice(CITIES)
            services.append({
                "name": f"{category['name']} Service {i+1}",
                "category": category["name"],
                "description": f"Professional {category['name'].lower()} service in {city}",
                "price": random.randint(200, 2000),
                "duration": random.choice([30, 60, 90, 120]),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "location": {"city": city, "area": f"Area {random.randint(1, 10)}"},
                "created_at": datetime.utcnow()
            })
        await db.services.insert_many(services)
        print(f"Created {len(services)} services")
        
        # Create indexes
        print("\n[3/3] Creating indexes...")
        await db.users.create_index("email", unique=True)
        await db.services.create_index("category")
        await db.bookings.create_index("user_id")
        await db.bookings.create_index("provider_id")
        print("Indexes created")
        
        print("\n" + "=" * 50)
        print("  Database initialization complete!")
        print("=" * 50)
        print(f"\nDatabase: {DATABASE_NAME}")
        print(f"Collections: users, services, bookings, payments, reviews, etc.")
        print(f"Sample data: {len(CATEGORIES)} categories, {len(services)} services")
        
        client.close()
        
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure MongoDB is running on localhost:27017")

if __name__ == "__main__":
    asyncio.run(init_database())
