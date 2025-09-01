import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

"""Application configuration and defaults.

This module previously accessed required environment variables using
``os.environ["VAR_NAME"]`` which raises a ``KeyError`` when the variable is
missing.  Deployments that do not define optional settings like
``SECRET_KEY`` or mail credentials would therefore crash at import time.

To make the application more robust – especially in development or
platforms where these variables are not provided – the configuration now
uses ``os.environ.get`` with sensible fallbacks.  This allows the app to
start with default values while still permitting overrides via
environment variables.
"""

# A default value is used if SECRET_KEY isn't specified so the app doesn't
# crash on start-up.  In production this should be overridden via an
# environment variable.
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")

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

SUPPLY4_FILENAME = "Bond_Bid_Extract.xlsx"
DEFAULT_SUPPLY4_FILE = os.path.join(UPLOAD_FOLDER, SUPPLY4_FILENAME)

MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() in ["true", "1", "t"]
# Mail credentials are optional; default to empty strings if not provided.
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

SESSION_PERMANENT = True
# Extend session lifetime to ensure long-term persistence.
PERMANENT_SESSION_LIFETIME = timedelta(days=365)

ALLOWED_EXTENSIONS = {"xlsx"}

# Sales tax rate applied to template totals
TAX_RATE = 0.07

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

