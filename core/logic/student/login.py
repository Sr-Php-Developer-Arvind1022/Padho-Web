
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from authentication.token_handler import generate_access_token
from database.database import get_db
from helpers.helper import hash_password

import pyotp




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
            return {"status": False, "message": "Password field is required", "data": []}

        

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
        print(result_data)
        db.commit()
        if not result_data:
            return {"status": False, "message": "Invalid login credentials", "data": []}

        
        message = result_data.get("Message", "Unknown error occurred")
        if result_data and result_data.get("Status","Error").lower() == "success":
            # track the login with ip address and data
            student_id = result_data.get("student_id_pk")
            email = student.email
            token_value = generate_access_token(student_id,email)
            
            response = {
                "message": message,
                "status": True,
                "data": {
                    "student": {
                       "student_id": result_data.get("student_id_pk")
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