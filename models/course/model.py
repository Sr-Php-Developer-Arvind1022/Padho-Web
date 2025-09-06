from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from fastapi import UploadFile

class CourseRegister(BaseModel):
    course_name: str = Field(..., min_length=1, max_length=255)
    course_title: str = Field(..., min_length=1, max_length=255)
    course_description: Optional[str] = Field(None, max_length=2000)
    course_price: Optional[float] = Field(None, ge=0)
    login_id_fk: Optional[int] = Field(None)  # Student/Teacher ID who created the course
    # Note: course_image and demo_video will be handled as UploadFile in the route
    
class CourseUpdate(BaseModel):
    course_id: int
    course_name: Optional[str] = Field(None, min_length=1, max_length=255)
    course_title: Optional[str] = Field(None, min_length=1, max_length=255)
    course_description: Optional[str] = Field(None, max_length=2000)
    course_price: Optional[float] = Field(None, ge=0)
