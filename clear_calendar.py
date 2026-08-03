# clear_calendar.py
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import config

def get_calendar_service():
    creds = None
    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.CREDENTIALS_FILE, config.SCOPES)
            creds = flow.run_local_server(port=0)
        with open(config.TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

def clear_bot_events():
    # -----------------------------------------------------------------
    # 1. INTERACTIVE TARGET SELECTION
    # -----------------------------------------------------------------
    print("====================================================")
    print("             CALENDAR CLEANUP UTILITY               ")
    print("====================================================")
    print("Select the target site you want to clear:")
    print("1. IREPS Only")
    print("2. MSTC Only")
    print("3. MetalJunction Only")
    print("4. Clear ALL Sites")
    print("5. Cancel Operations")
    print("----------------------------------------------------")
    
    choice = input("Enter your selection (1-5): ").strip()
    
    # Switched from strict prefixes to flexible keywords
    if choice == '1':
        target_keywords = ["IREPS"]
        target_label = "IREPS"
    elif choice == '2':
        target_keywords = ["MSTC"]
        target_label = "MSTC"
    elif choice == '3':
        target_keywords = ["METALJUNCTION", "[MJ]"]
        target_label = "MetalJunction"
    elif choice == '4':
        target_keywords = ["IREPS", "MSTC", "METALJUNCTION", "[MJ]"]
        target_label = "ALL sites"
    elif choice == '5':
        print("Operation cancelled by user.")
        return
    else:
        print("❌ Invalid selection. Aborting.")
        return

    # -----------------------------------------------------------------
    # 2. CALENDAR AUTHENTICATION
    # -----------------------------------------------------------------
    print(f"\nConnecting to Google Calendar to clean up {target_label} entries...")
    try:
        service = get_calendar_service()
    except Exception as e:
        print(f"Calendar authentication failed: {e}")
        return

    time_baseline = "2026-01-01T00:00:00Z"
    print("Scanning calendar for upcoming scraper slots...")
    
    try:
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=time_baseline,
            maxResults=500, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
    except Exception as e:
        print(f"Failed to fetch calendar events: {e}")
        return

    if not events:
        print("Your calendar is already clear of upcoming events.")
        return

    # -----------------------------------------------------------------
    # 3. FLEXIBLE KEYWORD PURGING PIPELINE
    # -----------------------------------------------------------------
    deleted_count = 0
    print(f"Searching for keywords: {target_keywords}...")
    
    for event in events:
        summary = event.get('summary', '')
        summary_upper = summary.upper() # Convert title to uppercase for easy matching
        
        # If ANY of our target keywords exist anywhere in the title, delete it
        if any(keyword in summary_upper for keyword in target_keywords):
            event_id = event['id']
            try:
                service.events().delete(calendarId='primary', eventId=event_id).execute()
                print(f"🗑️ Removed: {summary[:50]}...")
                deleted_count += 1
            except Exception as e:
                print(f"Could not remove event {summary[:30]}: {e}")

    print(f"\nCleanup finished! Total {target_label} slots cleared: {deleted_count}")

if __name__ == "__main__":
    clear_bot_events()