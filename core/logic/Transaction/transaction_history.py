import os
import logging
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError


logger = logging.getLogger(__name__)


MONGO_URI = "mongodb+srv://arvind:arvind123@cluster0.d3e8kz2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "transaction_db"
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set")
    
#DB_NAME = os.getenv("DB_NAME", "transaction_db")


_client = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DB_NAME]


def SaveTransaction(user_id: str, transaction: dict) -> dict:
    try:
        col = get_db()["transactions"]
        wallet_col = get_db()["wallet"]
        transaction["user_id"] = user_id
        transaction["created_at"] = datetime.utcnow().isoformat()
        print(f"Saving transaction for user_id={user_id}: {transaction}")
        result = col.insert_one(transaction)
        # Wallet logic
        amount = float(transaction.get("amount", 0))
        transaction_type = transaction.get("transaction_type", "").lower()

        # Check wallet exists
        wallet = wallet_col.find_one({"user_id": user_id})

        if not wallet:
            balance = amount if transaction_type == "credit" else -amount

            wallet_col.insert_one({
                "user_id": user_id,
                "balance": balance,
                "created_at": datetime.utcnow().isoformat()
            })

        else:
            if transaction_type == "credit":
                wallet_col.update_one(
                    {"user_id": user_id},
                    {"$inc": {"balance": amount}}
                )
            elif transaction_type == "debit":
                wallet_col.update_one(
                    {"user_id": user_id},
                    {"$inc": {"balance": -amount}}
                )
        return {"status": "success", "inserted_id": str(result.inserted_id)}
    except PyMongoError as e:
        logger.error(f"SaveTransaction error: {e}")
        return {"status": "error", "detail": str(e)}

def GetTransactionHistory(user_id: str, limit: int = 50, skip: int = 0) -> dict:
    try:
        col = get_db()["transactions"]
        transactions = list(col.find({"user_id": user_id}, {"_id": 0}).skip(skip).limit(limit))
        total_credits = sum(t.get("amount", 0) for t in transactions if t.get("transaction_type") == "credit")
        total_debits = sum(t.get("amount", 0) for t in transactions if t.get("transaction_type") == "debit")
        transactions.append({"total_credits": total_credits})
        transactions.append({"total_debits": total_debits})
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
