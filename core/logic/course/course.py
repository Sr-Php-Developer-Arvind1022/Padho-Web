from asyncio.log import logger
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from database.database import get_db

async def course_register(course, course_image_path=None, demo_video_path=None):
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Validate input fields
        if not course.course_name:
            return {"status": False, "message": "Course name field is required", "data": []}
        
        if not course.course_title:
            return {"status": False, "message": "Course title field is required", "data": []}
        
        # Execute the stored procedure for course registration
        result = connection.execute(
            text(
                """
                CALL usp_CourseRegister(
                    :p_course_name, 
                    :p_course_title,
                    :p_course_description, 
                    :p_course_price,
                    :p_course_image,
                    :p_demo_video,
                    :p_login_id_fk
                )
                """
            ),
            {
                "p_course_name": course.course_name,
                "p_course_title": course.course_title,
                "p_course_description": course.course_description,
                "p_course_price": course.course_price,
                "p_course_image": course_image_path,
                "p_demo_video": demo_video_path,
                "p_login_id_fk": course.login_id_fk,
            },
        )
        
        # Fetch the result from the stored procedure
        result_data = result.mappings().fetchone()
        print("Course registration data => ", result_data)
        db.commit()
        from helpers.helper import clear_courses_cache
        clear_courses_cache()
        if not result_data:
            return {"status": False, "message": "Course registration failed", "data": []}
        
        message = result_data.get("Message", "Unknown error occurred")
        if result_data and result_data.get("Status", "Error").lower() == "success":
            # Encrypt course_id before sending
            from helpers.helper import encrypt_the_string
            encrypted_course_id = encrypt_the_string(str(result_data.get("course_id")))
            
            return {
                "message": message,
                "status": True,
                "data": {
                    "course_id": encrypted_course_id,
                    "course_name": course.course_name,
                    "course_title": course.course_title
                }
            }
        else:
            return {
                "status": False, 
                "message": result_data.get("Message", "Course registration failed") if result_data else "Course registration failed", 
                "data": []
            }
    
    except HTTPException as http_err:
        raise http_err
    
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()

async def get_all_courses(user_id=None):
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Execute the stored procedure to get all courses or courses by user
        if user_id:
            result = connection.execute(
                text("CALL usp_GetCoursesByUser(:p_login_id_fk)"),
                {"p_login_id_fk": user_id}
            )
        else:
            result = connection.execute(
                text("CALL usp_GetAllCourses()")
            )
        
        # Fetch all results
        courses = result.mappings().fetchall()
        db.commit()
        
        if not courses:
            return {"status": True, "message": "No courses found", "data": []}
        
        # Check if first result is an error message (for user-specific queries)
        if user_id and courses:
            first_result = courses[0]
            if first_result.get("Message"):
                return {"status": False, "message": first_result.get("Message"), "data": []}
        
        course_list = []
        for course in courses:
            # Encrypt course_id and login_id_fk before sending
            from helpers.helper import encrypt_the_string
            encrypted_course_id = encrypt_the_string(str(course.get("course_id")))
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
                "created_at": course.get("created_at")
            })
        
        message = f"Found {len(course_list)} courses" if user_id else "Courses retrieved successfully"
        return {
            "status": True,
            "message": message,
            "data": course_list
        }
    
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()

async def get_course_by_id(course_id: int, user_id: int = None):
    db: Session = next(get_db())
    try:
        connection = db.connection()
        
        # Validate required parameters
        if not course_id:
            return {"status": False, "message": "Course ID is required", "data": []}
        
        if not user_id:
            return {"status": False, "message": "User authentication is required", "data": []}
        
        # Execute the stored procedure to get course by ID
        result = connection.execute(
            text("CALL usp_GetCourseById(:p_course_id, :p_login_id_fk)"),
            {
                "p_course_id": course_id,
                "p_login_id_fk": user_id
            }
        )
        
        # Fetch the result
        course_data = result.mappings().fetchone()
        db.commit()
        
        if not course_data:
            return {"status": False, "message": "Course not found", "data": []}
        
        # Check if result contains an error message
        if course_data.get("Message"):
            return {"status": False, "message": course_data.get("Message"), "data": []}
        
        # Encrypt course_id and login_id_fk before sending
        from helpers.helper import encrypt_the_string
        encrypted_course_id = encrypt_the_string(str(course_data.get("course_id")))
        encrypted_login_id_fk = encrypt_the_string(str(course_data.get("login_id_fk")))
        
        return {
            "status": True,
            "message": "Course retrieved successfully",
            "data": {
                "course_id": encrypted_course_id,
                "course_name": course_data.get("course_name"),
                "course_title": course_data.get("course_title"),
                "course_description": course_data.get("course_description"),
                "course_price": course_data.get("course_price"),
                "course_image": course_data.get("course_image"),
                "demo_video": course_data.get("demo_video"),
                "login_id_fk": encrypted_login_id_fk,
                "creator_email": course_data.get("creator_email"),
                "creator_role": course_data.get("creator_role"),
                "created_at": course_data.get("created_at")
            }
        }
    
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()

