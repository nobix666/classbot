import os
import logging
import certifi
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

DB_NAME = "ClassBotDB"

client = None
db = None

async def connect_db():
    global client, db
    
    # 👈 ပြင်ဆင်ချက်: Function အထဲရောက်မှ MONGO_URI ကို ဖတ်ခိုင်းခြင်း
    MONGO_URI = os.getenv("MONGO_URI")
    
    if not MONGO_URI:
        logger.error("❌ MONGO_URI not found in .env file!")
        return
    
    try:
        logger.info("Connecting to MongoDB Atlas...")
        client = AsyncIOMotorClient(
            MONGO_URI, 
            tls=True, 
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000
        )
        db = client[DB_NAME]
        
        await client.admin.command('ping')
        logger.info("✅ MongoDB Connected Successfully!")
    except Exception as e:
        logger.error(f"❌ MongoDB Connection Error: {e}")

def get_db():
    return db