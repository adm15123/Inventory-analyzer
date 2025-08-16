import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TEMPLATE_DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(TEMPLATE_DATA_DIR, exist_ok=True)

EXCEL_FILENAME = "Final_Extracted_Data_Fixed_Logic4.xlsx"
DEFAULT_FILE = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)

SUPPLY2_FILENAME = "Supply2.xlsx"
DEFAULT_SUPPLY2_FILE = os.path.join(UPLOAD_FOLDER, SUPPLY2_FILENAME)

SUPPLY3_FILENAME = "Lion_Bid_Extract.xlsx"
DEFAULT_SUPPLY3_FILE = os.path.join(UPLOAD_FOLDER, SUPPLY3_FILENAME)

MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() in ["true", "1", "t"]
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "aliant.delgado07@gmail.com")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "lgco kmqe emqr qdrj")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

ALLOWED_EXTENSIONS = {"xlsx"}

ALLOWED_EMAILS = [
    "aliant.delgado@yahoo.com",
    "aliant.delgado17@gmail.com",
    "zamoraplumbing01@gmail.com",
    "aliant.delgado01@yahoo.com",
]

# GitHub API configuration for saving templates
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "username/repo")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

