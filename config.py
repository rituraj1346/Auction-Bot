import os
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# SECRETS LOADED FROM .env
# ==============================================================================
TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY")
IREPS_MOBILE = os.getenv("IREPS_MOBILE")
WA_PHONE_ID = os.getenv("WA_PHONE_ID")
WA_BUSINESS_ID = os.getenv("WA_BUSINESS_ID")
WA_TOKEN = os.getenv("WA_TOKEN")
SEND_TO_NUMBER = os.getenv("SEND_TO_NUMBER")

# ==============================================================================
# STANDARD CONFIGURATION
# ==============================================================================
ACTIVE_SITES = ['mstc', 'metaljunction', 'ireps']

TARGET_LOCATIONS = [
    'Assam', 'Arunachal Pradesh', 'Meghalaya', 'Mizoram', 
    'Nagaland', 'Sikkim', 'Tripura', 'West Bengal'
]

WA_TEMPLATE = "declartion"
WA_LANG = "en"

# ==============================================================================
# SYSTEM PATHS & DIRECTORIES
# ==============================================================================
BASE_DIR = r"C:\AuctionBot"
DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_downloads")
OUTPUT_SUMMARY_PATH = os.path.join(BASE_DIR, "Auction_Summary_Report.pdf")

# ==============================================================================
# GOOGLE API INTEGRATION
# ==============================================================================
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive'
]
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")