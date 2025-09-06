from fastapi import FastAPI, File, Form, HTTPException, APIRouter, UploadFile, Depends
from models.course.model import *
from core.logic.course.course import *
from core.logic.course.course import search_courses_with_filters
from authentication.token_handler import get_current_user
from typing import Optional
import os
import shutil
from datetime import datetime

router = APIRouter()

@router.post("/api/course/register", tags=["CourseOperation"], summary="Register a new course")
async def create_course(
    course_name: str = Form(...),
    course_title: str = Form(...),
    course_description: Optional[str] = Form(None),
    course_price: Optional[float] = Form(None),
    course_image: Optional[UploadFile] = File(None),
    demo_video: Optional[UploadFile] = File(None),
    current_user_id: int = Depends(get_current_user)  # JWT token से user ID extract करेंगे
):
    """
    Endpoint to handle course registration with file uploads.
    Requires JWT authentication.
    """
    try:
        # Handle file uploads
        course_image_path = None
        demo_video_path = None
        
        # Create uploads directory if it doesn't exist
        upload_dir = "uploads/courses"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save course image if provided
        if course_image:
            image_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{course_image.filename}"
            course_image_path = f"{upload_dir}/{image_filename}"
            with open(course_image_path, "wb") as buffer:
                shutil.copyfileobj(course_image.file, buffer)
        
        # Save demo video if provided
        if demo_video:
            video_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{demo_video.filename}"
            demo_video_path = f"{upload_dir}/{video_filename}"
            with open(demo_video_path, "wb") as buffer:
                shutil.copyfileobj(demo_video.file, buffer)
        
        # Create course object with login_id_fk from JWT token
        course = CourseRegister(
            course_name=course_name,
            course_title=course_title,
            course_description=course_description,
            course_price=course_price,
            login_id_fk=current_user_id  # JWT से decrypt किया गया user ID
        )
        
        data = await course_register(course, course_image_path, demo_video_path)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/course/all", tags=["CourseOperation"], summary="Get all courses with advanced filtering")
async def get_courses(
    login_id_fk: Optional[str] = Form(None),  # Encrypted login_id_fk as string
    search: Optional[str] = Form(None),
    limit: int = Form(10),
    offset: int = Form(0),
    current_user_id: int = Depends(get_current_user)  # JWT authentication required
):
    """
    Endpoint to get all courses with advanced filtering options (POST method):
    - login_id_fk: Encrypted user ID to filter courses by specific user
    - search: Search in course name, title, or description
    - limit: Number of results to return (default: 10)
    - offset: Number of results to skip for pagination (default: 0)
    
    Note: JWT authentication is required. If login_id_fk is provided, it will be decrypted.
    
    Example POST body (form-data):
    login_id_fk: encrypted_user_id_string
    search: python
    limit: 10
    offset: 0
    """
    try:
        # Decrypt login_id_fk if provided
        decrypted_user_id = None
        if login_id_fk and login_id_fk.strip():
            try:
                from helpers.helper import decrypt_the_string
                decrypted_user_id = int(decrypt_the_string(login_id_fk.strip()))
            except Exception as decrypt_error:
                raise HTTPException(status_code=400, detail="Invalid encrypted login_id_fk")
        
        data = await get_all_courses_with_filters(user_id=decrypted_user_id, search=search, limit=limit, offset=offset)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/course/{course_id}", tags=["CourseOperation"], summary="Get course by ID")
async def get_course(course_id: int):
    """
    Endpoint to get a specific course by ID.
    """
    try:
        data = await get_course_by_id(course_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/course/my-courses", tags=["CourseOperation"], summary="Get my courses")
async def get_my_courses(current_user_id: int = Depends(get_current_user)):
    """
    Endpoint to get courses created by the current user.
    Requires JWT authentication.
    """
    try:
        data = await get_courses_by_user(current_user_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/course/by-user/{login_id}", tags=["CourseOperation"], summary="Get courses by login ID")
async def get_courses_by_login_id(login_id: int):
    """
    Endpoint to get courses by specific login ID.
    """
    try:
        data = await get_courses_by_user(login_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/course/search", tags=["CourseOperation"], summary="Search courses with filters")
async def search_courses(
    search: Optional[str] = Form(None),
    login_id_fk: Optional[str] = Form(None),  # Encrypted login_id_fk as string
    limit: int = Form(10),
    offset: int = Form(0),
    current_user_id: int = Depends(get_current_user)  # JWT authentication required
):
    """
    Endpoint to search courses with filters, limit and offset.
    - search: Search term for course name/title/description
    - login_id_fk: Encrypted user ID to filter by specific user
    - limit: Number of results to return (default: 10)
    - offset: Number of results to skip (default: 0)
    
    Note: JWT authentication is required. If login_id_fk is provided, it will be decrypted.
    """
    try:
        # Decrypt login_id_fk if provided
        decrypted_user_id = None
        if login_id_fk and login_id_fk.strip():
            try:
                from helpers.helper import decrypt_the_string
                decrypted_user_id = int(decrypt_the_string(login_id_fk.strip()))
            except Exception as decrypt_error:
                raise HTTPException(status_code=400, detail="Invalid encrypted login_id_fk")
        
        data = await search_courses_with_filters(search, decrypted_user_id, limit, offset)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/course/update/{course_id}", tags=["CourseOperation"], summary="Update course")
async def update_course(
    course_id: int,
    course_name: Optional[str] = Form(None),
    course_title: Optional[str] = Form(None),
    course_description: Optional[str] = Form(None),
    course_price: Optional[float] = Form(None),
    course_image: Optional[UploadFile] = File(None),
    demo_video: Optional[UploadFile] = File(None),
    current_user_id: int = Depends(get_current_user)
):
    """
    Endpoint to update course by course ID.
    Only course creator can update their course.
    Requires JWT authentication.
    """
    try:
        # Handle file uploads
        course_image_path = None
        demo_video_path = None
        
        upload_dir = "uploads/courses"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save course image if provided
        if course_image:
            image_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{course_image.filename}"
            course_image_path = f"{upload_dir}/{image_filename}"
            with open(course_image_path, "wb") as buffer:
                shutil.copyfileobj(course_image.file, buffer)
        
        # Save demo video if provided
        if demo_video:
            video_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{demo_video.filename}"
            demo_video_path = f"{upload_dir}/{video_filename}"
            with open(demo_video_path, "wb") as buffer:
                shutil.copyfileobj(demo_video.file, buffer)
        
        data = await update_course_by_id(
            course_id, current_user_id, course_name, course_title, 
            course_description, course_price, course_image_path, demo_video_path
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    
    