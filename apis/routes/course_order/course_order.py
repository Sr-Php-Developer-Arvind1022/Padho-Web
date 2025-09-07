from fastapi import FastAPI, Form, HTTPException, APIRouter, Depends
from models.course_order.model import *
from core.logic.course_order.course_order import *
from authentication.token_handler import get_current_user, get_current_role
from typing import Optional, Union
import os
import uuid
import time
from datetime import datetime

router = APIRouter()

@router.post("/api/course/order", tags=["CourseOrderOperation"], summary="Create a new course order")
async def create_new_course_order(
    course_id: str = Form(..., description="Encrypted course ID"),
    order_amount: float = Form(..., description="Order amount"),
    payment_method: Optional[str] = Form(None, description="Payment method"),
    transaction_id: Optional[str] = Form(None, description="Transaction ID (optional, will be auto-generated if not provided)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new course order (JWT authentication required).
    
    Features:
    1. JWT authentication required
    2. Encrypted course_id handling
    3. Flexible transaction_id (can be provided or auto-generated)
    4. Automatic pending payment and order status
    5. Validates course exists and is active
    6. Prevents duplicate orders
    7. Returns encrypted order details
    
    Process:
    - Payment status: 'pending'
    - Order status: 'pending-verification'
    - Course must be active
    - Order amount must match course price
    - Transaction ID: Use provided ID or auto-generate unique ID
    
    Security:
    - Requires valid JWT token
    - All IDs are encrypted in response
    - Only authenticated users can create orders
    
    Transaction ID Logic:
    - If transaction_id is provided in request, it will be used
    - If not provided, system will generate: TXN_{timestamp}_{uuid}_{user_id}
    """
    try:
        # Get login_id from JWT (current_user returns user_id as integer)
        login_id = current_user  # current_user is the user_id integer from JWT
        
        # Encrypt login_id for the function call
        from helpers.helper import encrypt_the_string
        encrypted_login_id = encrypt_the_string(str(login_id))
        
        # Handle transaction ID - use provided one or generate dynamic one
        if transaction_id and transaction_id.strip():
            # Use provided transaction ID
            final_transaction_id = transaction_id.strip()
        else:
            # Generate dynamic transaction ID
            timestamp = int(time.time() * 1000)  # milliseconds timestamp
            unique_id = str(uuid.uuid4()).replace('-', '')[:8]  # 8 character unique ID
            final_transaction_id = f"TXN_{timestamp}_{unique_id}_{login_id}"
        
        # Validate inputs
        if not course_id or not course_id.strip():
            raise HTTPException(status_code=400, detail="Course ID is required")
        
        if order_amount <= 0:
            raise HTTPException(status_code=400, detail="Order amount must be greater than 0")
        
        # Create the order
        result = await create_course_order(
            course_id=course_id.strip(),
            login_id_fk=encrypted_login_id,
            order_amount=round(order_amount, 2),
            payment_method=payment_method.strip() if payment_method else None,
            transaction_id=transaction_id.strip() if transaction_id else final_transaction_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

@router.post("/api/course/order/my-orders", tags=["CourseOrderOperation"], summary="Get my course orders")
async def get_my_orders(
    limit: Union[int, str, None] = Form(10),
    offset: Union[int, str, None] = Form(0),
    payment_status: Union[str, None] = Form(None),
    order_status: Union[str, None] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Helper functions for safe conversion
        def safe_convert_to_int(value, default=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        def safe_convert_to_string(value, default=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return default
            return str(value).strip()
        
        # Convert and validate parameters
        limit = safe_convert_to_int(limit, 10)
        offset = safe_convert_to_int(offset, 0)
        payment_status = safe_convert_to_string(payment_status)
        order_status = safe_convert_to_string(order_status)
        
        # Validate pagination
        if limit <= 0 or limit > 100:
            limit = 10
        if offset < 0:
            offset = 0
        
        # Get login_id from JWT (current_user returns user_id as integer)
        login_id = current_user  # current_user is the user_id integer from JWT
        
        # Encrypt login_id for the function call
        from helpers.helper import encrypt_the_string
        encrypted_login_id = encrypt_the_string(str(login_id))
        
        # Get user's orders with optional filters
        result = await get_course_orders_with_filters(
            login_id_fk=encrypted_login_id,
            payment_status=payment_status,
            order_status=order_status,
            limit=limit,
            offset=offset
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

@router.post("/api/course/order/admin/all", tags=["CourseOrderOperation"], summary="Get all course orders (Admin only)")
async def get_all_orders_admin(
    order_id: Union[str, None] = Form(None, description="Encrypted order ID"),
    course_id: Union[str, None] = Form(None, description="Encrypted course ID"),
    login_id_fk: Union[str, None] = Form(None, description="Encrypted user ID"),
    payment_status: Union[str, None] = Form(None),
    order_status: Union[str, None] = Form(None),
    start_date: Union[str, None] = Form(None, description="Start date (YYYY-MM-DD)"),
    end_date: Union[str, None] = Form(None, description="End date (YYYY-MM-DD)"),
    limit: Union[int, str, None] = Form(10),
    offset: Union[int, str, None] = Form(0),
    current_user: int = Depends(get_current_user),
    user_role: str = Depends(get_current_role)
):
    """
    Get all course orders with advanced filtering (Admin/Teacher only).
    
    Features:
    1. JWT authentication required
    2. Admin/Teacher role required
    3. Full order access with filtering
    4. Date range filtering
    5. Encrypted ID filtering
    6. Pagination support
    
    Access Control:
    - Only users with 'admin' or 'teacher' role can access
    - Returns all orders with complete details
    
    Filters:
    - order_id: Specific order (encrypted)
    - course_id: Orders for specific course (encrypted)
    - login_id_fk: Orders by specific user (encrypted)
    - payment_status: pending, completed, failed, refunded
    - order_status: pending-verification, approved, cancelled
    - start_date & end_date: Date range filter (YYYY-MM-DD format)
    """
    try:
        # Check if user has admin or teacher role
        if not user_role or user_role.lower() not in ["admin", "teacher"]:
            raise HTTPException(status_code=403, detail="Access denied. Admin or teacher role required.")
        
        # Helper functions for safe conversion
        def safe_convert_to_int(value, default=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        def safe_convert_to_string(value, default=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return default
            return str(value).strip()
        
        def safe_convert_to_datetime(value, default=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return default
            try:
                return datetime.strptime(str(value).strip(), "%Y-%m-%d")
            except (ValueError, TypeError):
                return default
        
        # Convert and validate parameters
        order_id = safe_convert_to_string(order_id)
        course_id = safe_convert_to_string(course_id)
        login_id_fk = safe_convert_to_string(login_id_fk)
        payment_status = safe_convert_to_string(payment_status)
        order_status = safe_convert_to_string(order_status)
        limit = safe_convert_to_int(limit, 10)
        offset = safe_convert_to_int(offset, 0)
        start_date = safe_convert_to_datetime(start_date)
        end_date = safe_convert_to_datetime(end_date)
        
        # Validate pagination
        if limit <= 0 or limit > 100:
            limit = 10
        if offset < 0:
            offset = 0
        
        # Get all orders with filters
        result = await get_course_orders_with_filters(
            order_id=order_id,
            course_id=course_id,
            login_id_fk=login_id_fk,
            payment_status=payment_status,
            order_status=order_status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")
