"""
Course API Routes with Remote File Upload Support

This module handles course-related operations including:
- Course registration with file uploads
- Course updates with file uploads
- Course retrieval and searching
- Public course access

File Upload Features:
- Remote upload to https://sahilmoney.in/padho_video
- Automatic folder creation based on course name
- Direct remote upload without local fallback
- Support for both images and videos
- Encrypted file URLs stored in database

Configuration:
- REMOTE_UPLOAD_ENABLED: Enable/disable remote uploads (default: true)
- REMOTE_UPLOAD_URL: Remote upload endpoint URL

Testing:
- POST /api/course/test-upload: Test file upload functionality
  Parameters:
  - file: File to upload
  - course_name: Course name for folder creation
  - file_type: 'image' or 'video'

Usage Examples:
1. Course Registration with Files:
   POST /api/course/register
   - course_name: "Python Programming"
   - course_image: (file)
   - demo_video: (file)
   - Files will be uploaded to: https://sahilmoney.in/padho_video/Python_Programming/

2. Test File Upload:
   POST /api/course/test-upload
   - file: (test image/video)
   - course_name: "TestCourse"
   - file_type: "image"

Error Handling:
- Network errors are retried up to 2 times
- All errors are logged for debugging
- Files are uploaded directly to remote server
"""

from fastapi import FastAPI, File, Form, HTTPException, APIRouter, UploadFile, Depends, Request, Body
from models.course.model import *
from core.logic.course.course import *
from core.logic.course.course import search_courses_with_filters, get_courses_public_with_filters
from authentication.token_handler import get_current_user
from typing import Optional, Union
import os
import ftplib
import logging
from datetime import datetime
from io import BytesIO

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration for file uploads
REMOTE_UPLOAD_ENABLED = os.getenv('REMOTE_UPLOAD_ENABLED', 'true').lower() == 'true'
REMOTE_UPLOAD_URL = os.getenv('REMOTE_UPLOAD_URL', 'https://sahilmoney.in/padho_video')

# FTP Configuration
FTP_HOST = os.getenv('FTP_HOST', 'ftp.sahilmoney.in')
FTP_USER = os.getenv('FTP_USER', 'padho_videos@sahilmoney.in')
FTP_PASS = os.getenv('FTP_PASS', 'Arvind@123')
FTP_BASE_DIR = os.getenv('FTP_BASE_DIR', 'padho_video/')

router = APIRouter()

async def test_ftp_connection():
    """
    Test FTP connection and list directories
    """
    try:
        logger.info(f"Testing FTP connection to {FTP_HOST}")
        ftp = ftplib.FTP()
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASS)
        logger.info("FTP connection successful")
        
        # Get current directory
        current_dir = ftp.pwd()
        logger.info(f"Current directory: {current_dir}")
        
        # List root directory
        logger.info("Listing root directory:")
        try:
            ftp.dir()
        except Exception as e:
            logger.info(f"Could not list root directory: {e}")
        
        # Try to change to base directory
        try:
            ftp.cwd(FTP_BASE_DIR)
            logger.info(f"Successfully changed to: {FTP_BASE_DIR}")
            logger.info("Listing base directory:")
            ftp.dir()
        except ftplib.error_perm as e:
            logger.error(f"Could not change to {FTP_BASE_DIR}: {str(e)}")
            
            # List available directories in current location
            logger.info("Available directories:")
            try:
                files = ftp.nlst()
                for file in files:
                    logger.info(f"  {file}")
            except Exception as e:
                logger.info(f"Could not list files: {e}")
        
        ftp.quit()
        return {"status": "success", "message": "FTP test completed"}
        
    except Exception as e:
        logger.error(f"FTP test failed: {str(e)}")
        return {"status": "error", "message": str(e)}

