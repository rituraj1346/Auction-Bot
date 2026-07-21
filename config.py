# config.py
import os

ACTIVE_SITES = ['mstc', 'metaljunction', 'ireps']
TWOCAPTCHA_API_KEY = ""

# --- IREPS CREDENTIALS ---
IREPS_MOBILE = ""

# --- MSTC SETTINGS ---
TARGET_LOCATIONS = [
    'Assam', 'Arunachal Pradesh', 'Meghalaya', 'Mizoram', 
    'Nagaland', 'Sikkim', 'Tripura', 'West Bengal'
]

# Workspace Directory Settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_downloads")
OUTPUT_SUMMARY_PATH = os.path.join(BASE_DIR, "Auction_Summary_Report.pdf")

# Meta WhatsApp Business API Credentials 
WA_PHONE_ID = ""
WA_BUSINESS_ID = ""
# Keep your actual long token here
WA_TOKEN = ""
WA_TEMPLATE = ""
WA_LANG = "en"
SEND_TO_NUMBER = "918"

# Google API Integration Configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/drive.file'
]
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
