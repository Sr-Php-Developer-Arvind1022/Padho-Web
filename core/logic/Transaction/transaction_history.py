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
        db = get_db()
        col = db["transactions"]
        wallet_col = db["wallet"]

        # ---- Basic validation ----
        amount = abs(float(transaction.get("amount", 0)))
        transaction_type = transaction.get("transaction_type", "").lower()

        if transaction_type not in ["credit", "debit"]:
            return {"status": "error", "detail": "Invalid transaction type"}

        # ---- Get wallet ----
        wallet = wallet_col.find_one({"user_id": user_id})
        current_balance = wallet.get("balance", 0) if wallet else 0

        # ---- Insufficient balance check ----
        if transaction_type == "debit" and current_balance < amount:
            return {"status": "error", "detail": "Insufficient balance"}

        # ---- Opening & Closing Balance ----
        opening_balance = current_balance

        if transaction_type == "credit":
            closing_balance = current_balance + amount
        else:
            closing_balance = current_balance - amount

        # ---- Prepare transaction ----
        transaction["user_id"] = user_id
        transaction["amount"] = amount
        transaction["transaction_type"] = transaction_type
        transaction["opening_balance"] = opening_balance
        transaction["closing_balance"] = closing_balance
        transaction["created_at"] = datetime.utcnow().isoformat()

        print(f"Saving transaction: {transaction}")

        # ---- Insert transaction ----
        result = col.insert_one(transaction)

        # ---- Update wallet (upsert safe) ----
        wallet_col.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "balance": closing_balance,
                    "updated_at": datetime.utcnow().isoformat()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            upsert=True
        )

        return {
            "status": "success",
            "inserted_id": str(result.inserted_id),
            "opening_balance": opening_balance,
            "closing_balance": closing_balance
        }

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
