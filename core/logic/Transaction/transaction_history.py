import os
import logging
from datetime import datetime
from unittest import result
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import re
from bson import ObjectId

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
        transaction['is_deleted'] = False
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
        result = {}
        col = get_db()["transactions"]

        #  Filter (exclude deleted)
        query = {
            "user_id": user_id,
            "is_deleted": {"$ne": True}
        }

        # Fetch transactions
        transactions = list(
            col.find(query, {"_id": 0})
            .skip(skip)
            .limit(limit)
        )

        # Totals
        total_credits = 0
        total_debits = 0

        for t in transactions:
            amount = float(t.get("amount", 0))

            if t.get("transaction_type") == "credit":
                total_credits += amount
            elif t.get("transaction_type") == "debit":
                total_debits += amount

            # Item parsing (only real transactions)
            items = t.get("items", "")
            if not items:
                continue

            for part in items.split(','):
                part = part.strip()
                if not part:
                    continue

                qty_match = re.search(r'\d+', part)
                if not qty_match:
                    continue

                qty = int(qty_match.group())
                name = re.sub(r'\d+', '', part).strip().lower()

                key = name.split()[-1]

                if key.endswith('es'):
                    key = key[:-2]
                elif key.endswith('s'):
                    key = key[:-1]

                result[key] = result.get(key, 0) + qty

        
        return {
            "status": "success",
            "transactions": transactions,
            "total_credits": total_credits,
            "total_debits": total_debits,
            "summary": {
                "item_summary": result
            },
            "total_count": col.count_documents(query),  # correct count
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
    
async def DeleteTransaction(user_id: str, transaction_id: str) -> dict:
    try:
        db = get_db()
        trans_col = db["transactions"]
        wallet_col = db["wallet"]

        # Step 1: Get transaction (ignore already deleted)
        transaction = trans_col.find_one({
            "transaction_id": transaction_id,
            "user_id": user_id,
            "is_deleted": {"$ne": True}
        })

        if not transaction:
            return {"status": "error", "message": "Transaction not found or already deleted"}

        amount = float(transaction.get("amount", 0))
        trans_type = transaction.get("transaction_type")

        # Step 2: Get wallet
        wallet = wallet_col.find_one({"user_id": user_id})
        if not wallet:
            return {"status": "error", "message": "Wallet not found"}

        balance = float(wallet.get("balance", 0))

        # Step 3: Reverse wallet
        if trans_type == "credit":
            new_balance = balance - amount
        elif trans_type == "debit":
            new_balance = balance + amount
        else:
            return {"status": "error", "message": "Invalid transaction type"}

        # Step 4: Update wallet
        wallet_col.update_one(
            {"user_id": user_id},
            {"$set": {"balance": new_balance}}
        )

        # Step 5: Soft delete
        trans_col.update_one(
            {"_id": transaction["_id"]},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow()
                }
            }
        )

        return {
            "status": "success",
            "message": "Transaction soft deleted & wallet updated",
            "new_balance": new_balance
        }

    except PyMongoError as e:
        logger.error(f"DeleteTransaction error: {e}")
        return {"status": "error", "detail": str(e)}