async def upload_file_to_remote(file: UploadFile, course_name: str, file_type: str) -> str:
    """
    Upload file to remote FTP server and return the URL (fast, no local fallback)
    """
    try:
        folder_name = course_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        # Read file content with explicit exception handling and fallback
        file_content = None
        try:
            file_content = await file.read()
            await file.seek(0)
        except Exception as e:
            logger.info(f"Async read failed for {getattr(file,'filename', 'unknown')}, trying sync read: {e}")
            try:
                file_content = file.file.read()
                file.file.seek(0)
            except Exception as e2:
                logger.error(f"Sync read also failed for {getattr(file,'filename','unknown')}: {e2}")
                raise Exception(f"Failed to read uploaded file: {e2}") from e2

        try:
            logger.info(f"Connecting to FTP: {FTP_HOST} as {FTP_USER}")
            ftp = ftplib.FTP()
            ftp.connect(FTP_HOST, 21, timeout=30)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.set_pasv(True)
            logger.info("FTP connected and passive mode set")
            # Change to base directory (assume it exists)
            ftp.cwd(FTP_BASE_DIR)
            # Try to create course folder (ignore error if exists)
            try:
                ftp.mkd(folder_name)
            except ftplib.error_perm:
                pass
            ftp.cwd(folder_name)
            # Upload file
            file_stream = BytesIO(file_content)
            ftp.storbinary(f'STOR {file.filename}', file_stream)
            logger.info(f"File uploaded via FTP: {file.filename}")
            ftp.quit()
            remote_file_url = f"{REMOTE_UPLOAD_URL}/{folder_name}/{file.filename}"
            logger.info(f"Remote file URL: {remote_file_url}")
            return remote_file_url
        except Exception as e:
            logger.error(f"FTP upload failed: {str(e)}")
            raise Exception(f"FTP upload failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Remote upload failed: {str(e)}")
        raise Exception(f"File upload failed: {str(e)}") from e

@router.get("/api/course/test-ftp", tags=["CourseOperation"], summary="Test FTP connection")
async def test_ftp():
    """
    Test FTP connection and list directories
    """
    result = await test_ftp_connection()
    return result

@router.post("/api/course/test-upload", tags=["CourseOperation"], summary="Test file upload functionality")
async def test_file_upload(
    file: UploadFile = File(...),
    course_name: str = Form("TestCourse"),
    file_type: str = Form("image")
):
    """
    Test endpoint to verify file upload functionality.
    This endpoint uploads files directly to the remote FTP server.
    
    Parameters:
    - file: File to upload
    - course_name: Course name for folder creation
    - file_type: Type of file ('image' or 'video')
    """
    try:
        logger.info(f"Testing FTP file upload: {file.filename}, course: {course_name}, type: {file_type}")
        
        # Test the upload function
        result_url = await upload_file_to_remote(file, course_name, file_type)
        
        return {
            "status": True,
            "message": "FTP file upload test successful",
            "data": {
                "filename": file.filename,
                "course_name": course_name,
                "file_type": file_type,
                "uploaded_url": result_url,
                "ftp_host": FTP_HOST,
                "ftp_base_dir": FTP_BASE_DIR,
                "upload_type": "ftp"
            }
        }
    except Exception as e:
        logger.error(f"FTP file upload test failed: {str(e)}")
        return {
            "status": False,
            "message": f"FTP file upload test failed: {str(e)}",
            "data": {
                "filename": file.filename,
                "course_name": course_name,
                "file_type": file_type,
                "ftp_host": FTP_HOST,
                "ftp_base_dir": FTP_BASE_DIR
            }
        }

