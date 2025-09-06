from fastapi import FastAPI, File, Form, HTTPException,APIRouter, UploadFile
from models.student.model import *


from core.logic.student.login import *

router= APIRouter()

@router.post("/api/student/register",tags=["StudentLoginOperation"],summary=" ")
async def login(student: StudentRegister):
    """
    Endpoint to handle user login.
    """
    try:
       
       data = await student_register(student)
       return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/api/student/login",tags=["StudentLoginOperation"],summary=" ")
async def login(student: StudentLogin):
    """
    Endpoint to handle user login.
    """
    try:
       data = await student_login(student)
       return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    