async def get_courses_by_user(user_id: int):
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Execute the stored procedure to get courses by user
        result = connection.execute(
            text("CALL usp_GetCoursesByUser(:p_login_id_fk)"),
            {"p_login_id_fk": user_id}
        )
        
        # Fetch all results
        courses = result.mappings().fetchall()
        db.commit()
        
        if not courses:
            return {"status": True, "message": "No courses found for this user", "data": []}
        
        # Check if first result is an error message
        first_result = courses[0]
        if first_result.get("Message"):
            return {"status": False, "message": first_result.get("Message"), "data": []}
        
        course_list = []
        for course in courses:
            # Encrypt course_id and login_id_fk before sending
            from helpers.helper import encrypt_the_string
            encrypted_course_id = encrypt_the_string(str(course.get("course_id")))
            encrypted_login_id_fk = encrypt_the_string(str(course.get("login_id_fk")))
            
            course_list.append({
                "course_id": encrypted_course_id,
                "course_name": course.get("course_name"),
                "course_title": course.get("course_title"),
                "course_description": course.get("course_description"),
                "course_price": course.get("course_price"),
                "course_image": course.get("course_image"),
                "demo_video": course.get("demo_video"),
                "creator_name": course.get("creator_name"),
                "creator_email": course.get("creator_email"),
                "login_id_fk": encrypted_login_id_fk,
                "created_at": course.get("created_at")
            })
        
        return {
            "status": True,
            "message": f"Found {len(course_list)} courses",
            "data": course_list
        }
    
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()

async def get_all_courses_with_filters(user_id=None, search=None, limit=10, offset=0):
    """
    Get all courses with advanced filtering options using stored procedure:
    - user_id: Filter by specific user
    - search: Search in course name, title, description
    - limit: Number of results to return
    - offset: Number of results to skip (pagination)
    """
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Set defaults
        if not limit or limit <= 0:
            limit = 10
        if not offset or offset < 0:
            offset = 0
        
        # Clean the search parameter
        clean_search = None
        if search and search.strip() and search.strip().lower() != 'none':
            clean_search = search.strip()
        
        # Execute the stored procedure with all filters
        result = connection.execute(
            text("CALL usp_GetAllCoursesWithFilters(:p_login_id_fk, :p_search, :p_limit, :p_offset)"),
            {
                "p_login_id_fk": user_id if user_id and user_id > 0 else None,
                "p_search": clean_search,
                "p_limit": limit,
                "p_offset": offset
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
                    "total": 0
                }
            }
        
        # Check if first result is an error message
        first_result = courses[0]
        if first_result.get("Message"):
            return {"status": False, "message": first_result.get("Message"), "data": []}
        
        course_list = []
        for course in courses:
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
                "status": course.get("status")
            })
        
        # Create filter description for message
        filter_desc = []
        if user_id:
            filter_desc.append(f"user ID {user_id}")
        if search:
            filter_desc.append(f"search term '{search}'")
        
        filter_text = " with " + " and ".join(filter_desc) if filter_desc else ""
        message = f"Found {len(course_list)} courses{filter_text}"
        
        return {
            "status": True,
            "message": message,
            "data": course_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "returned": len(course_list)
            }
        }
    
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()

async def search_courses_with_filters(search=None, user_id=None, limit=10, offset=0):
    """
    Search courses with filters - wrapper function for backwards compatibility
    """
    return await get_all_courses_with_filters(user_id=user_id, search=search, limit=limit, offset=offset)

