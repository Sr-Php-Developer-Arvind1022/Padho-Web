"""
Transaction API Routes

This module handles transaction-related operations including:
- Transaction extraction from natural language input (English/Hindi/Marathi/Hinglish)
- Automatic transaction classification (credit/debit)
- Transaction history retrieval
- Transaction save/update operations

Features:
- AI-powered transaction extraction using Groq LLaMA model
- Multi-language support (English, Hindi, Marathi, Hinglish)
- Automatic counterparty identification
- Transaction status tracking
- Confidence scoring for extracted transactions

Usage Examples:
1. Extract Transactions:
   POST /api/transaction/extract
   {
     "text": "maine Ravi ko 500 diya"
   }
   - Requires JWT authentication
   - Returns extracted transactions with status

2. Get Transaction History:
   GET /api/transaction/history
   - Requires JWT authentication
   - Returns all transactions for the authenticated user
"""


from fastapi import APIRouter, HTTPException, Form, Query
from pydantic import BaseModel
from typing import Optional, List
import logging
from core.logic.Transaction.transaction import extract_transactions

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Request/Response Models ============
class TransactionExtractRequest(BaseModel):
    """Request model for transaction extraction"""
    text: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "maine Ravi ko 500 diya"
            }
        }


class TransactionResponse(BaseModel):
    """Individual transaction response"""
    transaction_id: str
    date: str
    counterparty: str
    amount: float
    transaction_type: str
    description: str
    notes: Optional[str] = None
    status: str


class ExtractTransactionResponse(BaseModel):
    """Response model for transaction extraction"""
    status: str
    message: str
    data: dict
    

# ============ API Endpoints ============

@router.post(
    "/api/transaction/extract",
    tags=["TransactionOperation"],
    summary="Extract transactions from natural language",
    response_model=ExtractTransactionResponse
)
async def extract_transaction_endpoint(
    text: str = Form(...),
    user_id: int = Form(...)
):
    """
    Endpoint to extract transactions from natural language input.
    
    Supports English, Hindi, Marathi, and Hinglish input.
    Automatically identifies:
    - Transaction type (credit/debit)
    - Amount
    - Counterparty
    - Transaction date
    
    Args:
        text: Natural language transaction description
        user_id: User ID (no authentication required)
        
    Returns:
        Extracted transactions with confidence score
    """
    try:
        logger.info(f"💰 Transaction extraction request: user={user_id}, text_length={len(text)}")
        
        # Create request object with user_id and text
        class Request:
            def __init__(self, user_id, text):
                self.user_id = user_id
                self.text = text
        
        request = Request(user_id, text)
        
        # Call extract_transactions from core logic
        result = await extract_transactions(request)
        
        logger.info(f"✅ Transaction extraction completed: user={user_id}")
        
        return {
            "status": result.get("status", "success"),
            "message": result.get("message", "Transactions extracted"),
            "data": result.get("data", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Transaction extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transaction extraction error: {str(e)}"
        )


@router.get(
    "/api/transaction/history",
    tags=["TransactionOperation"],
    summary="Get transaction history"
)
async def get_transaction_history(
    user_id: int = Query(...),
    limit: Optional[int] = Query(50),
    skip: Optional[int] = Query(0)
):
    """
    Endpoint to retrieve transaction history for a user.
    
    Args:
        user_id: User ID (query parameter, no authentication required)
        limit: Maximum number of transactions to return (default: 50)
        skip: Number of transactions to skip for pagination (default: 0)
        
    Returns:
        List of transactions for the user
    """
    try:
        logger.info(f"📜 Fetching transaction history: user={user_id}, limit={limit}, skip={skip}")
        
        # Import GetTransactionHistory from transaction_history module
        from core.logic.Transaction.transaction_history import GetTransactionHistory
        
        # Call GetTransactionHistory from transaction_history module
        result = GetTransactionHistory(user_id, limit, skip)
        
        logger.info(f"✅ Retrieved {len(result.get('transactions', []))} transactions for user={user_id}")
        
        return {
            "status": "success",
            "message": "Transaction history retrieved",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve transaction history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transaction history: {str(e)}"
        )
