import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from database.database import get_db
from helpers.helper import decrypt_the_string
from pymongo import MongoClient
from datetime import datetime
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://arvind:arvind123@cluster0.d3e8kz2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
MONGO_DB = os.getenv("MONGO_DB", "StudentManagementDb")

def _get_mongo_client():
    return MongoClient(MONGO_URI)

# New helper: format "field = value" safely for p_where
def _format_where_eq(field: str, value: Any) -> str:
    """
    Return "field = <value>" where numeric values are unquoted and others are single-quoted safely.
    """
    if value is None:
        return f"{field} IS NULL"
    try:
        # try integer
        intval = int(value)
        return f"{field} = {intval}"
    except Exception:
        # fallback: quote and escape single quotes
        s = str(value).replace("'", "''")
        return f"{field} = '{s}'"

def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    # Convert SQLAlchemy RowMapping to plain dict and normalize datetimes and unsupported types
    doc = {}
    try:
        # Try to import Decimal128 for precise Decimal storage in Mongo
        from bson.decimal128 import Decimal128  # type: ignore
    except Exception:
        Decimal128 = None

    for k, v in row.items():
        # normalize datetime
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
            continue

        # normalize Decimal
        if isinstance(v, Decimal):
            if Decimal128:
                try:
                    doc[k] = Decimal128(str(v))
                except Exception:
                    doc[k] = float(v)
            else:
                doc[k] = float(v)
            continue

        # bytes / memoryview -> decode to string
        if isinstance(v, (bytes, bytearray, memoryview)):
            try:
                doc[k] = v.decode("utf-8")
            except Exception:
                doc[k] = str(bytes(v))
            continue

        # UUID -> string
        if isinstance(v, uuid.UUID):
            doc[k] = str(v)
            continue

        # basic types OK
        if isinstance(v, (str, int, float, bool, type(None))):
            doc[k] = v
            continue

        # fallback: convert to string to ensure JSON serializable for Mongo insert
        try:
            doc[k] = str(v)
        except Exception:
            doc[k] = None
    return doc

