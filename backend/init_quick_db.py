import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "quickserve"

async def init_services():
    print("🚀 Initializing QuickServe Services...")
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB")
        
        # Clear existing services
        await db.services.delete_many({})
        print("🧹 Cleared existing services")
        
        # Sample services data
        services = [
            {
                "name": "Professional Plumbing Service",
                "category": "Plumbing",
                "description": "Expert plumbing services for all your needs",
                "price": 500,
                "duration": 60,
                "rating": 4.5,
                "provider_id": "provider1",
                "provider_name": "John Doe",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Electrical Repair Service",
                "category": "Electrical",
                "description": "Licensed electrician for home and office",
                "price": 600,
                "duration": 90,
                "rating": 4.7,
                "provider_id": "provider2",
                "provider_name": "Jane Smith",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Home Cleaning Service",
                "category": "Cleaning",
                "description": "Professional home cleaning and sanitization",
                "price": 800,
                "duration": 120,
                "rating": 4.8,
                "provider_id": "provider3",
                "provider_name": "Mike Johnson",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Beauty & Salon Services",
                "category": "Beauty & Salon",
                "description": "Professional beauty and grooming services",
                "price": 1000,
                "duration": 90,
                "rating": 4.6,
                "provider_id": "provider4",
                "provider_name": "Sarah Williams",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Personal Fitness Training",
                "category": "Fitness Training",
                "description": "Certified personal trainer for home workouts",
                "price": 1500,
                "duration": 60,
                "rating": 4.9,
                "provider_id": "provider5",
                "provider_name": "David Brown",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Fast Delivery Service",
                "category": "Delivery Services",
                "description": "Quick and reliable delivery services",
                "price": 200,
                "duration": 30,
                "rating": 4.4,
                "provider_id": "provider6",
                "provider_name": "Tom Wilson",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Appliance Repair Expert",
                "category": "Appliance Repair",
                "description": "Expert repair for all home appliances",
                "price": 700,
                "duration": 90,
                "rating": 4.5,
                "provider_id": "provider7",
                "provider_name": "Robert Davis",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Home Tutoring Service",
                "category": "Home Tutoring",
                "description": "Experienced tutor for all subjects",
                "price": 500,
                "duration": 60,
                "rating": 4.7,
                "provider_id": "provider8",
                "provider_name": "Emily Taylor",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Carpentry Services",
                "category": "Carpentry",
                "description": "Custom carpentry and furniture repair",
                "price": 900,
                "duration": 120,
                "rating": 4.6,
                "provider_id": "provider9",
                "provider_name": "James Anderson",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Professional Painting",
                "category": "Painting",
                "description": "Interior and exterior painting services",
                "price": 1200,
                "duration": 180,
                "rating": 4.8,
                "provider_id": "provider10",
                "provider_name": "Chris Martin",
                "location": {"type": "Point", "coordinates": [72.8777, 19.0760]},
                "city": "Mumbai",
                "is_active": True,
                "created_at": datetime.utcnow()
            }
        ]
        
        # Insert services
        result = await db.services.insert_many(services)
        print(f"✅ Inserted {len(result.inserted_ids)} services")
        
        # Create categories
        await db.categories.delete_many({})
        categories = [
            {"name": "Plumbing", "icon": "🔧", "description": "Professional plumbing services"},
            {"name": "Electrical", "icon": "⚡", "description": "Licensed electrical work"},
            {"name": "Cleaning", "icon": "🧹", "description": "Home and office cleaning"},
            {"name": "Beauty & Salon", "icon": "💄", "description": "Beauty and grooming services"},
            {"name": "Fitness Training", "icon": "💪", "description": "Personal fitness training"},
            {"name": "Delivery Services", "icon": "📦", "description": "Fast delivery services"},
            {"name": "Appliance Repair", "icon": "🔨", "description": "Appliance repair services"},
            {"name": "Home Tutoring", "icon": "📚", "description": "Educational tutoring"},
            {"name": "Carpentry", "icon": "🪚", "description": "Carpentry and woodwork"},
            {"name": "Painting", "icon": "🎨", "description": "Painting services"},
            {"name": "Gardening", "icon": "🌱", "description": "Garden maintenance"},
            {"name": "Pest Control", "icon": "🐛", "description": "Pest control services"}
        ]
        
        result = await db.categories.insert_many(categories)
        print(f"✅ Inserted {len(result.inserted_ids)} categories")
        
        # Create indexes
        await db.services.create_index([("location", "2dsphere")])
        await db.services.create_index("category")
        await db.services.create_index("rating")
        print("✅ Created indexes")
        
        print("\n🎉 Database initialized successfully!")
        print(f"📊 Total Services: {await db.services.count_documents({})}")
        print(f"📊 Total Categories: {await db.categories.count_documents({})}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(init_services())
