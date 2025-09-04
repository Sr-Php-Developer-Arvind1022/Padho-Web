from fastapi import FastAPI, Request, Body
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from apis.api import router as api_router
# from core.config import API_V1_STR, PROJECT_NAME
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

app = FastAPI()
origins = ["*"] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],              # 👈 List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],              # 👈 Allow all methods like GET, POST
    allow_headers=["*"],              # 👈 Allow all headers
)

app.include_router(api_router) 

@app.get("/")
def read_root():
    return {"message": "Student Management API is running."}

class LoginRequest(BaseModel):
    username: str
    password: str
def main():
    print("Student Management API is running.")
# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))  # Use Render's PORT or default to 10000 locally
    uvicorn.run(app, host="0.0.0.0", port=port)
