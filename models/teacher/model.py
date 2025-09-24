
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any,Literal
from pydantic import BaseModel,Field,Json,Extra, model_validator
from typing import List, Literal,Optional,Annotated 
from fastapi import UploadFile

class RegisterTeacher(BaseModel):
    name : str
    username : str
    password : str
    hire_date : str
    role : str
    specialization : str
    phone : str
    address : str
    
class DeleteTeacher(BaseModel):
    id : int