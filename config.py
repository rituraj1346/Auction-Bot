# config.py
import os

ACTIVE_SITES = ['mstc', 'metaljunction', 'ireps']
TWOCAPTCHA_API_KEY = "7edb643dc2fc3fd3c31baeb38dbe30cc"

# --- IREPS CREDENTIALS ---
IREPS_MOBILE = "8812018662"

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
WA_PHONE_ID = "695194337013529"
WA_BUSINESS_ID = "695194337013529"
# Keep your actual long token here
WA_TOKEN = "EAAHPINsf7EcBPKiothSx8vR3Kbw5eOUwqxUD3g07A6evEZAoUAFN32cZC6EZAYQuem3QZA4HjmJSzw93VIMAiwbyk0kRKT75VK2qDFvPnUZBZBvEJP59n8wmobSNrpc4qsjl9a8M6ZA1mZBqKHzW91gqZC4FKz2vcMrXtZCjpylxxE9OYEk9ZCV2SolqAUw4rLkwkfRMAZDZD"
WA_TEMPLATE = "declartion"
WA_LANG = "en"
SEND_TO_NUMBER = "918761913078"

# Google API Integration Configuration
BASE_DIR = r"C:\AuctionBot"

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive'
]
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")