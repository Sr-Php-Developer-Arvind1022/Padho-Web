from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"

class OrderStatus(str, Enum):
    pending_verification = "pending-verification"
    approved = "approved"
    cancelled = "cancelled"

class CourseOrderCreate(BaseModel):
    course_id: str = Field(..., description="Encrypted course ID")
    login_id_fk: str = Field(..., description="Encrypted login ID")
    order_amount: float = Field(..., gt=0, description="Order amount must be greater than 0")
    payment_method: Optional[str] = Field(None, max_length=50, description="Payment method")
    transaction_id: Optional[str] = Field(None, max_length=100, description="Transaction ID")
    
    @validator('course_id')
    def validate_course_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Course ID is required')
        return v.strip()
    
    @validator('login_id_fk')
    def validate_login_id_fk(cls, v):
        if not v or not v.strip():
            raise ValueError('Login ID is required')
        return v.strip()
    
    @validator('order_amount')
    def validate_order_amount(cls, v):
        if v <= 0:
            raise ValueError('Order amount must be greater than 0')
        return round(v, 2)

class CourseOrderResponse(BaseModel):
    order_id_pk: str  # Encrypted order ID
    course_id_fk: str  # Encrypted course ID
    login_id_fk: str  # Encrypted login ID
    order_date: datetime
    order_amount: float
    payment_status: PaymentStatus
    payment_method: Optional[str]
    transaction_id: Optional[str]
    order_status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CourseOrderUpdate(BaseModel):
    order_id_pk: str = Field(..., description="Encrypted order ID")
    payment_status: Optional[PaymentStatus] = None
    order_status: Optional[OrderStatus] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    transaction_id: Optional[str] = Field(None, max_length=100)
    
    @validator('order_id_pk')
    def validate_order_id_pk(cls, v):
        if not v or not v.strip():
            raise ValueError('Order ID is required')
        return v.strip()

class CourseOrderFilter(BaseModel):
    course_id: Optional[str] = Field(None, description="Encrypted course ID filter")
    login_id_fk: Optional[str] = Field(None, description="Encrypted login ID filter")
    payment_status: Optional[PaymentStatus] = None
    order_status: Optional[OrderStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = Field(10, ge=1, le=100)
    offset: Optional[int] = Field(0, ge=0)
    
    @validator('limit')
    def validate_limit(cls, v):
        if v is None or v <= 0 or v > 100:
            return 10
        return v
    
    @validator('offset')
    def validate_offset(cls, v):
        if v is None or v < 0:
            return 0
        return v
