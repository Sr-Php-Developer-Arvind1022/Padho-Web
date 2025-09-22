from sqlalchemy.orm import Session
from database.database import get_db
from sqlalchemy import text
from fastapi import HTTPException
from datetime import datetime
from typing import Optional

async def create_course_order(
    course_id: str, login_id_fk: str, order_amount: float,
    payment_method: Optional[str] = None, transaction_id: Optional[str] = None
):
    """
    Create a new course order with encrypted ID handling.
    
    Features:
    1. Decrypt encrypted course_id and login_id_fk
    2. Validate course exists and is active
    3. Validate user exists
    4. Check order amount matches course price
    5. Prevent duplicate orders
    6. Create order with pending status
    7. Return encrypted order details
    """
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Decrypt the encrypted IDs
        from helpers.helper import decrypt_the_string
        try:
            decrypted_course_id = int(decrypt_the_string(course_id))
            decrypted_login_id = int(decrypt_the_string(login_id_fk))
        except Exception as decrypt_error:
            raise HTTPException(status_code=400, detail="Invalid encrypted IDs provided")
        
        # Validate decrypted IDs
        if decrypted_course_id <= 0 or decrypted_login_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid course or user ID")
        
        # Execute the stored procedure
        result = connection.execute(
            text("CALL usp_CreateCourseOrder(:p_course_id, :p_login_id_fk, :p_order_amount, :p_payment_method, :p_transaction_id)"),
            {
                "p_course_id": decrypted_course_id,
                "p_login_id_fk": decrypted_login_id,
                "p_order_amount": order_amount,
                "p_payment_method": payment_method,
                "p_transaction_id": transaction_id
            }
        )
        
        # Fetch result
        order_result = result.mappings().fetchone()
        db.commit()
        
        if not order_result:
            raise HTTPException(status_code=500, detail="Failed to create order")
        
        # Check if there was an error
        if order_result.get("Status") == "Error":
            return {"status": False, "message": order_result.get("Message"), "data": []}
        
        # Encrypt IDs before returning
        from helpers.helper import encrypt_the_string
        encrypted_order_id = encrypt_the_string(str(order_result.get("order_id_pk")))
        encrypted_course_id_return = encrypt_the_string(str(order_result.get("course_id_fk")))
        encrypted_login_id_return = encrypt_the_string(str(order_result.get("login_id_fk")))
        
        return {
            "status": True,
            "message": "Course order created successfully",
            "data": {
                "order_id_pk": encrypted_order_id,
                "course_id_fk": encrypted_course_id_return,
                "login_id_fk": encrypted_login_id_return,
                "order_date": order_result.get("order_date"),
                "order_amount": order_result.get("order_amount"),
                "payment_status": order_result.get("payment_status"),
                "payment_method": order_result.get("payment_method"),
                "transaction_id": order_result.get("transaction_id"),
                "order_status": order_result.get("order_status"),
                "created_at": order_result.get("created_at"),
                "updated_at": order_result.get("updated_at")
            }
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()

async def get_course_orders_with_filters(
    order_id: Optional[str] = None,
    course_id: Optional[str] = None,
    login_id_fk: Optional[str] = None,
    payment_status: Optional[str] = None,
    order_status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10,
    offset: int = 0
):
    """
    Get course orders with advanced filtering and encrypted ID handling.
    
    Features:
    1. Filter by encrypted order_id, course_id, login_id_fk
    2. Filter by payment status and order status
    3. Filter by date range
    4. Pagination support
    5. Return encrypted IDs for security
    """
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Decrypt encrypted IDs if provided
        decrypted_order_id = None
        decrypted_course_id = None
        decrypted_login_id = None
        
        from helpers.helper import decrypt_the_string
        
        try:
            if order_id and order_id.strip():
                decrypted_order_id = int(decrypt_the_string(order_id))
            if course_id and course_id.strip():
                decrypted_course_id = int(decrypt_the_string(course_id))
            if login_id_fk and login_id_fk.strip():
                decrypted_login_id = int(decrypt_the_string(login_id_fk))
        except Exception as decrypt_error:
            raise HTTPException(status_code=400, detail="Invalid encrypted ID provided")
        
        # Execute the stored procedure
        result = connection.execute(
            text("CALL usp_GetCourseOrders(:p_order_id, :p_course_id, :p_login_id_fk, :p_payment_status, :p_order_status, :p_start_date, :p_end_date, :p_limit, :p_offset)"),
            {
                "p_order_id": decrypted_order_id,
                "p_course_id": decrypted_course_id,
                "p_login_id_fk": decrypted_login_id,
                "p_payment_status": payment_status,
                "p_order_status": order_status,
                "p_start_date": start_date,
                "p_end_date": end_date,
                "p_limit": limit,
                "p_offset": offset
            }
        )
        
        # Fetch all results
        orders = result.mappings().fetchall()
        db.commit()
        
        if not orders:
            return {
                "status": True,
                "message": "No orders found",
                "data": [],
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "returned": 0,
                    "has_more": False
                }
            }
        
        # Build order list with encrypted IDs
        order_list = []
        for order in orders:
            # Encrypt all IDs before sending
            from helpers.helper import encrypt_the_string
            encrypted_order_id = encrypt_the_string(str(order.get("order_id_pk")))
            encrypted_course_id = encrypt_the_string(str(order.get("course_id_fk")))
            encrypted_login_id = encrypt_the_string(str(order.get("login_id_fk")))
            
            order_list.append({
                "order_id_pk": encrypted_order_id,
                "course_id_fk": encrypted_course_id,
                "login_id_fk": encrypted_login_id,
                "order_date": order.get("order_date"),
                "order_amount": order.get("order_amount"),
                "payment_status": order.get("payment_status"),
                "payment_method": order.get("payment_method"),
                "transaction_id": order.get("transaction_id"),
                "order_status": order.get("order_status"),
                "created_at": order.get("created_at"),
                "updated_at": order.get("updated_at"),
                "course_name": order.get("course_name"),
                "course_title": order.get("course_title"),
                "course_image": order.get("course_image"),
                "user_email": order.get("user_email")
            })
        
        # Create filter description for message
        filter_desc = []
        if order_id:
            filter_desc.append(f"order ID {order_id[:8]}...")
        if course_id:
            filter_desc.append(f"course ID {course_id[:8]}...")
        if login_id_fk:
            filter_desc.append(f"user ID {login_id_fk[:8]}...")
        if payment_status:
            filter_desc.append(f"payment status '{payment_status}'")
        if order_status:
            filter_desc.append(f"order status '{order_status}'")
        if start_date and end_date:
            filter_desc.append(f"date range {start_date.date()} to {end_date.date()}")
        elif start_date:
            filter_desc.append(f"from {start_date.date()}")
        elif end_date:
            filter_desc.append(f"until {end_date.date()}")
        
        filter_text = " with " + ", ".join(filter_desc) if filter_desc else ""
        message = f"Found {len(order_list)} orders{filter_text}"
        
        # Check if there are more results
        has_more = len(order_list) == limit
        
        return {
            "status": True,
            "message": message,
            "data": order_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "returned": len(order_list),
                "has_more": has_more,
                "next_offset": offset + limit if has_more else None
            },
            "filters": {
                "order_id": order_id,
                "course_id": course_id,
                "login_id_fk": login_id_fk,
                "payment_status": payment_status,
                "order_status": order_status,
                "start_date": start_date,
                "end_date": end_date
            }
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()

async def get_my_course_orders(login_id_fk: str, limit: int = 10, offset: int = 0):
    """
    Get current user's course orders only.
    JWT authentication ensures user can only see their own orders.
    """
    return await get_course_orders_with_filters(
        login_id_fk=login_id_fk,
        limit=limit,
        offset=offset
    )