async def update_course_by_id(course_id, user_id, course_name=None, course_title=None, 
                            course_description=None, course_price=None, 
                            course_image_path=None, demo_video_path=None):
    """
    Update course by ID - only course creator can update
    """
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Validate required parameters
        if not course_id or course_id <= 0:
            return {"status": False, "message": "Valid course ID is required", "data": []}
        
        if not user_id or user_id <= 0:
            return {"status": False, "message": "User authentication is required", "data": []}
        
        # Execute the stored procedure to update course
        result = connection.execute(
            text("""
                CALL usp_UpdateCourseByLoginId(
                    :p_course_id,
                    :p_login_id_fk,
                    :p_course_name,
                    :p_course_title,
                    :p_course_description,
                    :p_course_price,
                    :p_course_image,
                    :p_demo_video
                )
            """),
            {
                "p_course_id": course_id,
                "p_login_id_fk": user_id,
                "p_course_name": course_name,
                "p_course_title": course_title,
                "p_course_description": course_description,
                "p_course_price": course_price,
                "p_course_image": course_image_path,
                "p_demo_video": demo_video_path
            }
        )
        
        # Fetch the result
        result_data = result.mappings().fetchone()
        db.commit()
        from helpers.helper import clear_courses_cache
        clear_courses_cache()
        if not result_data:
            return {"status": False, "message": "Course update failed", "data": []}
        
        message = result_data.get("Message", "Unknown error occurred")
        status = result_data.get("Status", "Error").lower()
        
        if status == "success":
            # Encrypt course_id before sending
            from helpers.helper import encrypt_the_string
            encrypted_course_id = encrypt_the_string(str(course_id))
            
            return {
                "status": True,
                "message": message,
                "data": {
                    "course_id": encrypted_course_id,
                    "updated_fields": {
                        k: v for k, v in {
                            "course_name": course_name,
                            "course_title": course_title,
                            "course_description": course_description,
                            "course_price": course_price,
                            "course_image": course_image_path,
                            "demo_video": demo_video_path
                        }.items() if v is not None
                    }
                }
            }
        else:
            return {"status": False, "message": message, "data": []}
    
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()

