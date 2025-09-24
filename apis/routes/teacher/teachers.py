from fastapi import FastAPI, File, Form, HTTPException, APIRouter, UploadFile, Depends, Request
from models.teacher.model import *
from core.logic.teacher.teachers import *
from authentication.token_handler import *
from typing import Optional

router = APIRouter()

@router.post("/api/teacher/register", tags=["TeacherLoginOperation"], summary="Register new student")
async def register_teacher(teacher: RegisterTeacher):
    """
    Endpoint to handle student registration.
    """
    try:
       data = await teacher_register(teacher)
       return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/api/teacher/list", tags=["TeacherLoginOperation"], summary="Register new student")
async def list_teacher():
    """
    Endpoint to handle student registration.
    """
    try:
       data = await getAllTeacher()
       return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.delete("/api/teacher/delete", tags=["TeacherLoginOperation"], summary="Register new student")
async def delete_teacher(teacher:DeleteTeacher):
    """
    Endpoint to handle student registration.
    """
    try:
       data = await teacher_delete(teacher)
       return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))