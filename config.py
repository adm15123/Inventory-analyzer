import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = "your_secret_key"

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

EXCEL_FILENAME = "Final_Extracted_Data_Fixed_Logic4.xlsx"
DEFAULT_FILE = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)

SUPPLY2_FILENAME = "Supply2.xlsx"
DEFAULT_SUPPLY2_FILE = os.path.join(UPLOAD_FOLDER, SUPPLY2_FILENAME)

MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = "aliant.delgado07@gmail.com"
MAIL_PASSWORD = "lgco kmqe emqr qdrj"
MAIL_DEFAULT_SENDER = "aliant.delgado07@gmail.com"

SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

ALLOWED_EXTENSIONS = {"xlsx"}

ALLOWED_EMAILS = [
    "aliant.delgado@yahoo.com",
    "aliant.delgado17@gmail.com",
    "zamoraplumbing01@gmail.com",
    "aliant.delgado01@yahoo.com",
]

