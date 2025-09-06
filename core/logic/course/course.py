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
        
        if not result_data:
            return {"status": False, "message": "Course registration failed", "data": []}
        
        message = result_data.get("Message", "Unknown error occurred")
        if result_data and result_data.get("Status", "Error").lower() == "success":
            return {
                "message": message,
                "status": True,
                "data": {
                    "course_id": result_data.get("course_id"),
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
            course_list.append({
                "course_id": course.get("course_id"),
                "course_name": course.get("course_name"),
                "course_title": course.get("course_title"),
                "course_description": course.get("course_description"),
                "course_price": course.get("course_price"),
                "course_image": course.get("course_image"),
                "demo_video": course.get("demo_video"),
                "login_id_fk": course.get("login_id_fk"),
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

async def get_course_by_id(course_id: int):
    db: Session = next(get_db())
    
    try:
        connection = db.connection()
        
        # Execute the stored procedure to get course by ID
        result = connection.execute(
            text("CALL usp_GetCourseById(:p_course_id)"),
            {"p_course_id": course_id}
        )
        
        # Fetch the result
        course_data = result.mappings().fetchone()
        db.commit()
        
        if not course_data:
            return {"status": False, "message": "Course not found", "data": []}
        
        return {
            "status": True,
            "message": "Course retrieved successfully",
            "data": {
                "course_id": course_data.get("course_id"),
                "course_name": course_data.get("course_name"),
                "course_title": course_data.get("course_title"),
                "course_description": course_data.get("course_description"),
                "course_price": course_data.get("course_price"),
                "course_image": course_data.get("course_image"),
                "demo_video": course_data.get("demo_video"),
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
            course_list.append({
                "course_id": course.get("course_id"),
                "course_name": course.get("course_name"),
                "course_title": course.get("course_title"),
                "course_description": course.get("course_description"),
                "course_price": course.get("course_price"),
                "course_image": course.get("course_image"),
                "demo_video": course.get("demo_video"),
                "creator_name": course.get("creator_name"),
                "creator_email": course.get("creator_email"),
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
            course_list.append({
                "course_id": course.get("course_id") or course.get("course_id_pk"),
                "course_name": course.get("course_name"),
                "course_title": course.get("course_title"),
                "course_description": course.get("course_description"),
                "course_price": course.get("course_price"),
                "course_image": course.get("course_image"),
                "demo_video": course.get("demo_video"),
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
        
        if not result_data:
            return {"status": False, "message": "Course update failed", "data": []}
        
        message = result_data.get("Message", "Unknown error occurred")
        status = result_data.get("Status", "Error").lower()
        
        if status == "success":
            return {
                "status": True,
                "message": message,
                "data": {
                    "course_id": course_id,
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
