from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, APIRouter, Form, Depends, Request
from authentication.token_handler import generate_access_token, get_current_user
from database.database import get_db
from helpers.helper import hash_password, encrypt_the_string, decrypt_the_string
import pyotp
from typing import Optional

# Create router for endpoints
router = APIRouter()


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


async def fetch_user_details(login_id_encrypted: str, table_name: str = "logins", columns: str = "login_id_pk,username,email,role", where_clause: str = None):
   
    db: Session = next(get_db())
    
    try:
        # Decrypt login_id
        try:
            decrypted_login_id = int(decrypt_the_string(login_id_encrypted.strip()))
        except Exception as decrypt_error:
            return {"status": False, "message": "Invalid encrypted login ID", "data": []}
            
        if decrypted_login_id <= 0:
            return {"status": False, "message": "Invalid login ID", "data": []}
            
        # Create WHERE clause with login_id
        base_where = f"login_id_fk = {decrypted_login_id}"
        final_where = base_where
        
        # Add any additional conditions if provided
        if where_clause and where_clause.strip():
            final_where = f"{base_where} AND ({where_clause.strip()})"
            
        # Prepare parameters for stored procedure
        params = {
            "p_table_name": table_name.strip(),
            "p_columns": columns.strip(),
            "p_where": final_where,
            "p_group_by": None,
            "p_order_by": None,
            "p_limit": 1,  # We only need one user's details
            "p_offset": 0,
            "p_login_id_fk": decrypted_login_id
        }
        
        # Execute the stored procedure
        connection = db.connection()
        result = connection.execute(
            text("CALL usp_FlexibleQuery(:p_table_name, :p_columns, :p_where, :p_group_by, :p_order_by, :p_limit, :p_offset, :p_login_id_fk)"),
            params
        )
        
        # Fetch the results
        user_data = result.mappings().fetchall()
        db.commit()
        
        # No results found
        if not user_data or len(user_data) == 0:
            return {"status": False, "message": "User not found", "data": []}
        
        # Process the results - convert to list of dicts
        user_details = []
        for row in user_data:
            user_dict = dict(row)
            # Re-encrypt the login_id_pk for security
            if "login_id_pk" in user_dict and user_dict["login_id_pk"]:
                user_dict["login_id_pk"] = encrypt_the_string(str(user_dict["login_id_pk"]))
            user_details.append(user_dict)
        
        return {
            "status": True,
            "message": "User details retrieved successfully",
            "data": user_details
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error getting user details: {str(e)}")
        return {"status": False, "message": f"Failed to get user details: {str(e)}", "data": []}
    
    finally:
        db.close()


@router.post("/api/user/details", tags=["UserOperation"], summary="Get user details")
async def user_details_api(
    request: Request,
    login_id: Optional[str] = Form(None, description="Encrypted login ID"),
    table_name: Optional[str] = Form("logins", description="Table name to query"),
    columns: Optional[str] = Form("login_id_pk,username,email,role", description="Columns to return"),
    where_clause: Optional[str] = Form(None, description="Additional WHERE conditions"),
    current_user_id: int = Depends(get_current_user)  # JWT token authentication
):
    
    try:
        # Check if we have JSON data
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                json_data = await request.json()
                
                # Extract parameters from JSON
                if "table" in json_data:
                    table_name = json_data["table"]
                
                if "columns" in json_data:
                    # Handle columns as list or string
                    if isinstance(json_data["columns"], list):
                        columns = ",".join(json_data["columns"])
                    else:
                        columns = json_data["columns"]
                
                # Extract login_id from where clause
                if "where" in json_data and isinstance(json_data["where"], dict):
                    where_dict = json_data["where"]
                    if "login_id" in where_dict:
                        login_id = where_dict["login_id"]
                    
                    # Build where clause from dict
                    where_parts = []
                    for key, value in where_dict.items():
                        if key != "login_id":  # Skip login_id as it's handled separately
                            if isinstance(value, str):
                                where_parts.append(f"{key} = '{value}'")
                            else:
                                where_parts.append(f"{key} = {value}")
                    
                    if where_parts:
                        where_clause = " AND ".join(where_parts)
            
            except Exception as json_err:
                return {"status": False, "message": f"Invalid JSON format: {str(json_err)}", "data": []}
        
        # Validate required parameters
        if not login_id:
            return {"status": False, "message": "login_id is required", "data": []}
        
        # Call the function to get user details
        result = await fetch_user_details(
            login_id_encrypted=login_id,
            table_name=table_name,
            columns=columns,
            where_clause=where_clause
        )
        
        return result
        
    except Exception as e:
        print(f"Error in user_details_api: {str(e)}")
        return {"status": False, "message": f"Failed to get user details: {str(e)}", "data": []}