def _determine_upsert_key(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Prefer login_id_pk, then login_id, then login_id_fk
    for key in ("login_id_pk", "login_id", "login_id_fk"):
        if key in doc and doc.get(key) not in (None, ""):
            return {key: doc.get(key)}
    return None

def call_flexible_query_and_sync(
    table_name: str,
    columns: Optional[List[str]] = None,
    where_clause: Optional[str] = None,
    login_id_encrypted: Optional[str] = None,
    mongo_db_name: Optional[str] = None,
    mongo_collection: str = "login_table",
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> Dict[str, Any]:
    """
    Call usp_FlexibleQuery stored procedure and sync rows into MongoDB collection.
    
    Changes:
    - Password stored as plain "123"
    - No decryption logic for passwords
    - Old data removed if same email exists
    """
    db: Session = next(get_db())
    mongo_client = None
    try:
        # If encrypted login_id provided, decrypt and add to where_clause
        decrypted_login_id = None
        if login_id_encrypted:
            try:
                decrypted_login_id = int(decrypt_the_string(login_id_encrypted.strip()))
            except Exception as e:
                logger.error(f"Failed to decrypt login_id_encrypted: {e}")
                raise

            login_filter = f"login_id_fk = {decrypted_login_id}"
            if where_clause and str(where_clause).strip():
                where_clause = f"{login_filter} AND ({where_clause})"
            else:
                where_clause = login_filter

        params = {
            "p_table_name": table_name,
            "p_columns": "*",
            "p_where":"role='student'",
            "p_group_by": None,
            "p_order_by": None,
            "p_limit": int(limit) if limit is not None else None,
            "p_offset": int(offset) if offset is not None else None,
            "p_login_id_fk": None
        }

        connection = db.connection()
        logger.info(f"Running usp_FlexibleQuery with params: table={params['p_table_name']} columns={params['p_columns']} where={params['p_where']}")
        result = connection.execute(
            text("CALL usp_FlexibleQuery(:p_table_name, :p_columns, :p_where, :p_group_by, :p_order_by, :p_limit, :p_offset, :p_login_id_fk)"),
            params
        )
        rows = result.mappings().fetchall()
        db.commit()

        logger.info(f"Fetched {len(rows)} rows from DB for table {table_name}")

        # Connect to MongoDB
        mongo_client = _get_mongo_client()
        try:
            # quick ping to ensure connection and surface auth/network issues early
            mongo_client.admin.command("ping")
            logger.info("MongoDB ping successful")
        except Exception as ping_err:
            logger.error(f"MongoDB ping failed: {ping_err}")
            return {"status": False, "message": f"MongoDB connection failed: {str(ping_err)}"}

        db_name = mongo_db_name or os.getenv("MONGO_DB", MONGO_DB)
        mdb = mongo_client[db_name]
        coll = mdb[mongo_collection]

        docs = [_normalize_row(dict(r)) for r in rows] if rows else []

        if not docs:
            logger.info("No documents to sync to MongoDB")
            return {"status": True, "message": "No rows fetched", "rows_fetched": 0, "inserted": 0, "updated": 0}

        # Process each document
        inserted = 0
        updated = 0
        for doc in docs:
            try:
                # Build minimal mongo document: email + plain password
                email = doc.get("email") or doc.get("username")
                mongo_doc = {}
                if email:
                    # store both fields to ensure future deletes/matches work
                    mongo_doc["email"] = email
                    mongo_doc["username"] = email

                name_val = doc.get("name")

                # Read login_id_pk from the original row (try common keys)
                login_id_pk = doc.get("login_id_pk")
                for key_name in ("login_id_pk", "login_id", "login_id_fk", "loginId", "login_idPk"):
                    if key_name in doc and doc.get(key_name) not in (None, ""):
                        #login_id_pk = doc.get(key_name)
                        break

                # If name missing and we have login_id_pk -> call students SP with WHERE login_id_fk = <login_id_pk>
                if mongo_doc["email"] :
                    db2: Optional[Session] = None
                    try:
                        logger.info(f"Calling students lookup with login_id_fk='{login_id_pk}' (from first SP login_id_pk)")
                        db2 = next(get_db())
                        # Build concrete p_where string (no parameter placeholder)
                        p_where_students = _format_where_eq("login_id_fk", login_id_pk)
                        params_students = {
                            "p_table_name": "students",
                            "p_columns": "name",
                            "p_where": p_where_students,
                            "p_group_by": None,
                            "p_order_by": None,
                            "p_limit": 1,
                            "p_offset": 0,
                            "p_login_id_fk": None
                        }
                        conn2 = db2.connection()
                        res2 = conn2.execute(
                            text("CALL usp_FlexibleQuery(:p_table_name, :p_columns, :p_where, :p_group_by, :p_order_by, :p_limit, :p_offset, :p_login_id_fk)"),
                            params_students
                        )
                        rows_students = res2.mappings().fetchall()
                        db2.commit()
                        if rows_students:
                            fetched = dict(rows_students[0])
                            name_val = fetched.get("name") or fetched.get("Name")
                            logger.info(f"Students SP returned name='{name_val}' for login_id_fk='{login_id_pk}'")
                    except Exception as sp_err:
                        logger.error(f"Students lookup failed for login_id_fk='{login_id_pk}': {sp_err}")
                    finally:
                        try:
                            if db2:
                                db2.close()
                        except Exception:
                            pass
                
                # If still no name, derive from email local-part
                if not name_val and email:
                    try:
                        local = str(email).split("@", 1)[0]
                        name_val = local.replace(".", " ").replace("_", " ").replace("-", " ").title()
                    except Exception:
                        name_val = email

                # Store name in mongo document
                if name_val:
                    mongo_doc["name"] = name_val

                # Store password as name+123 (e.g., "john123", "mary123")
                if name_val:
                    # Clean name for password (remove spaces, special chars)
                    clean_name = "".join(c.lower() for c in str(name_val) if c.isalnum())
                    password_with_name = f"{clean_name}@{datetime.utcnow().year}"
                    mongo_doc["password_hash"] = password_with_name
                    logger.info(f"Set password as '{password_with_name}' for email={email}")
                else:
                    # Fallback if no name available
                    mongo_doc["password_hash"] = "user123"
                    logger.info(f"Set fallback password 'user123' for email={email}")

                # Add common_id as login_id_pk value
                if login_id_pk:
                    from helpers.helper import encrypt_the_string
                    mongo_doc["common_id"] = encrypt_the_string(str(login_id_pk))
                
                # Add timestamp
                mongo_doc["created_at"] = datetime.utcnow().isoformat()
                mongo_doc["updated_at"] = datetime.utcnow().isoformat()

                # Remove old data with same email, then insert new
                if email:
                    delete_filter = {"$or": [{"email": email}, {"username": email}]}
                    try:
                        del_res = coll.delete_many(delete_filter)
                        logger.info(f"Deleted {del_res.deleted_count} existing docs for email={email}")
                    except Exception as del_err:
                        logger.exception(f"Failed to delete existing docs for email={email}: {del_err}")
                    
                    # Insert new document
                    insert_result = coll.insert_one(mongo_doc)
                    logger.info(f"Inserted new doc for email={email} with id={insert_result.inserted_id}")
                    inserted += 1
                else:
                    # Fallback: use previous key logic (login_id_pk/login_id/login_id_fk)
                    key_filter = _determine_upsert_key(doc)
                    if key_filter:
                        try:
                            del_res = coll.delete_many(key_filter)
                            logger.info(f"Deleted {del_res.deleted_count} existing docs for key={key_filter}")
                        except Exception as del_err:
                            logger.exception(f"Failed to delete existing docs for key={key_filter}: {del_err}")
                        
                        insert_result = coll.insert_one(mongo_doc)
                        inserted += 1
                    else:
                        # No key available, insert as new document
                        insert_result = coll.insert_one(mongo_doc)
                        inserted += 1

            except Exception as single_err:
                logger.exception(f"Failed to process doc (email: {doc.get('email') or doc.get('username')}): {single_err}")
                # continue with other docs

        logger.info(f"Sync completed: fetched={len(docs)}, inserted={inserted}, updated={updated}")
        return {"status": True, "message": "Sync completed - passwords set to name+123 format", "rows_fetched": len(docs), "inserted": inserted, "updated": updated}

    except Exception as e:
        db.rollback()
        logger.exception(f"Sync failed: {e}")
        return {"status": False, "message": str(e)}
    finally:
        try:
            db.close()
        except:
            pass
        if mongo_client:
            mongo_client.close()

def insert_user_to_mongo(
    common_id: Optional[str],
    email: Optional[str] = None,
    password_hash: Optional[str] = None,
    name: Optional[str] = None,
    mongo_db_name: Optional[str] = None,
    mongo_collection: str = "login_table"
) -> Dict[str, Any]:
    """
    Insert or replace a user document in MongoDB.
    
    Changes:
    - Always uses "123" as password
    - No dynamic password generation
    - Removes old data for same email before inserting
    """
    mongo_client = None
    db: Session = None
    try:
        # Ensure common_id present (generate if missing)
        if not common_id or not str(common_id).strip():
            common_id = str(uuid.uuid4())

        # If name or email missing, try fetch both from DB using common_id as login_id_pk
        login_id_pk = None
        if (not name or not email) and common_id:
            try:
                db = next(get_db())
                params = {
                    "p_table_name": "logins",
                    "p_columns": "name,email,login_id_pk",
                    "p_where": "role='student'",
                    "p_group_by": None,
                    "p_order_by": None,
                    "p_limit": 1,
                    "p_offset": 0,
                    "p_login_id_fk": None
                }
                conn = db.connection()
                res = conn.execute(
                    text("CALL usp_FlexibleQuery(:p_table_name, :p_columns, :p_where, :p_group_by, :p_order_by, :p_limit, :p_offset, :p_login_id_fk)"),
                    {**params, "common_id": common_id}
                )
                rows = res.mappings().fetchall()
                db.commit()
                if rows:
                    fetched = dict(rows[0])
                    name = fetched.get("name") or name
                    email = fetched.get("email") or email
                    login_id_pk = fetched.get("login_id_pk") or common_id
                    logger.info(f"Fetched name='{name}', email='{email}', login_id_pk='{login_id_pk}' for common_id={common_id}")
            except Exception as sp_err:
                logger.error(f"Name/email fetch by common_id={common_id} failed: {sp_err}")
            finally:
                try:
                    if db:
                        db.close()
                except:
                    pass

        # If name missing, try to fetch from students table using login_id_fk = login_id_pk
        if not name and login_id_pk:
            try:
                db = next(get_db())
                params_students = {
                    "p_table_name": "students",
                    "p_columns": "name",
                    "p_where": "login_id_fk = :login_id_pk",
                    "p_group_by": None,
                    "p_order_by": None,
                    "p_limit": 1,
                    "p_offset": 0,
                    "p_login_id_fk": None
                }
                conn = db.connection()
                res = conn.execute(
                    text("CALL usp_FlexibleQuery(:p_table_name, :p_columns, :p_where, :p_group_by, :p_order_by, :p_limit, :p_offset, :p_login_id_fk)"),
                    {**params_students, "login_id_pk": login_id_pk}
                )
                rows = res.mappings().fetchall()
                db.commit()
                if rows:
                    fetched = dict(rows[0])
                    name = fetched.get("name") or fetched.get("Name")
                    logger.info(f"Fetched name='{name}' from students table for login_id_fk={login_id_pk}")
            except Exception as sp_err:
                logger.error(f"Failed to fetch student name for login_id_fk={login_id_pk}: {sp_err}")
            finally:
                try:
                    if db:
                        db.close()
                except:
                    pass

        # If still no email, create a fallback
        if not email or not str(email).strip():
            email = f"noemail_{common_id}@local"
            logger.info(f"Generated fallback email='{email}' for common_id={common_id}")

        # Create password as name+123 (e.g., "john123", "mary123")
        if name and str(name).strip():
            clean_name = "".join(c.lower() for c in str(name) if c.isalnum())
            password_hash = f"{clean_name}123"
        else:
            password_hash = "user123"

        # Build mongo document
        from helpers.helper import encrypt_the_string
        data = encrypt_the_string(common_id)
        mongo_doc: Dict[str, Any] = {
            "email": email,
            "username": email,  # Store both for consistency
            "password_hash": password_hash,
            "common_id": data,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        print(mongo_doc)
        if name:
            mongo_doc["name"] = name

        # Connect to Mongo
        mongo_client = _get_mongo_client()
        try:
            mongo_client.admin.command("ping")
        except Exception as ping_err:
            logger.error(f"MongoDB ping failed in insert_user_to_mongo: {ping_err}")
            return {"status": False, "message": f"MongoDB connection failed: {str(ping_err)}"}

        db_name = mongo_db_name or os.getenv("MONGO_DB", MONGO_DB)
        mdb = mongo_client[db_name]
        coll = mdb[mongo_collection]

        # Remove old data with same email first
        if email:
            delete_filter = {"$or": [{"email": email}, {"username": email}]}
            try:
                del_res = coll.delete_many(delete_filter)
                logger.info(f"Deleted {del_res.deleted_count} existing docs for email={email}")
            except Exception as del_err:
                logger.exception(f"Failed to delete existing docs for email={email}: {del_err}")

        # Insert new document
        try:
            insert_res = coll.insert_one(mongo_doc)
            result_id = str(insert_res.inserted_id)
            logger.info(f"Inserted new user doc for {email} with password '{password_hash}'")
        except Exception as mongo_err:
            logger.exception(f"Failed to insert user doc for {email}: {mongo_err}")
            return {"status": False, "message": str(mongo_err)}

        return {
            "status": True, 
            "message": f"User inserted with password '{password_hash}'", 
            "inserted_id": result_id,
            "password_used": password_hash
        }

    except Exception as e:
        logger.exception(f"insert_user_to_mongo failed: {e}")
        return {"status": False, "message": str(e)}
    finally:
        try:
            if db:
                db.close()
        except:
            pass
        if mongo_client:
            mongo_client.close()

# Example usage (uncomment to run from code):
# result = insert_user_to_mongo(
#     common_id="422a486c-726a-4261-92b9-fc91ea0c3b7d",
#     email="vish@gmail.com",
#     name="Vishal"
# )
# print(result)  # Will show password as '123'