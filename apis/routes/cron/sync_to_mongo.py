from fastapi import APIRouter, HTTPException
from core.logic.cron.sync import call_flexible_query_and_sync

router = APIRouter()

@router.get("/api/cron/sync-login-table", tags=["Cron"], summary="Trigger login_table sync to MongoDB (no params)")
async def sync_login_table_trigger():
    """
    Trigger sync of 'logins' -> Mongo 'login_table' for role = 'student'.
    No parameters required; calling this URL will perform the sync.
    """
    try:
        result = call_flexible_query_and_sync(
            table_name="logins",
            columns=["username", "password"],
            where_clause="role = 'student'",
            mongo_collection="login_table"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


