from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class SyncRequest(BaseModel):
    table: str
    columns: Optional[List[str]] = None  # list of column names (will be joined if provided)
    where: Optional[Dict[str, Any]] = None  # dict for where conditions, may include encrypted login_id
    mongo_collection: Optional[str] = "login_table"
    mongo_db: Optional[str] = None  # override via request (optional)
    limit: Optional[int] = None
    offset: Optional[int] = None
