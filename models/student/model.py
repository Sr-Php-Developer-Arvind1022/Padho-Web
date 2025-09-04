# all deserialize models 
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any,Literal
from pydantic import BaseModel,Field,Json,Extra, model_validator
from typing import List, Literal,Optional,Annotated 
from fastapi import UploadFile

class StudentLogin(BaseModel):
    email: str
    password: str