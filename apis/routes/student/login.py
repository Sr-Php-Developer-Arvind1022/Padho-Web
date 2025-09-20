from fastapi import FastAPI, File, Form, HTTPException, APIRouter, UploadFile, Depends, Request
from models.student.model import *
from core.logic.student.login import student_register, student_login, fetch_user_details
from authentication.token_handler import get_current_user
from typing import Optional

router = APIRouter()

@router.post("/api/student/register", tags=["StudentLoginOperation"], summary="Register new student")
async def register_student(student: StudentRegister):
    """
    Endpoint to handle student registration.
    """
    try:
       data = await student_register(student)
       return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/api/student/login", tags=["StudentLoginOperation"], summary="Student login")
async def login_student(student: StudentLogin):
    """
    Endpoint to handle student login.
    """
    try:
       data = await student_login(student)
       return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/student/get_user_details", tags=["StudentOperation"], summary="Get user details")
async def user_details(
    request: Request,
    login_id: Optional[str] = Form(None, description="Encrypted login ID"),
    table_name: Optional[str] = Form("logins", description="Table to query"),
    columns: Optional[str] = Form("login_id_pk,username,email,role", description="Columns to return"),
    where_clause: Optional[str] = Form(None, description="Additional WHERE conditions"),
    current_user_id: int = Depends(get_current_user)  # JWT token protection
):
    """
    Get user details using flexible query.
    Requires JWT authentication token.
    
    Accepts both form data and JSON:
    
    Form data:
    - login_id: Encrypted login ID
    - table_name: Table name (default: logins)
    - columns: Comma-separated column names
    - where_clause: Additional WHERE conditions
    
    JSON format:
    {
      "table": "courses",
      "columns": "course_id_pk,course_name",
      "login_id": "encrypted_login_id_string"
    }
    """
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
                    columns = json_data["columns"]
                
                if "login_id" in json_data:
                    login_id = json_data["login_id"]
                
                # Extract where clause if provided
                if "where_clause" in json_data:
                    where_clause = json_data["where_clause"]
            
            except Exception as json_err:
                raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(json_err)}")
        
        # Validate required parameters
        if not login_id:
            raise HTTPException(status_code=400, detail="login_id is required")
        
        data = await fetch_user_details(
            login_id_encrypted=login_id,
            table_name=table_name,
            columns=columns,
            where_clause=where_clause
        )
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))