from sqlalchemy import text
from fastapi import HTTPException, APIRouter, Form, Depends, Request
from authentication.token_handler import generate_access_token, get_current_user
from database.database import get_db
from helpers.helper import hash_password, encrypt_the_string, decrypt_the_string
import pyotp
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

# Create router for endpoints
router = APIRouter()


async def teacher_register(teacher):
    db : Session = next(get_db())
    try:
        connection = db.connection()
        # Validate input fields
        if not teacher.name:
            return {"status": False, "message": "Name field is required", "data": []}

        if not teacher.username:
            return {"status": False, "message": "Username field is required", "data": []}

        if not teacher.password:
            return {"status": False, "message": "Password field is required", "data": []}

        if not teacher.hire_date:
            return {"status": False, "message": "Hire Date field is required", "data": []}

        if not teacher.role:
            return {"status": False, "message": "Role field is required", "data": []}

        if not teacher.phone:
            return {"status": False, "message": "Phone field is required", "data": []}

        if not teacher.address:
            return {"status": False, "message": "Address field is required", "data": []}

        if not teacher.specialization:
            return {"status": False, "message": "Specialization field is required", "data": []}

        # Execute the stored procedure
        result = connection.execute(
            text(
                """
            CALL usp_TeacherRegister(:p_name, :p_username,:p_role, :p_password, :p_hire_date, :p_phone, :p_address, :p_specialization)
        """
            ),
            {
                "p_name": teacher.name,
                "p_username": teacher.username,
                "p_role": teacher.role,
                "p_password": hash_password(teacher.password),
                "p_hire_date": teacher.hire_date,
                "p_phone": teacher.phone,
                "p_address": teacher.address,
                "p_specialization": teacher.specialization,
            },
        )

        # Fetch the result from the stored procedure
        result_data = result.mappings().fetchone()
        db.commit()
        if not result_data:
            return {"status": False, "message": "Registration failed", "data": []}

        message = result_data.get("Message", "Unknown error occurred")
        if result_data and result_data.get("Status","Error").lower() == "success":
            return {
                "message": message,
                "status": True,
                "data": []
            }
        else:
            return {"status": False, "message": result_data.get("Message", "Registration failed")
                    if result_data
                    else "Registration failed", "data": []}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}"
        )
    finally:
        db.close()
        
    
async def getAllTeacher():

    
    db: Session = next(get_db())
    try:

        connection = db.connection()
        
        result = connection.execute(
            text(
                """CALL usp_GetteacherList();"""
            )
        )

        rows = result.mappings().fetchall()

        teacher_list = [dict(row) for row in rows]  # Convert to dictionary    

        db.commit()
        if not teacher_list:
            return {
                "status": True,
                "message": "No Teacher found",
                "data": {
                    "teacher_list": [],
                },
            }
        else:
            for user in teacher_list:
                user.pop("Message", None)
                user.pop("Status", None)

            return {
                "status": True,
                "message": "Teacher fetched successfully",
                "data": {
                    "teacher_list": teacher_list
                },
            }
    except HTTPException as http_err:
        # Re-raise the FastAPI HTTPException without modifying it
        db.rollback()        
        raise http_err

    except Exception as err:
        db.rollback()        
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )

    finally:
        db.close()
        
        
async def teacher_delete(teacher):
    db : Session = next(get_db())
    try:
        connection = db.connection()
        # Validate input fields
        if not teacher.id:
            return {"status": False, "message": "Teacher id field is required", "data": []}

        

        # Execute the stored procedure
        result = connection.execute(
            text(
                """
            CALL usp_TeacherDelete(:p_id)
        """
            ),
            {
                "p_id": teacher.id,
                
            },
        )

        # Fetch the result from the stored procedure
        result_data = result.mappings().fetchone()
        db.commit()
        if not result_data:
            return {"status": False, "message": "Teacher deletion failed", "data": []}

        message = result_data.get("Message", "Unknown error occurred")
        if result_data and result_data.get("Status","Error").lower() == "success":
            return {
                "message": message,
                "status": True,
                "data": []
            }
        else:
            return {"status": False, "message": result_data.get("Message", "Teacher deletion failed")
                    if result_data
                    else "Teacher deletion failed", "data": []}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}"
        )
    finally:
        db.close()