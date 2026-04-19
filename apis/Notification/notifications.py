import firebase_admin
from firebase_admin import credentials, messaging
from datetime import datetime
import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MONGO_URI = "mongodb+srv://arvind:arvind123@cluster0.d3e8kz2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set")
    
DB_NAME = "transaction_db"

_client = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DB_NAME]


# 🔑 Service Account JSON path
firebase_config = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "token_uri": "https://oauth2.googleapis.com/token",
}
# print(firebase_config)
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)


def save_notification(user_id: int, title: str, body: str, notification_type: str = "general"):
    try:
        col = get_db()["notifications"]

        notification_data = {
            "title": title,
            "body": body,
            "type": notification_type,
            "timestamp": datetime.now().isoformat(),
            "is_read": False
        }

        result = col.update_one(
            {"user_id": user_id},          # 🔍 condition
            {"$set": notification_data},   # ✏️ update data
            upsert=True                    # 🔥 insert if not exists
        )

        logger.info(f"Notification upserted for user_id={user_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving notification: {str(e)}")
        return False


def send_notification_2(fcm_token: str, title: str, body: str, data: dict = None):
    try:
        print(f"Sending notification to token: {fcm_token}")
        logger.info(f"Sending notification to token: {fcm_token}")

        android = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                priority="high",
                channel_id="high_priority",
                sound="default"
            )
        )

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            android=android,   # ✅ MOST IMPORTANT LINE
            token=fcm_token,
            data=data or {}
        )

        response = messaging.send(message)

        return {
            "success": True,
            "message_id": response
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
def send_notification(fcm_token: str = None, title: str = None, body: str = None):
    token = fcm_token
    notification_title = title or "🔥 BoloApp"
    notification_body = body or "Python se notification aa gaya"

    return send_notification_2(
        fcm_token=token,
        title=notification_title,
        body=notification_body
    )
def save_fcm_token(user_id: int, fcm_token: str):
    try:
        col = get_db()["user_fcm_tokens"]

        result = col.update_one(
            {"user_id": user_id},   # 🔍 same user check
            {
                "$set": {
                    "fcm_token": fcm_token,
                    "updated_at": datetime.now().isoformat()
                }
            },
            upsert=True  # 🔥 insert if not exists
        )
        print(f"FCM token saved/updated for user_id={user_id}")
        logger.info(f"FCM token saved/updated for user_id={user_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving FCM token: {str(e)}")
        return False
