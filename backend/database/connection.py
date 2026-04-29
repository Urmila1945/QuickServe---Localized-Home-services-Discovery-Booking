from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client = None
db = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    # helper for creating indexes to avoid stopping the whole process on conflict
    async def create_index(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except Exception as e:
            # Handle index conflict code 86 (IndexKeySpecsConflict) or other mismatches
            if "IndexKeySpecsConflict" in str(e) or "already exists with different options" in str(e):
                try:
                    # Try to find the name of the conflicting index and drop it
                    # Usually it is "field_1" for single field indexes
                    name = kwargs.get("name")
                    if not name and isinstance(args[0], str):
                        name = f"{args[0]}_1"
                    if name:
                        await collection.drop_index(name)
                        await collection.create_index(*args, **kwargs)
                        print(f"[OK] Re-created index with new options for {args[0]}")
                    else:
                        print(f"[WARN] Could not determine index name to drop for {args[0]}")
                except Exception as drop_error:
                    print(f"[ERROR] Failed to drop and recreate index: {drop_error}")
            elif "DuplicateKeyError" in str(e) or "E11000" in str(e):
                print(f"[ERROR] Cannot create unique index on {args[0]} because duplicate values exist: {e}")
            else:
                print(f"[WARN] Failed to create index for {args[0]}: {e}")

    # Create indexes for better performance on large datasets
    await create_index(db.users, "email", unique=True)
    await create_index(db.users, "role")
    await create_index(db.users, "city")
    
    await create_index(db.bookings, "status")
    await create_index(db.bookings, "customer_id")
    await create_index(db.bookings, "provider_id")
    await create_index(db.bookings, "created_at")
    
    await create_index(db.services, "category")
    await create_index(db.services, "city")
    await create_index(db.services, "is_csv_imported")
    
    print(f"[OK] Connected to MongoDB: {settings.DATABASE_NAME}")

async def close_db():
    global client
    if client:
        client.close()
        print("[DISCONNECTED] MongoDB connection closed")

def get_db():
    return db