async def get_courses_public_with_filters1(
    course_id=None, search=None, category_id=None, sort_by="created_at", 
    sort_order="desc", limit=10, offset=0, min_price=None, max_price=None, status="active"
):
    """
    Public function to get courses with advanced filtering, sorting, and pagination.
    No authentication required - for public access.
    
    Features:
    1. Get specific course by ID
    2. Search in course name, title, description
    3. Category filtering (ready for implementation)
    4. Sorting by multiple fields
    5. Price range filtering
    6. Pagination for chunk loading
    7. Status filtering
    """
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Set defaults
        if not limit or limit <= 0:
            limit = 10
        if not offset or offset < 0:
            offset = 0
        
        # Execute the stored procedure with all filters
        result = connection.execute(
            text("CALL usp_GetCoursesPublic(:p_course_id, :p_search, :p_category_id, :p_sort_by, :p_sort_order, :p_limit, :p_offset, :p_min_price, :p_max_price, :p_status)"),
            {
                "p_course_id": course_id if course_id and course_id > 0 else None,
                "p_search": search,
                "p_category_id": category_id if category_id and category_id > 0 else None,
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
                "filters": {
                    "course_id": course_id,
                    "search": search,
                    "category_id": category_id,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "min_price": min_price,
                    "max_price": max_price,
                    "status": status
                }
            }
        
        # Check if first result is an error message
        first_result = courses[0]
        if first_result.get("Message"):
            return {"status": False, "message": first_result.get("Message"), "data": []}
        
        # Build course list with encrypted IDs
        course_list = []
        for course in courses:
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
        
        # Create filter description for message
        filter_desc = []
        if course_id:
            filter_desc.append(f"course ID {course_id}")
        if search:
            filter_desc.append(f"search '{search}'")
        if category_id:
            filter_desc.append(f"category {category_id}")
        if min_price is not None or max_price is not None:
            price_range = f"price {min_price or 0}-{max_price or '∞'}"
            filter_desc.append(price_range)
        
        filter_text = " with " + ", ".join(filter_desc) if filter_desc else ""
        message = f"Found {len(course_list)} courses{filter_text}"
        
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
            }
        }
    
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()
async def get_courses_public_with_filters(
    course_id=None, search=None, category_id=None, sort_by="created_at", 
    sort_order="desc", limit=10, offset=0, min_price=None, max_price=None, status="active"
):
    """
    Public function to get courses with advanced filtering, sorting, and pagination.
    No authentication required - for public access.
    
    Features:
    1. Get specific course by ID
    2. Search in course name, title, description
    3. Category filtering (ready for implementation)
    4. Sorting by multiple fields
    5. Price range filtering
    6. Pagination for chunk loading
    7. Status filtering
    8. Redis caching for performance
    """
    import redis
    import json
    
    # Initialize Redis connection
    r = redis.Redis.from_url("rediss://default:AUEQAAIncDIwOTk0M2IwYWU5MTI0N2NjODAzZjhhNGEyZTMxZmI2ZHAyMTY2NTY@vast-reindeer-16656.upstash.io:6379")
    
    # Create unique cache key based on all filters
    cache_key = f"courses:filters:{course_id}:{search}:{category_id}:{sort_by}:{sort_order}:{limit}:{offset}:{min_price}:{max_price}:{status}"
    
    # Try to get data from Redis first
    try:
        cached_data = r.get(cache_key)
        if cached_data:
            logger.info(f"Returning cached data for key: {cache_key}")
            cached_response = json.loads(cached_data.decode())
            cached_response["source"] = "redis_cache"
            return cached_response
    except Exception as redis_err:
        logger.warning(f"Redis get error: {str(redis_err)}, proceeding with DB query")
    
    # If not in cache, fetch from database
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Set defaults
        if not limit or limit <= 0:
            limit = 10
        if not offset or offset < 0:
            offset = 0
        
        # Execute the stored procedure with all filters
        result = connection.execute(
            text("CALL usp_GetCoursesPublic(:p_course_id, :p_search, :p_category_id, :p_sort_by, :p_sort_order, :p_limit, :p_offset, :p_min_price, :p_max_price, :p_status)"),
            {
                "p_course_id": course_id if course_id and course_id > 0 else None,
                "p_search": search,
                "p_category_id": category_id if category_id and category_id > 0 else None,
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
            response = {
                "status": True, 
                "message": "No courses found", 
                "data": [],
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": 0,
                    "has_more": False
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
                "source": "database"
            }
            
            # Cache empty result too (with shorter TTL)
            try:
                r.setex(cache_key, 300, json.dumps(response))  # 5 minutes for empty results
            except Exception as redis_err:
                logger.warning(f"Redis set error: {str(redis_err)}")
            
            return response
        
        # Check if first result is an error message
        first_result = courses[0]
        if first_result.get("Message"):
            return {"status": False, "message": first_result.get("Message"), "data": [], "source": "database"}
        
        # Build course list with encrypted IDs
        course_list = []
        for course in courses:
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
                "created_at": str(course.get("created_at")) if course.get("created_at") else None,
                "updated_at": str(course.get("updated_at")) if course.get("updated_at") else None,
                "status": course.get("status"),
                "category_id": course.get("category_id"),
                "category_name": course.get("category_name")
            })
        
        # Create filter description for message
        filter_desc = []
        if course_id:
            filter_desc.append(f"course ID {course_id}")
        if search:
            filter_desc.append(f"search '{search}'")
        if category_id:
            filter_desc.append(f"category {category_id}")
        if min_price is not None or max_price is not None:
            price_range = f"price {min_price or 0}-{max_price or '∞'}"
            filter_desc.append(price_range)
        
        filter_text = " with " + ", ".join(filter_desc) if filter_desc else ""
        message = f"Found {len(course_list)} courses{filter_text}"
        
        # Check if there are more results
        has_more = len(course_list) == limit
        
        response = {
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
            "source": "database"
        }
        
        # Store in Redis with TTL (1 hour = 3600 seconds)
        try:
            r.setex(cache_key, 3600, json.dumps(response))
            logger.info(f"Cached data for key: {cache_key}")
        except Exception as redis_err:
            logger.warning(f"Redis set error: {str(redis_err)}")
        
        return response
    
    except Exception as err:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(err)}"
        )
    
    finally:
        db.close()