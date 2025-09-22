from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from typing import Optional
import uuid
import hashlib
import logging
import time
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "1>|IDheet14rMs")  # Move to environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24*60
REFRESH_TOKEN_EXPIRE_DAYS = 7
INACTIVITY_TIMEOUT_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Token blacklist - for logout (in-memory per service)
TOKEN_BLACKLIST = set()

# User login timestamp tracking - must be consistent across services
USER_LAST_LOGIN = {}  # {user_id: latest_login_timestamp}

def get_current_timestamp():
    """Get current timestamp in seconds"""
    return int(time.time())

def create_token_signature(user_id: int, session_id: str, token_type: str, exp: float, login_timestamp: int) -> str:
    """
    Create a unique signature for the token, using full float precision for exp.
    """
    data = f"{user_id}:{session_id}:{token_type}:{exp}:{login_timestamp}:{SECRET_KEY}"
    signature = hashlib.sha256(data.encode()).hexdigest()[:16]
    logger.info(f"Creating signature with data: {data}")
    logger.info(f"Generated signature: {signature}")
    return signature

def generate_access_token(user_id: int, username: str, role: str, force_logout_others: bool = True):
    """
    Pure token-based generation - no database calls.
    force_logout_others = True means old tokens will be invalidated.
    """
    logger.info(f"Generating tokens for user {user_id}")
    
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    login_timestamp = get_current_timestamp()
    
    # Update user's last login timestamp and clear blacklist for this user
    if force_logout_others:
        USER_LAST_LOGIN[user_id] = login_timestamp
        logger.info(f"User {user_id} new login at {login_timestamp}, previous sessions will be invalidated")
    
    access_exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_exp = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Store exp as timestamp (float) to avoid signature mismatch
    access_exp_timestamp = access_exp.timestamp()
    access_token_payload = {
        "user_id": user_id,
        "role": role or "",
        "username": username,
        "session_id": session_id,
        "exp": access_exp_timestamp,
        "iat": now.timestamp(),
        "last_activity": now.timestamp(),
        "token_type": "access",
        "login_time": now.timestamp(),
        "login_timestamp": login_timestamp,
        "signature": create_token_signature(user_id, session_id, "access", access_exp_timestamp, login_timestamp)
    }
    
    logger.info(f"Access token payload: {access_token_payload}")
    logger.info(f"exp_timestamp during signature creation: {access_exp_timestamp}")
    
    refresh_exp_timestamp = refresh_exp.timestamp()
    refresh_token_payload = {
        "user_id": user_id,
        "role": role or "",
        "username": username,
        "session_id": session_id,
        "exp": refresh_exp_timestamp,
        "iat": now.timestamp(),
        "token_type": "refresh",
        "login_time": now.timestamp(),
        "login_timestamp": login_timestamp,
        "signature": create_token_signature(user_id, session_id, "refresh", refresh_exp_timestamp, login_timestamp)
    }
    
    access_token = jwt.encode(access_token_payload, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token = jwt.encode(refresh_token_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    logger.info(f"Tokens generated successfully for user {user_id} with login_timestamp {login_timestamp}")
    logger.info(f"USER_LAST_LOGIN for user {user_id}: {USER_LAST_LOGIN.get(user_id)}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }

def is_token_from_latest_login(user_id: int, token_login_timestamp: int) -> bool:
    """
    Check if the token is from the latest login session.
    """
    latest_login = USER_LAST_LOGIN.get(user_id)
    
    logger.info(f"Checking login timestamp for user {user_id}: token={token_login_timestamp}, latest={latest_login}")
    
    if latest_login is None:
        logger.info(f"No login record found for user {user_id}, allowing token")
        return True
    
    is_valid = token_login_timestamp >= latest_login
    logger.info(f"Login timestamp check for user {user_id}: {is_valid}")
    return is_valid

def verify_access_token(token: str = Depends(oauth2_scheme)):
    """
    Pure token verification - no database calls.
    Checks login timestamp and signature.
    """
    try:
        if token in TOKEN_BLACKLIST:
            logger.info("Token found in blacklist")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Token has been invalidated"
            )
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_id = payload.get("user_id")
        exp_timestamp = payload.get("exp")
        last_activity = payload.get("last_activity")
        session_id = payload.get("session_id")
        token_type = payload.get("token_type", "access")
        login_time = payload.get("login_time")
        token_signature = payload.get("signature")
        login_timestamp = payload.get("login_timestamp")
        
        logger.info(f"Verifying token for user {user_id}, login_timestamp: {login_timestamp}")
        logger.info(f"Payload extracted: {payload}")
        logger.info(f"exp_timestamp during verification: {exp_timestamp}")
        
        if not all([user_id, exp_timestamp, last_activity, session_id]):
            logger.error("Token missing required fields")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token format"
            )
        
        if token_type != "access":
            logger.error(f"Invalid token type: {token_type}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Ensure exp_timestamp is a float
        if isinstance(exp_timestamp, datetime):
            exp_timestamp = exp_timestamp.timestamp()
        exp_timestamp = float(exp_timestamp)
        
        if login_timestamp is not None:
            if not is_token_from_latest_login(user_id, login_timestamp):
                logger.info(f"Token rejected for user {user_id}: not from latest login session")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session invalidated by new login"
                )
        
        if token_signature:
            expected_signature = create_token_signature(user_id, session_id, "access", exp_timestamp, login_timestamp or 0)
            if token_signature != expected_signature:
                logger.error(f"Token signature mismatch for user {user_id}. Expected: {expected_signature}, Got: {token_signature}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token signature invalid"
                )
        
        current_time = datetime.now(timezone.utc)
        current_timestamp = current_time.timestamp()
        
        if current_timestamp > exp_timestamp:
            logger.info(f"Token expired for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Token has expired"
            )
        
        inactivity_duration = current_timestamp - last_activity
        if inactivity_duration > INACTIVITY_TIMEOUT_MINUTES * 60:
            TOKEN_BLACKLIST.add(token)
            logger.info(f"Token inactive for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Session expired due to inactivity"
            )
        
        logger.info(f"Token verified successfully for user {user_id}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.info("Token expired (JWT level)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except JWTError as e:
        logger.error(f"JWT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token"
        )

async def refresh_access_token(refresh_token: str):
    """
    Pure token-based refresh - no database calls.
    Checks login timestamp and signature.
    """
    try:
        if refresh_token in TOKEN_BLACKLIST:
            logger.info("Refresh token found in blacklist")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been invalidated"
            )
        
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_id = payload.get("user_id")
        username = payload.get("username")
        role = payload.get("role")
        session_id = payload.get("session_id")
        token_type = payload.get("token_type", "refresh")
        exp_timestamp = payload.get("exp")
        login_time = payload.get("login_time")
        token_signature = payload.get("signature")
        login_timestamp = payload.get("login_timestamp")
        
        logger.info(f"Refreshing token for user {user_id}, login_timestamp: {login_timestamp}")
        
        if not all([user_id, username, session_id]):
            logger.error("Refresh token missing required fields")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid refresh token"
            )
        
        if token_type != "refresh":
            logger.error(f"Invalid refresh token type: {token_type}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for refresh"
            )
        
        if isinstance(exp_timestamp, datetime):
            exp_timestamp = exp_timestamp.timestamp()
        exp_timestamp = float(exp_timestamp)
        
        if login_timestamp is not None:
            if not is_token_from_latest_login(user_id, login_timestamp):
                logger.info(f"Refresh token rejected for user {user_id}: not from latest login session")
                TOKEN_BLACKLIST.add(refresh_token)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session invalidated by new login"
                )
        
        if token_signature:
            expected_signature = create_token_signature(user_id, session_id, "refresh", exp_timestamp, login_timestamp or 0)
            if token_signature != expected_signature:
                logger.error(f"Refresh token signature mismatch for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token signature invalid"
                )
        
        current_time = datetime.now(timezone.utc)
        if current_time.timestamp() > exp_timestamp:
            TOKEN_BLACKLIST.add(refresh_token)
            logger.info(f"Refresh token expired for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Refresh token has expired"
            )
        
        now = datetime.now(timezone.utc)
        new_access_exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_refresh_exp = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_access_exp_timestamp = new_access_exp.timestamp()
        new_access_token_payload = {
            "user_id": user_id,
            "role": role,
            "username": username,
            "session_id": session_id,
            "exp": new_access_exp_timestamp,
            "iat": now.timestamp(),
            "last_activity": now.timestamp(),
            "token_type": "access",
            "login_time": login_time,
            "login_timestamp": login_timestamp,
            "signature": create_token_signature(user_id, session_id, "access", new_access_exp_timestamp, login_timestamp or 0)
        }
        
        new_refresh_exp_timestamp = new_refresh_exp.timestamp()
        new_refresh_token_payload = {
            "user_id": user_id,
            "role": role,
            "username": username,
            "session_id": session_id,
            "exp": new_refresh_exp_timestamp,
            "iat": now.timestamp(),
            "token_type": "refresh",
            "login_time": login_time,
            "login_timestamp": login_timestamp,
            "signature": create_token_signature(user_id, session_id, "refresh", new_refresh_exp_timestamp, login_timestamp or 0)
        }
        
        new_access_token = jwt.encode(new_access_token_payload, SECRET_KEY, algorithm=ALGORITHM)
        new_refresh_token = jwt.encode(new_refresh_token_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        TOKEN_BLACKLIST.add(refresh_token)
        
        logger.info(f"Tokens refreshed successfully for user {user_id}")
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token
        }
        
    except jwt.ExpiredSignatureError:
        logger.info("Refresh token expired (JWT level)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Refresh token has expired"
        )
    except JWTError as e:
        logger.error(f"Refresh token JWT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid refresh token"
        )

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current user from token - no database call.
    """
    payload = verify_access_token(token)
    user_id = payload.get("user_id")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token"
        )
    
    return user_id

def get_current_role(token: str = Depends(oauth2_scheme)):
    """
    Get current user role from token - no database call.
    """
    try:
        payload = verify_access_token(token)
        return payload.get("role", "")
    except:
        return None

def get_current_username(token: str = Depends(oauth2_scheme)):
    """
    Get current username from token - no database call.
    """
    try:
        payload = verify_access_token(token)
        return payload.get("username", "")
    except:
        return None

def get_session_info(token: str = Depends(oauth2_scheme)):
    """
    Get complete session info from token - no database call.
    """
    payload = verify_access_token(token)
    
    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("username"),
        "role": payload.get("role"),
        "session_id": payload.get("session_id"),
        "login_time": payload.get("login_time"),
        "last_activity": payload.get("last_activity"),
        "login_timestamp": payload.get("login_timestamp")
    }

def require_role(allowed_roles: list):
    """
    Role-based access control from token - no database call.
    """
    def wrapper(token: str = Depends(oauth2_scheme)):
        payload = verify_access_token(token)
        role = payload.get("role", "")
        
        if not role:
            raise HTTPException(
                status_code=403,
                detail="No role assigned"
            )
        
        if str(role).lower() not in [str(allowed_role).lower() for allowed_role in allowed_roles]:
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions"
            )
        
        return role
    
    return wrapper

def logout_user(token: str = Depends(oauth2_scheme)):
    """
    Logout by adding tokens to blacklist - no database call.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        login_timestamp = payload.get("login_timestamp")
        
        TOKEN_BLACKLIST.add(token)
        
        logger.info(f"User {user_id} logged out successfully")
        
        return {
            "message": "Logged out successfully",
            "user_id": user_id
        }
        
    except JWTError:
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