@router.post("/api/course/register", tags=["CourseOperation"], summary="Register a new course")
async def create_course(
    course_category: Optional[int] = Form(None),
    course_name: str = Form(...),
    course_title: str = Form(...),
    course_description: Optional[str] = Form(None),
    course_price: Optional[float] = Form(None),
    course_image: Optional[UploadFile] = File(None),
    demo_video: Optional[UploadFile] = File(None),
    current_user_id: int = Depends(get_current_user),
    flag: str = Form(...),
    update_id: Optional[int] = Form(None)
):
    """
    Endpoint to handle course registration with file uploads.
    Requires JWT authentication.
    Files are uploaded to remote FTP server: sahilmoney.in/padho_video
    """
    try:
        logger.info(f"Creating course: {course_name}")
        
        # Handle file uploads to remote server
        course_image_url = None
        demo_video_url = None
        
        # Upload course image if provided
        if course_image:
            logger.info(f"Uploading course image: {course_image.filename}")
            course_image_url = await upload_file_to_remote(course_image, course_name, "image")
            logger.info(f"Course image uploaded: {course_image_url}")
        
        # Upload demo video if provided
        if demo_video:
            logger.info(f"Uploading demo video: {demo_video.filename}")
            demo_video_url = await upload_file_to_remote(demo_video, course_name, "video")
            logger.info(f"Demo video uploaded: {demo_video_url}")
        
        # Call stored procedure usp_CourseRegister using a connection() from the Session
        from sqlalchemy.orm import Session
        from database.database import get_db
        from sqlalchemy import text

        db: Session = next(get_db())
        try:
            connection = db.connection()
            logger.info("Executing stored procedure usp_CourseRegister via connection.execute")
            # Ensure parameters follow stored-proc signature and count:
            # (p_course_category, p_course_name, p_course_title, p_course_description,
            #  p_course_price, p_course_image, p_demo_video, p_login_id_fk, p_flag, p_update_id)
            params = {
                "p_course_category": course_category,
                "p_course_name": course_name,
                "p_course_title": course_title,
                "p_course_description": course_description,
                "p_course_price": course_price,
                "p_course_image": course_image_url,
                "p_demo_video": demo_video_url,
                "p_login_id_fk": current_user_id,
                "p_flag": flag,
                "p_update_id": update_id
            }
            logger.info(f"usp_CourseRegister params: {{'p_course_category': {course_category}, 'p_course_name': '{course_name}', 'p_login_id_fk': {current_user_id}, 'p_flag': 'I'}}")
            result = connection.execute(
                text("CALL usp_CourseRegister(:p_course_category, :p_course_name, :p_course_title, :p_course_description, :p_course_price, :p_course_image, :p_demo_video, :p_login_id_fk, :p_flag, :p_update_id)"),
                params
            )
            sp_result = result.mappings().fetchone()
            db.commit()
        except Exception as db_err:
            db.rollback()
            logger.error(f"DB error in usp_CourseRegister: {str(db_err)}")
            raise HTTPException(status_code=500, detail=f"DB error: {str(db_err)}")
        finally:
            db.close()
        
        # Interpret stored-proc response if present
        if not sp_result:
            return {"status": True, "message": "Course registered (no detailed response from DB)", "data": {}}
        
        response_payload = {
            "status": True if sp_result.get("Status") in (None, "Success", True, "True") else False,
            "message": sp_result.get("Message", "Course registered successfully"),
            "data": {k: v for k, v in sp_result.items() if k not in ("Status", "Message")}
        }
        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/course/all", tags=["CourseOperation"], summary="Get all courses with advanced filtering")
