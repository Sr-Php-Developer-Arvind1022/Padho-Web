
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from authentication.token_handler import generate_access_token
from database.database import get_db
from helpers.helper import hash_password, encrypt_the_string
import pyotp


async def student_register(student):
    db : Session = next(get_db())
    try:
        connection = db.connection()
        # Validate input fields
        if not student.name:
            return {"status": False, "message": "Name field is required", "data": []}

        if not student.email:
            return {"status": False, "message": "Email field is required", "data": []}

        if not student.password:
            return {"status": False, "message": "Password field is required", "data": []}

        if not student.date_of_birth:
            return {"status": False, "message": "Date of birth field is required", "data": []}

        if not student.grade:
            return {"status": False, "message": "Grade field is required", "data": []}

        if not student.phone:
            return {"status": False, "message": "Phone field is required", "data": []}

        if not student.address:
            return {"status": False, "message": "Address field is required", "data": []}

        if not student.parent_email:
            return {"status": False, "message": "Parent email field is required", "data": []}

        # Execute the stored procedure
        result = connection.execute(
            text(
                """
            CALL usp_StudentRegister(:p_name, :p_email,:p_role, :p_password, :p_date_of_birth, :p_grade, :p_phone, :p_address, :p_parent_email)
        """
            ),
            {
                "p_name": student.name,
                "p_email": student.email,
                "p_role": student.role,
                "p_password": hash_password(student.password),
                "p_date_of_birth": student.date_of_birth,
                "p_grade": student.grade,
                "p_phone": student.phone,
                "p_address": student.address,
                "p_parent_email": student.parent_email,
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


async def student_login(student):
    db: Session = next(get_db())

    
    try:

        # logger.info(f"Login Received Request: {login_data.__dict__}")

        connection = db.connection()
        # logger.info("Database connected successfully")

        # Validate input fields
        if not student.email:
            # logger.error(f"Username field is required")
            # raise HTTPException(status_code=422, detail="Username field is required")
            return {"status": False, "message": "Email field is required", "data": []}

        if not student.password:
            # logger.error(f"Password field is required")
            # raise HTTPException(status_code=422, detail="Password field is required")
            return {"status": False, "  ": "Password field is required", "data": []}

        

        # logger.info(f"Login OTP is : {otp}")
        # Execute the stored procedure

        result = connection.execute(
            text(
                """
            CALL usp_StudentLogin(:p_email, :p_password)
        """
            ),
            {
                "p_email": student.email,
                "p_password": hash_password(student.password),

            },
        )


        # logger.info("execute the login procedure successfully")
    
        # Fetch the result from the stored procedure
        result_data = result.mappings().fetchone()
        print("data => ",result_data)
        db.commit()
        if not result_data:
            return {"status": False, "message": "Invalid login credentials", "data": []}

        
        message = result_data.get("Message", "Unknown error occurred")
        if result_data and result_data.get("Status","Error").lower() == "success":
            # track the login with ip address and data
            student_id = result_data.get("login_id_pk")
            email = student.email
            token_value = generate_access_token(student_id,email)
            
            # Encrypt the student_id before returning
            encrypted_student_id = encrypt_the_string(str(student_id))
            
            response = {
                "message": message,
                "status": True,
                "data": {
                    "student": {
                       "student_id": encrypted_student_id,
                       "role": result_data.get("role")
                    },
                    "tokens": token_value,
                },
            }
                
            return response
        else:
            # logger.error(f"Failed to login")
            return {"status": False, "message": result_data.get("Message", "Login failed")
                    if result_data
                    else "Login failed", "data": []}

    except HTTPException as http_err:
        # Re-raise the FastAPI HTTPException without modifying it
        # logger.error(f"Error : {str(http_err)}")
        raise http_err

    except Exception as err:
        db.rollback()
        # logger.error(f"An error occurred: {str(err)}")
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )

    finally:
        # logger.info(f"Close the database connection")
        db.close()