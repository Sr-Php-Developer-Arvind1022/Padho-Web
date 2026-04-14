import os
import logging
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError


logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI","mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set")
    
DB_NAME = os.getenv("DB_NAME", "transaction_db")


_client = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DB_NAME]


def SaveTransaction(user_id: str, transaction: dict) -> dict:
    try:
        col = get_db()["transactions"]
        transaction["user_id"] = user_id
        transaction["created_at"] = datetime.utcnow().isoformat()
        result = col.insert_one(transaction)
        return {"status": "success", "inserted_id": str(result.inserted_id)}
    except PyMongoError as e:
        logger.error(f"SaveTransaction error: {e}")
        return {"status": "error", "detail": str(e)}


def GetTransactionHistory(user_id: str, limit: int = 50, skip: int = 0) -> dict:
    try:
        col = get_db()["transactions"]
        transactions = list(col.find({"user_id": user_id}, {"_id": 0}).skip(skip).limit(limit))
        return {
            "status": "success",
            "transactions": transactions,
            "total_count": col.count_documents({"user_id": user_id}),
            "limit": limit,
            "skip": skip
        }
    except PyMongoError as e:
        logger.error(f"GetTransactionHistory error: {e}")
        return {
            "status": "error",
            "transactions": [],
            "detail": str(e)
        }
