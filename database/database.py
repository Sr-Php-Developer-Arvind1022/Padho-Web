from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

username = "sahilmon_padho"
password = quote_plus("padho@123") 
host = "176.9.144.171"
port = "3306"
dbname = "sahilmon_padho"


# print(password)
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{username}:{password}@{host}:{port}/{dbname}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# try:
#     engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
#     connection = engine.connect()
#     print("✅ Database connection successful!")
#     connection.close()
# except Exception as e:
#     print(f"❌ Database connection failed: {e}")


SessionLocal = sessionmaker(autocommit=False, autoflush=False,bind=engine)


def get_db():
    db = SessionLocal()
    try :
        yield db
    finally:
        db.close()
