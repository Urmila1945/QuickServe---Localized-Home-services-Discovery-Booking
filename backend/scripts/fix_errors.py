import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def fix_database_issues():
    """Fix common database issues causing 500 errors"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.quickserve
    
    print("Checking and fixing database issues...")
    
    # 1. Ensure admin user exists
    admin = await db.users.find_one({"email": "admin@quickserve.com"})
    if not admin:
        print("Creating admin user...")
        from middleware.auth import hash_password
        await db.users.insert_one({
            "email": "admin@quickserve.com",
            "password": hash_password("admin123"),
            "full_name": "Admin User",
            "phone": "+91-0000000000",
            "role": "admin",
            "created_at": datetime.utcnow(),
            "verified_email": True,
            "verified_by_admin": True
        })
        print("✓ Admin user created")
    else:
        print("✓ Admin user exists")
    
    # 2. Ensure collections exist
    collections = await db.list_collection_names()
    required = ["users", "services", "bookings", "rewards", "disputes"]
    
    for coll in required:
        if coll not in collections:
            await db.create_collection(coll)
            print(f"✓ Created collection: {coll}")
    
    # 3. Fix user data issues
    print("\nFixing user data...")
    await db.users.update_many(
        {"quickserve_credits": {"$exists": False}},
        {"$set": {"quickserve_credits": 0}}
    )
    
    await db.users.update_many(
        {"available_balance": {"$exists": False}},
        {"$set": {"available_balance": 0}}
    )
    
    print("✓ User data fixed")
    
    # 4. Check services
    service_count = await db.services.count_documents({})
    print(f"\n✓ Services in database: {service_count}")
    
    if service_count == 0:
        print("⚠ No services found. Run import_csv.py to import data.")
    
    # 5. Create system config if not exists
    kill_switch = await db.system_config.find_one({"key": "kill_switch"})
    if not kill_switch:
        await db.system_config.insert_one({
            "key": "kill_switch",
            "enabled": False,
            "zone": None,
            "reason": "",
            "activated_at": None
        })
        print("✓ System config initialized")
    
    print("\n✅ Database check complete!")
    client.close()

if __name__ == "__main__":
    asyncio.run(fix_database_issues())