def force_logout_all_sessions(user_id: int):
    """
    Force logout all sessions for a user by updating their login timestamp.
    """
    USER_LAST_LOGIN[user_id] = get_current_timestamp()
    
    logger.info(f"All sessions force logged out for user {user_id}")
    
    return {"message": f"All sessions invalidated for user {user_id}"}

def invalidate_all_user_sessions(user_id: int, current_token: str = None):
    """
    Invalidate all sessions for a user (e.g., when logging in from another device).
    """
    return force_logout_all_sessions(user_id)

def is_token_valid_format(token: str) -> bool:
    """
    Check if token has valid format without full verification.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        required_fields = ["user_id", "session_id", "token_type"]
        return all(field in payload for field in required_fields)
    except:
        return False

def get_token_info(token: str) -> dict:
    """
    Get token information without verification (for debugging).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        user_id = payload.get("user_id")
        login_timestamp = payload.get("login_timestamp")
        
        return {
            "user_id": user_id,
            "username": payload.get("username"),
            "role": payload.get("role"),
            "token_type": payload.get("token_type"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "session_id": payload.get("session_id"),
            "login_timestamp": login_timestamp,
            "is_blacklisted": token in TOKEN_BLACKLIST,
            "is_from_latest_login": is_token_from_latest_login(user_id, login_timestamp or 0) if user_id else False,
            "latest_login_in_memory": USER_LAST_LOGIN.get(user_id) if user_id else None
        }
    except:
        return {"error": "Invalid token format"}

def clean_blacklist():
    """
    Clean expired tokens from blacklist (optional background task).
    """
    current_time = datetime.now(timezone.utc).timestamp()
    
    if len(TOKEN_BLACKLIST) > 10000:
        TOKEN_BLACKLIST.clear()
        logger.info("Token blacklist cleared due to size")

def clean_old_login_records(max_records: int = 10000):
    """
    Clean old login records to prevent memory issues.
    """
    if len(USER_LAST_LOGIN) > max_records:
        sorted_records = sorted(USER_LAST_LOGIN.items(), key=lambda x: x[1], reverse=True)
        USER_LAST_LOGIN.clear()
        USER_LAST_LOGIN.update(dict(sorted_records[:max_records//2]))
        logger.info("Old login records cleaned")

def extend_session_activity(token: str) -> str:
    """
    Extend session activity by generating new token with updated last_activity.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("token_type") != "access":
            raise HTTPException(status_code=400, detail="Can only extend access tokens")
        
        user_id = payload.get("user_id")
        login_timestamp = payload.get("login_timestamp")
        
        if login_timestamp and not is_token_from_latest_login(user_id, login_timestamp):
            raise HTTPException(status_code=401, detail="Session invalidated by new login")
        
        payload["last_activity"] = datetime.now(timezone.utc).timestamp()
        
        new_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        TOKEN_BLACKLIST.add(token)
        
        return new_token
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token for activity extension")

def create_login_response(user_id: int, username: str, role: str):
    """
    Complete login response helper.
    Automatically invalidates old sessions.
    """
    tokens = generate_access_token(user_id, username, role, force_logout_others=True)
    
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_info": {
            "user_id": user_id,
            "username": username,
            "role": role
        }
    }

def sync_user_login_timestamp(user_id: int, login_timestamp: int):
    """
    Sync login timestamp across services (optional).
    """
    USER_LAST_LOGIN[user_id] = login_timestamp
    logger.info(f"Login timestamp synced for user {user_id}: {login_timestamp}")

def get_user_last_login(user_id: int) -> Optional[int]:
    """
    Get user's last login timestamp.
    """
    return USER_LAST_LOGIN.get(user_id)

def clear_all_login_records():
    """
    Clear all login records (for testing/debugging).
    """
    USER_LAST_LOGIN.clear()
    logger.info("All login records cleared")

def clear_blacklist():
    """
    Clear token blacklist (for testing/debugging).
    """
    TOKEN_BLACKLIST.clear()
    logger.info("Token blacklist cleared")

def debug_user_status(user_id: int):
    """
    Debug function to check user's current status.
    """
    return {
        "user_id": user_id,
        "latest_login_timestamp": USER_LAST_LOGIN.get(user_id),
        "blacklist_size": len(TOKEN_BLACKLIST),
        "login_records_count": len(USER_LAST_LOGIN)
    }