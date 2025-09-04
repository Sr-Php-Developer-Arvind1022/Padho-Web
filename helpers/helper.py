from fastapi import HTTPException, status
import bcrypt
import pyotp

import random
import string
import secrets
import os
from dotenv import load_dotenv
import smtplib
from cryptography.fernet import Fernet
from pydantic import EmailStr, BaseModel
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
# import aiosmtplib
from email.message import EmailMessage
# from logger import logger

# Load environment variables
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# # Hash a password
# def hash_password(plain_text_password):
#     salt = bcrypt.gensalt()  # Generate a salt
#     hashed_password = bcrypt.hashpw(plain_text_password.encode(), salt)
#     return hashed_password

import hashlib


FIXED_SALT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


# Function to Hash Password
def hash_password(password: str) -> str:

    hash_pass = hashlib.sha256((password + FIXED_SALT).encode()).hexdigest()
    # logger.info(
    #     f"convert the password in hashing pass : {password}, hash_password  : {hash_pass}"
    # )

    return hash_pass  # hashlib.sha256((password + FIXED_SALT).encode()).hexdigest()


# Verify a password
def check_password(plain_text_password, hashed_password):
    # logger.info(f"check the password hash password and plain password")
    return bcrypt.checkpw(plain_text_password.encode(), hashed_password.encode())





# Generate the secret key
def generate_secret(user):
    """Generate a secret key for a user and return a QR code URL."""
    secret = pyotp.random_base32()

    otp_auth_url = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user, issuer_name="DBMonitor"
    )

    return {"email": user, "secret": secret, "otp_auth_url": otp_auth_url}





# generate otp


def generate_otp():
    """Generate a random 6-digit OTP."""
    six_digit_otp = str(random.randint(100000, 999999))
    # logger.info(f"otp generate OTP : {six_digit_otp}")
    return six_digit_otp


# Function to send email with error handling
# async def send_email(to_email: str, subject: str, body: str):
#     message = EmailMessage()
#     message["From"] = SMTP_USERNAME
#     message["To"] = to_email
#     message["Subject"] = subject
#     message.set_content(body, subtype="html")


#     try:
#         await aiosmtplib.send(
#             message,
#             hostname=SMTP_SERVER,
#             port=SMTP_PORT,
#             username=SMTP_USERNAME,
#             password=SMTP_PASSWORD,
#             start_tls=True,
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to send email: {str(e)}",
#         )
def send_email(to_email: str, subject: str, body: str):

    message = EmailMessage()
    message["From"] = SMTP_USERNAME
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body, subtype="html")

    # logger.info(f"Send the mail, To email : {to_email}, Subject : {subject}")

    try:
        # Use smtplib for synchronous email sending
        # logger.info(f"{subject} : send mail successfully")

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(SMTP_USERNAME, SMTP_PASSWORD)  # Log in to the SMTP server
            server.send_message(message)  # Send the email
    except Exception as e:
        # logger.error(f"Failed to send email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}",
        )


def generate_string(length=35):
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return "".join(secrets.choice(characters) for _ in range(length))


KEY = os.getenv("ENCRYPTION_KEY")  # Get from environment variable
cipher = Fernet(KEY)


# Function to encrypt data
def encrypt_the_string(data: str):
    try:
        # Convert string to bytes and encrypt
        encrypted_data = cipher.encrypt(data.encode())
        # Return as string (base64 encoded)
        return encrypted_data.decode()
    except Exception as e:
        # logger.error(f"Encryption failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encryption failed: {str(e)}",
        )


# # Function to decrypt data
def decrypt_the_string(encrypted_data: str):

    try:
        # Convert string to bytes and decrypt
        decrypted_data = cipher.decrypt(encrypted_data.encode())
        # Return as string
        return decrypted_data.decode()
    except Exception as e:
        # logger.error(f"Decryption failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decryption failed: {str(e)}",
        )


def dba_decrypt_map(data):
    decrypted_data = []

    for entry in data:
        decrypted_entry = {}
        for key, value in entry.items():
            if (
                isinstance(value, str) and value.strip()
            ):  # Only decrypt non-empty strings
                try:
                    decrypted_entry[key] = decrypt_the_string(value)
                except Exception:
                    decrypted_entry[key] = value  # If decryption fails, keep original
            else:
                decrypted_entry[key] = (
                    value  # Non-string or empty values remain unchanged
                )
        decrypted_data.append(decrypted_entry)

    return decrypted_data



def group_job_values_by_jobid(job_values):
    grouped = {}

    for item in job_values:
        job_id = item["JobID"]

        if job_id not in grouped:
            # Parent structure initialize karo
            grouped[job_id] = {
                "Message": item.get("Message", ""),
                "Status": item.get("Status", ""),
                "JobID": item["JobID"],
                "GraphType": item.get("GraphType", ""),
                "XAxisName": item.get("XAxisName", ""),
                "YAxisName": item.get("YAxisName", ""),
                "GraphName": item.get("GraphName", ""),
                "JobDescription": item.get("JobDescription", ""),
                "values": []
            }

        executed_at = item["ExecutedAt"]

        if isinstance(executed_at, datetime):
            executed_time = executed_at.strftime("%H:%M")  # Extract time part only
        elif isinstance(executed_at, str):
            executed_time = datetime.strptime(executed_at, "%H:%M").time()
        else:
            executed_time = None
        # values ke andar data append karo
        grouped[job_id]["values"].append({
            "AutoRunID": item["AutoRunID"],
            # "ExecutedAt": item["ExecutedAt"],
            "ExecutedAt": executed_time,
            "QueryValue": item["QueryValue"]
        })

    # Dictionary ko list me convert karke return karo
    return list(grouped.values())
