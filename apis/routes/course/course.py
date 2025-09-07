from fastapi import FastAPI, File, Form, HTTPException, APIRouter, UploadFile, Depends
from models.course.model import *
from core.logic.course.course import *
from core.logic.course.course import search_courses_with_filters, get_courses_public_with_filters
from authentication.token_handler import get_current_user
from typing import Optional, Union
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
async def get_course(
    course_id: str,  # Changed to string to accept encrypted ID
    current_user_id: int = Depends(get_current_user)  # JWT authentication required
):
    """
    Endpoint to get a specific course by encrypted ID.
    Note: JWT authentication is required. course_id must be encrypted.
    """
    try:
        # Validate input
        if not course_id or not course_id.strip():
            raise HTTPException(status_code=400, detail="Course ID is required")
        
        # Decrypt course_id
        from helpers.helper import decrypt_the_string
        try:
            decrypted_course_id = int(decrypt_the_string(course_id.strip()))
        except Exception as decrypt_error:
            raise HTTPException(status_code=400, detail="Invalid encrypted course_id")
        
        # Validate decrypted course_id
        if not decrypted_course_id or decrypted_course_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid course ID")
        
        data = await get_course_by_id(decrypted_course_id, current_user_id)
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
    course_id: str,  # Changed to string to accept encrypted ID
    course_name: Optional[str] = Form(None),
    course_title: Optional[str] = Form(None),
    course_description: Optional[str] = Form(None),
    course_price: Optional[float] = Form(None),
    course_image: Optional[UploadFile] = File(None),
    demo_video: Optional[UploadFile] = File(None),
    current_user_id: int = Depends(get_current_user)  # JWT gives us decrypted user ID
):
    """
    Endpoint to update course by encrypted course ID.
    Only course creator can update their course.
    Requires JWT authentication.
    - course_id: Encrypted course ID in URL
    - JWT token provides user authentication
    """
    try:
        # Validate and decrypt course_id
        if not course_id or not course_id.strip():
            raise HTTPException(status_code=400, detail="Course ID is required")
        
        from helpers.helper import decrypt_the_string
        try:
            decrypted_course_id = int(decrypt_the_string(course_id.strip()))
        except Exception as decrypt_error:
            raise HTTPException(status_code=400, detail="Invalid encrypted course_id")
        
        if decrypted_course_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid course ID")
        
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
        
        # Call update function with decrypted IDs
        data = await update_course_by_id(
            decrypted_course_id, current_user_id, course_name, course_title, 
            course_description, course_price, course_image_path, demo_video_path
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/course/public", tags=["PublicCourseOperation"], summary="Get courses publicly (no JWT required)")
async def get_courses_public(
    course_id: Union[str, None] = Form(None),  # Encrypted course ID
    search: Union[str, None] = Form(None),  # Search term
    category_id: Union[int, str, None] = Form(None),  # Category filter
    sort_by: Union[str, None] = Form(None),  # Sorting field
    sort_order: Union[str, None] = Form(None),  # asc or desc
    limit: Union[int, str, None] = Form(None),  # Pagination limit
    offset: Union[int, str, None] = Form(None),  # Pagination offset
    min_price: Union[float, str, None] = Form(None),  # Price filter
    max_price: Union[float, str, None] = Form(None),  # Price filter
    status: Union[str, None] = Form(None)  # Course status filter
):
    try:
        # Helper function to safely convert string values
        def safe_convert_to_int(value, default=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        def safe_convert_to_float(value, default=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        def safe_convert_to_string(value, default=None):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return default
            return str(value).strip()
        
        # Convert and validate all parameters
        course_id = safe_convert_to_string(course_id)
        search = safe_convert_to_string(search)
        category_id = safe_convert_to_int(category_id)
        sort_by = safe_convert_to_string(sort_by, "created_at")
        sort_order = safe_convert_to_string(sort_order, "desc")
        limit = safe_convert_to_int(limit, 10)
        offset = safe_convert_to_int(offset, 0)
        min_price = safe_convert_to_float(min_price)
        max_price = safe_convert_to_float(max_price)
        status = safe_convert_to_string(status, "active")
        
        # Validate pagination limits
        if limit <= 0 or limit > 100:
            limit = 10
        if offset < 0:
            offset = 0
        
        # Validate and sanitize inputs
        decrypted_course_id = None
        clean_search = None
        
        # Handle encrypted course_id
        if course_id and course_id.strip():
            try:
                from helpers.helper import decrypt_the_string
                decrypted_course_id = int(decrypt_the_string(course_id.strip()))
                if decrypted_course_id <= 0:
                    raise HTTPException(status_code=400, detail="Invalid course ID")
            except Exception as decrypt_error:
                raise HTTPException(status_code=400, detail="Invalid encrypted course_id")
        
        # Clean search parameter
        if search and search.strip() and search.strip().lower() != 'none':
            clean_search = search.strip()
        
        # Validate sorting
        valid_sort_fields = ["created_at", "updated_at", "course_name", "course_price", "course_title"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "desc"
        
        # Validate price filters
        if min_price is not None and min_price < 0:
            min_price = None
        if max_price is not None and max_price < 0:
            max_price = None
        if min_price is not None and max_price is not None and min_price > max_price:
            min_price, max_price = max_price, min_price
        
        # Call the public course function
        data = await get_courses_public_with_filters(
            course_id=decrypted_course_id,
            search=clean_search,
            category_id=category_id,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
            min_price=min_price,
            max_price=max_price,
            status=status
        )
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    
    