async def get_courses(
    login_id_fk: Optional[str] = Form(None),  # Encrypted user ID as string
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
        logger.info(f"Updating course: {course_id}")
        
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
        
        # Handle file uploads to remote server
        course_image_url = None
        demo_video_url = None
        
        # Get course name for folder creation (if updating course name, use new name)
        folder_course_name = course_name if course_name else None
        
        # If course_name not provided, we need to get it from database
        if not folder_course_name:
            # Fetch current course details to get the name
            from sqlalchemy.orm import Session
            from database.database import get_db
            from sqlalchemy import text
            
            db: Session = next(get_db())
            try:
                result = db.execute(
                    text("SELECT course_name FROM courses WHERE course_id_pk = :course_id"),
                    {"course_id": decrypted_course_id}
                ).fetchone()
                if result:
                    folder_course_name = result[0]
                db.close()
            except Exception:
                db.close()
                raise HTTPException(status_code=500, detail="Could not fetch course details")
        
        # Upload course image if provided
        if course_image and folder_course_name:
            logger.info(f"Uploading course image for update: {course_image.filename}")
            course_image_url = await upload_file_to_remote(course_image, folder_course_name, "image")
            logger.info(f"Course image updated: {course_image_url}")
        
        # Upload demo video if provided
        if demo_video and folder_course_name:
            logger.info(f"Uploading demo video for update: {demo_video.filename}")
            demo_video_url = await upload_file_to_remote(demo_video, folder_course_name, "video")
            logger.info(f"Demo video updated: {demo_video_url}")
        
        # Call update function with decrypted IDs
        data = await update_course_by_id(
            decrypted_course_id, current_user_id, course_name, course_title, 
            course_description, course_price, course_image_url, demo_video_url
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
    """
    Public endpoint to get courses without JWT authentication.
    This endpoint works WITHOUT any JWT token or Authorization header.
    
    Features:
    1. Search courses by name, title, description
    2. Get specific course by encrypted course_id
    3. Filter by category_id
    4. Sorting by multiple fields
    5. Price range filtering
    6. Pagination support
    7. NO AUTHENTICATION REQUIRED
    
    Usage Examples:
    1. All courses: POST /api/course/public (empty body)
    2. Search: POST with search=python
    3. Filter: POST with min_price=50&max_price=200
    """
    try:
        # Import database functions locally to avoid global auth issues
        from sqlalchemy.orm import Session
        from database.database import get_db
        from sqlalchemy import text
        
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
        
        # Decrypt course_id if provided
        decrypted_course_id = None
        if course_id and course_id.strip():
            try:
                from helpers.helper import decrypt_the_string
                decrypted_course_id = int(decrypt_the_string(course_id.strip()))
                if decrypted_course_id <= 0:
                    raise HTTPException(status_code=400, detail="Invalid course ID")
            except Exception as decrypt_error:
                raise HTTPException(status_code=400, detail="Invalid encrypted course_id")
        
        # Get database session
        db: Session = next(get_db())
        
        try:
            connection = db.connection()
            
            # Call the stored procedure directly
            result = connection.execute(
                text("CALL usp_GetCoursesPublic(:p_course_id, :p_search, :p_category_id, :p_sort_by, :p_sort_order, :p_limit, :p_offset, :p_min_price, :p_max_price, :p_status)"),
                {
                    "p_course_id": decrypted_course_id,
                    "p_search": search,
                    "p_category_id": category_id,
                    "p_sort_by": sort_by,
                    "p_sort_order": sort_order,
                    "p_limit": limit,
                    "p_offset": offset,
                    "p_min_price": min_price,
                    "p_max_price": max_price,
                    "p_status": status
                }
            )
            
            # Fetch all results
            courses = result.mappings().fetchall()
            db.commit()
            
            if not courses:
                return {
                    "status": True, 
                    "message": "No courses found", 
                    "data": [],
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "total": 0,
                        "has_more": False
                    },
                    "note": "This endpoint works WITHOUT JWT authentication"
                }
            
            # Check if first result is an error message
            first_result = courses[0]
            if first_result.get("Message"):
                return {"status": False, "message": first_result.get("Message"), "data": []}
            
            # Build course list with encrypted IDs
            course_list = []
            for course in courses:
                try:
                    # Encrypt course_id and login_id_fk before sending
                    from helpers.helper import encrypt_the_string
                    encrypted_course_id = encrypt_the_string(str(course.get("course_id") or course.get("course_id_pk")))
                    encrypted_login_id_fk = encrypt_the_string(str(course.get("login_id_fk")))
                    
                    course_list.append({
                        "course_id": encrypted_course_id,
                        "course_name": course.get("course_name"),
                        "course_title": course.get("course_title"),
                        "course_description": course.get("course_description"),
                        "course_price": course.get("course_price"),
                        "course_image": course.get("course_image"),
                        "demo_video": course.get("demo_video"),
                        "login_id_fk": encrypted_login_id_fk,
                        "creator_email": course.get("creator_email"),
                        "creator_role": course.get("creator_role"),
                        "created_at": course.get("created_at"),
                        "updated_at": course.get("updated_at"),
                        "status": course.get("status"),
                        "category_id": course.get("category_id"),
                        "category_name": course.get("category_name")
                    })
                except Exception as encrypt_error:
                    # If encryption fails, skip this course
                    continue
            
            # Create filter description for message
            filter_desc = []
            if course_id:
                filter_desc.append(f"course ID {course_id[:8]}...")
            if search:
                filter_desc.append(f"search '{search}'")
            if category_id:
                filter_desc.append(f"category {category_id}")
            if min_price is not None or max_price is not None:
                price_range = f"price {min_price or 0}-{max_price or '∞'}"
                filter_desc.append(price_range)
            
            filter_text = " with " + ", ".join(filter_desc) if filter_desc else ""
            message = f"Found {len(course_list)} courses{filter_text} (NO JWT REQUIRED)"
            
            # Check if there are more results
            has_more = len(course_list) == limit
            
            return {
                "status": True,
                "message": message,
                "data": course_list,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "returned": len(course_list),
                    "has_more": has_more,
                    "next_offset": offset + limit if has_more else None
                },
                "filters": {
                    "course_id": course_id,
                    "search": search,
                    "category_id": category_id,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "min_price": min_price,
                    "max_price": max_price,
                    "status": status
                },
                "note": "This endpoint works WITHOUT JWT authentication"
            }
            
        except Exception as db_error:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        return {
            "status": False,
            "message": f"Public API Error: {str(e)}",
            "data": [],
            "note": "This endpoint should work WITHOUT JWT authentication"
        }

