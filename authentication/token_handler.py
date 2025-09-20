from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import pytz
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from typing import Optional

# JWT Configuration
SECRET_KEY = "1>|IDheet14rMs"  # Read from config file
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# OAuth2PasswordBearer instance to handle token from header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=True)


# def generate_access_token(email: str) -> str:
#     """Generate a JWT access token for the given email."""
#     # Calculate expiration time in UTC first
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
#     # Convert UTC to IST (Asia/Kolkata)
#     ist = pytz.timezone('Asia/Kolkata')
#     expire = expire.replace(tzinfo=pytz.utc).astimezone(ist)
#     print(expire)
#     payload = {
#         "sub": email,
#         "exp": expire,
#         "type": "access"
#     }
#     return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# def generate_refresh_token(email: str) -> str:
#     """Generate a JWT refresh token for the given email."""
#     expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
#     # Convert UTC to IST (Asia/Kolkata)
#     ist = pytz.timezone('Asia/Kolkata')
#     expire = expire.replace(tzinfo=pytz.utc).astimezone(ist)
#     print(expire)
#     payload = {
#         "sub": email,
#         "exp": expire,
#         "type": "refresh"
#     }
#     return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# def verify_token(token: str) -> dict:
#     """Verify a JWT token and return its payload if valid."""
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         return payload
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token has expired",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     except jwt.JWTClaimsError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token has invalid claims",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     except jwt.JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token",
#             headers={"WWW-Authenticate": "Bearer"},
#         )


# async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
#     """Dependency to get current user from token using OAuth2PasswordBearer."""
#     payload = verify_token(token)
#     email: Optional[str] = payload.get("sub")
#     token_type: Optional[str] = payload.get("type")
    
#     if email is None or token_type != "access":
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return {"email": email}

INACTIVITY_TIMEOUT_MINUTES = 20

def generate_access_token(user_id,username,role=None) :
    """
    Generates both access and refresh tokens for a given user ID.
    """
    now = datetime.now(timezone.utc)
    
    access_token_payload = {
        "user_id": user_id,
        "role": role or "",
        "username": username,  # Include username in the payload
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "last_activity": now.timestamp()  # Track last activity time
    }
    access_token = jwt.encode(access_token_payload, SECRET_KEY, algorithm=ALGORITHM)

    refresh_token_payload = {
        "user_id": user_id,
        "role": role or "",
        "username": username,  # Include username in the payload
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }
    refresh_token = jwt.encode(refresh_token_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }

def verify_access_token(token: str = Depends(oauth2_scheme)):
    """
    Verifies the access token and checks for inactivity.
    """
    try:
        # Check if token is None or empty
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not provided")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_id = payload.get("user_id","")
        exp_timestamp = payload.get("exp","")
        last_activity = payload.get("last_activity","")
        
        if user_id is None or exp_timestamp is None or last_activity is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
        
        # Check expiration
        if datetime.now(timezone.utc).timestamp() > exp_timestamp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")

        # Check inactivity
        inactivity_duration = datetime.now(timezone.utc).timestamp() - last_activity
        if inactivity_duration > INACTIVITY_TIMEOUT_MINUTES * 60:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactivity timeout. Please log in again.")

        return payload

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

def refresh_access_token(refresh_token):
    """Refresh access token using a valid refresh token."""
    try:
        # Check if refresh_token is None or empty
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not provided")
        
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id","")
        username = payload.get("username","")
        role = payload.get("role","")

        if not user_id and not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        exp_timestamp = payload.get("exp","")
        if exp_timestamp is None or datetime.now(timezone.utc).timestamp() > exp_timestamp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired. Please log in again.")

        # Generate new access and refresh tokens
        # new_tokens = generate_tokens(user_id)["access_token"]
        # return { "access_token" : new_tokens,"refresh_token":refresh_token}
        new_tokens = generate_access_token(user_id,username,role)
        return {
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens["refresh_token"]
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired. Please log in again.")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    


# Function to get user_id from JWT token
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Check if token is None or empty
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not provided")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id","")
        
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        return user_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
def get_current_role(token: str = Depends(oauth2_scheme)):
   
    try:
        # Check if token is None or empty
        if not token:
            return None
        
        # JWT token decode karo
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role : str = payload.get("role", "")
        
        # Check if role exists in token
        if not role:
            return None
                
        return role
        
    except JWTError:
        return None

def require_role(allowed_roles: list):
    def wrapper(token: str = Depends(oauth2_scheme)):
        try:
            # Check if token is None or empty
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token not provided"
                )
            
            # JWT token decode karo
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            role = payload.get("role", "")
            
            # Check if role exists in token
            if not role:
                raise HTTPException(
                    status_code=403,
                    detail="No role assigned yet. Contact administrator."
                )
            
            # Check if role is in allowed roles
            # Convert both to string for comparison (case insensitive)
            if str(role).lower() not in [str(allowed_role).lower() for allowed_role in allowed_roles]:
                raise HTTPException(
                    status_code=403, 
                    detail="You do not have access to this resource. Please contact administrator."
                )
            
            return role
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token"
            )
    
    return wrapper