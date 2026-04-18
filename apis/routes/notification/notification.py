from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from apis.Notification.notifications import save_notification, send_notification_2, save_fcm_token as save_fcm_token_db

router = APIRouter(prefix="/notification", tags=["Notification"])


class NotificationRequest(BaseModel):
    fcm_token: str
    title: str
    body: str
    data: Optional[dict] = None


class SaveNotificationRequest(BaseModel):
    user_id: int
    title: str
    body: str
    notification_type: Optional[str] = "general"


@router.post("/send")
async def send_notification(request: NotificationRequest):
    """
    Send a notification via Firebase Cloud Messaging
    
    Args:
        fcm_token: Firebase Cloud Messaging token
        title: Notification title
        body: Notification body
        data: Optional additional data
    
    Returns:
        Response from FCM server
    """
    try:
        result = send_notification_2(
            fcm_token=request.fcm_token,
            title=request.title,
            body=request.body,
            data=request.data
        )
        print(f"Notification send result: {result}")
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_notification_endpoint(request: SaveNotificationRequest):
    """
    Save notification to database
    
    Args:
        user_id: User ID
        title: Notification title
        body: Notification body
        notification_type: Type of notification
    
    Returns:
        Success status
    """
    try:
        success = save_notification(
            user_id=request.user_id,
            title=request.title,
            body=request.body,
            notification_type=request.notification_type
        )
        
        if success:
            return {"success": True, "message": "Notification saved successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save notification")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-and-save")
async def send_and_save_notification(
    user_id: int,
    fcm_token: str,
    title: str,
    body: str,
    notification_type: str = "general",
    data: Optional[dict] = None
):
    """
    Send notification and save it to database
    """
    try:
        # Save to database
        save_notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type
        )
        
        # Send via FCM
        result = send_notification_2(
            fcm_token=fcm_token,
            title=title,
            body=body,
            data=data
        )
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/save_fcm_token")
async def save_fcm_token(user_id: int, fcm_token: str):
    """
    Save FCM token for a user
    """
    try:
        # Here you would save the fcm_token to your database associated with the user_id
        # For example:
        # db.users.update_one({"user_id": user_id}, {"$set": {"fcm_token": fcm_token}}, upsert=True)
        
        result = save_fcm_token_db(user_id, fcm_token)
        return {"success": True, "message": "FCM token saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))