@router.post("/api/course/upload-content", tags=["CourseOperation"], summary="Upload video/content for a course")
async def upload_course_content(
    login_id_fk: Optional[str] = Form(None),  # Encrypted user ID (not used here, but could be for validation)
    course_id: str = Form(..., description="Encrypted course ID"),
    topic: str = Form(..., description="Topic name"),
    description: Optional[str] = Form(None, description="Topic description"),
    video_file: UploadFile = File(..., description="Video file"),
    assignment_file: Optional[UploadFile] = File(None, description="Assignment file (optional)"),
    questions_json: Optional[str] = Form(None, description="Questions in JSON format (optional)")
):
    """
    Upload a video (and optional assignment) for a course topic. Stores file URLs in DB.
    """
    try:
        # Decrypt course_id
        print(f"Uploading content for course_id: {course_id}, topic: {topic}")
        from helpers.helper import decrypt_the_string
        try:
            decrypted_course_id = int(decrypt_the_string(course_id.strip()))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid encrypted course_id")
        if decrypted_course_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid course ID")
        #decrypt login_id_fk if provided (not used here, but could be for validation)
        decrypted_user_id = None
        if login_id_fk and login_id_fk.strip():
            try:
                decrypted_user_id = int(decrypt_the_string(login_id_fk.strip()))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid encrypted login_id_fk")
        # Upload video file to FTP
        video_url = await upload_file_to_remote(video_file, f"course_{decrypted_course_id}", "video")
        assignment_url = None
        if assignment_file:
            assignment_url = await upload_file_to_remote(assignment_file, f"course_{decrypted_course_id}", "assignment")

        # Insert into DB using stored procedure
        from sqlalchemy.orm import Session
        from database.database import get_db
        from sqlalchemy import text
        db: Session = next(get_db())
        try:
            result = db.execute(
                text("CALL usp_InsertCourseContent(:p_login_id_fk,:p_course_id_fk, :p_topic, :p_description, :p_video_path, :p_assignment_path, :p_questions_json)"),
                {
                    "p_login_id_fk": decrypted_user_id,
                    "p_course_id_fk": decrypted_course_id,
                    "p_topic": topic,
                    "p_description": description,
                    "p_video_path": video_url,
                    "p_assignment_path": assignment_url,
                    "p_questions_json": questions_json
                }
            )
            # Fetch result from stored procedure
            content_result = result.mappings().fetchone()
            db.commit()
            
            # Check if there was an error from stored procedure
            if content_result and content_result.get("Status") != "Success":
                raise HTTPException(status_code=400, detail=content_result.get("Message", "Failed to insert course content"))
                
        except Exception as db_err:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"DB error: {str(db_err)}")
        finally:
            db.close()
        return {
            "status": True,
            "message": "Course content uploaded successfully!",
            "data": {
                "topic": topic,
                "video_url": video_url,
                "assignment_url": assignment_url
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/api/course/get-content", tags=["CourseOperation"], summary="Get course content by course ID")
async def get_course_content(
    course_id: str = Form(..., description="Encrypted course ID")
):
    """
    Get all course content (videos, assignments) for a specific course by course ID.
    Returns list of all topics with their video and assignment URLs.
    """
    try:
        # Decrypt course_id
        from helpers.helper import decrypt_the_string
        try:
            decrypted_course_id = int(decrypt_the_string(course_id.strip()))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid encrypted course_id")
        if decrypted_course_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid course ID")

        # Get course content using stored procedure
        from sqlalchemy.orm import Session
        from database.database import get_db
        from sqlalchemy import text
        db: Session = next(get_db())
        try:
            result = db.execute(
                text("CALL usp_GetCourseContent(:p_course_id_fk)"),
                {"p_course_id_fk": decrypted_course_id}
            )
            # Fetch all results from stored procedure
            content_results = result.mappings().fetchall()
            db.commit()
            
            # Check if there was an error from stored procedure
            if content_results and content_results[0].get("Status") == "Error":
                raise HTTPException(status_code=400, detail=content_results[0].get("Message", "Failed to fetch course content"))
            elif content_results and content_results[0].get("Status") == "Validation Error":
                raise HTTPException(status_code=400, detail=content_results[0].get("Message", "Validation failed"))
            
            # Process the results
            course_content_list = []
            for content in content_results:
                if content.get("Status") == "Success":
                    # Encrypt course_contents_id_pk before sending
                    from helpers.helper import encrypt_the_string
                    encrypted_content_id = encrypt_the_string(str(content.get("course_contents_id_pk")))
                    encrypted_course_id_fk = encrypt_the_string(str(content.get("course_id_fk")))
                    
                    course_content_list.append({
                        "course_contents_id_pk": encrypted_content_id,
                        "course_id_fk": encrypted_course_id_fk,
                        "topic": content.get("topic"),
                        "description": content.get("description"),
                        "video_path": content.get("video_path"),
                        "questions_json": content.get("questions_json"),
                        "assignment_path": content.get("assignment_path"),
                        "is_active": content.get("is_active"),
                        "created_at": content.get("created_at"),
                        "updated_at": content.get("updated_at")
                    })
                
        except Exception as db_err:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"DB error: {str(db_err)}")
        finally:
            db.close()
            
        return {
            "status": True,
            "message": f"Found {len(course_content_list)} course content items",
            "data": course_content_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get course content: {str(e)}")

@router.post("/api/course/get-content-by-id", tags=["CourseOperation"], summary="Get specific course content by primary key")
async def get_course_content_by_id(
    course_content_id: str = Form(..., description="Encrypted course content ID")
):
    """
    Get specific course content by course_contents_id_pk.
    Returns single course content item with video, assignment URLs and questions.
    """
    try:
        # Decrypt course_content_id
        from helpers.helper import decrypt_the_string
        try:
            decrypted_content_id = int(decrypt_the_string(course_content_id.strip()))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid encrypted course_content_id")
        if decrypted_content_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid course content ID")

        # Get specific course content using stored procedure
        from sqlalchemy.orm import Session
        from database.database import get_db
        from sqlalchemy import text
        db: Session = next(get_db())
        try:
            result = db.execute(
                text("CALL usp_GetCourseContentById(:p_course_contents_id_pk)"),
                {"p_course_contents_id_pk": decrypted_content_id}
            )
            # Fetch result from stored procedure
            content_result = result.mappings().fetchone()
            db.commit()
            
            # Check if there was an error from stored procedure
            if content_result and content_result.get("Status") == "Error":
                raise HTTPException(status_code=400, detail=content_result.get("Message", "Failed to fetch course content"))
            elif content_result and content_result.get("Status") == "Validation Error":
                raise HTTPException(status_code=400, detail=content_result.get("Message", "Validation failed"))
            elif content_result and content_result.get("Status") == "Not Found":
                raise HTTPException(status_code=404, detail=content_result.get("Message", "Course content not found"))
            
            # Process the result
            if content_result and content_result.get("Status") == "Success":
                # Encrypt IDs before sending
                from helpers.helper import encrypt_the_string
                encrypted_content_id = encrypt_the_string(str(content_result.get("course_contents_id_pk")))
                encrypted_course_id_fk = encrypt_the_string(str(content_result.get("course_id_fk")))
                
                course_content_data = {
                    "course_contents_id_pk": encrypted_content_id,
                    "course_id_fk": encrypted_course_id_fk,
                    "topic": content_result.get("topic"),
                    "description": content_result.get("description"),
                    "video_path": content_result.get("video_path"),
                    "questions_json": content_result.get("questions_json"),
                    "assignment_path": content_result.get("assignment_path"),
                    "is_active": content_result.get("is_active"),
                    "created_at": content_result.get("created_at"),
                    "updated_at": content_result.get("updated_at")
                }
            else:
                raise HTTPException(status_code=404, detail="Course content not found")
                
        except HTTPException:
            raise
        except Exception as db_err:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"DB error: {str(db_err)}")
        finally:
            db.close()
            
        return {
            "status": True,
            "message": "Course content retrieved successfully",
            "data": course_content_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get course content: {str(e)}")

# Stored-procedure to create in MySQL (run once in your DB). It uses dynamic SQL (PREPARE) and returns selected rows.

# Notes:
# - This procedure runs dynamic SQL. For production, validate table_name/columns against a whitelist to avoid SQL injection.
# - The API will call this procedure and return rows. Use p_table_name='courses' and p_columns='course_id_pk,course_name' to get course id/name.

@router.post("/api/course/flexible-query", tags=["CourseOperation"], summary="Flexible table query via stored procedure")
async def flexible_query(
    request: Request,
    table_name: Optional[str] = Form(None, description="Table name (mandatory)"),
    columns: Optional[str] = Form(None, description="Columns to select, comma-separated (mandatory)"),
    where_clause: Optional[str] = Form(None, description="Optional WHERE clause (without 'WHERE')"),
    group_by: Optional[str] = Form(None, description="Optional GROUP BY clause (columns)"),
    order_by: Optional[str] = Form(None, description="Optional ORDER BY clause"),
    limit: Optional[int] = Form(None, description="Optional LIMIT"),
    offset: Optional[int] = Form(None, description="Optional OFFSET"),
    login_id_fk: Optional[str] = Form(None, description="Optional encrypted login_id_fk to add to WHERE")
):
    """
    Flexible query API. Accepts form-data or JSON.
    Example JSON:
    {
      "table_name": "courses",
      "columns": "course_id_pk,course_name",
      "login_id_fk": "ENCRYPTED_STRING"
    }
    """
    try:
        # If client sent JSON, merge values from JSON body (JSON overrides form fields)
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    table_name = body.get("table_name", table_name)
                    columns = body.get("columns", columns)
                    where_clause = body.get("where_clause", where_clause) or body.get("where", where_clause)
                    group_by = body.get("group_by", group_by)
                    order_by = body.get("order_by", order_by)
                    limit = int(body.get("limit")) if body.get("limit") is not None else limit
                    offset = int(body.get("offset")) if body.get("offset") is not None else offset
                    login_id_fk = body.get("login_id_fk", login_id_fk)
            except Exception as e:
                logger.info(f"Failed to parse JSON body for flexible-query: {e}")

        # Validate mandatory inputs now and return clear 400 if missing
        if not table_name or not str(table_name).strip():
            raise HTTPException(status_code=400, detail="table_name is required")
        if not columns or not str(columns).strip():
            raise HTTPException(status_code=400, detail="columns is required")

        # Decrypt login_id_fk if provided (it may be encrypted string)
        decrypted_login_id = None
        if login_id_fk is not None and str(login_id_fk).strip() != "":
            try:
                # If client accidentally sent numeric string, accept it without decrypt
                raw = str(login_id_fk).strip()
                if raw.isdigit():
                    decrypted_login_id = int(raw)
                else:
                    from helpers.helper import decrypt_the_string
                    decrypted_login_id = int(decrypt_the_string(raw))
            except Exception as e:
                logger.error(f"Failed to decrypt login_id_fk: {e}")
                raise HTTPException(status_code=400, detail="Invalid encrypted login_id_fk")

        # Build params for stored procedure (NULLs allowed)
        params = {
            "p_table_name": str(table_name).strip(),
            "p_columns": str(columns).strip(),
            "p_where": where_clause.strip() if where_clause and str(where_clause).strip() else None,
            "p_group_by": group_by.strip() if group_by and str(group_by).strip() else None,
            "p_order_by": order_by.strip() if order_by and str(order_by).strip() else None,
            "p_limit": int(limit) if limit is not None else None,
            "p_offset": int(offset) if offset is not None else None,
            "p_login_id_fk": int(decrypted_login_id) if decrypted_login_id is not None else None
        }

        # Execute stored procedure
        from sqlalchemy.orm import Session
        from database.database import get_db
        from sqlalchemy import text

        db: Session = next(get_db())
        try:
            connection = db.connection()
            logger.info(f"Calling usp_FlexibleQuery for table={params['p_table_name']} columns={params['p_columns']}")
            result = connection.execute(
                text("CALL usp_FlexibleQuery(:p_table_name, :p_columns, :p_where, :p_group_by, :p_order_by, :p_limit, :p_offset, :p_login_id_fk)"),
                params
            )
            rows = result.mappings().fetchall()
            db.commit()
        except Exception as db_err:
            db.rollback()
            logger.error(f"DB error in usp_FlexibleQuery: {db_err}")
            raise HTTPException(status_code=500, detail=f"DB error: {str(db_err)}")
        finally:
            db.close()

        # Convert to list of dicts and encrypt course id fields if present and non-empty
        data = []
        if rows:
            from helpers.helper import encrypt_the_string
            for r in rows:
                row = dict(r)
                # Encrypt course id fields if present and non-empty
                for id_key in ("course_id_pk", "course_id"):
                    val = row.get(id_key)
                    if val is not None and str(val).strip() != "":
                        try:
                            row[id_key] = encrypt_the_string(str(val))
                        except Exception as e:
                            logger.info(f"Failed to encrypt {id_key}: {e}")
                data.append(row)
        return {"status": True, "message": f"Returned {len(data)} rows", "data": data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flexible query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



