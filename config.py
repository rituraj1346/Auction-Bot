# config.py
import os

ACTIVE_SITES = ['mstc', 'metaljunction', 'ireps']
TWOCAPTCHA_API_KEY = "***REMOVED***"

# --- IREPS CREDENTIALS ---
IREPS_MOBILE = "***REMOVED***"

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
WA_PHONE_ID = "***REMOVED***"
WA_BUSINESS_ID = "***REMOVED***"
# Keep your actual long token here
WA_TOKEN = "***REMOVED***"
WA_TEMPLATE = "declartion"
WA_LANG = "en"
SEND_TO_NUMBER = "***REMOVED***"

# Google API Integration Configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/drive.file'
]
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")