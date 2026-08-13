# utils/calendar_sync.py
import os
import re
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import config

def get_google_services():
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
            
    cal_service = build("calendar", "v3", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    return cal_service, drive_service

def sync_to_calendar(auctions):
    print("Connecting to Google Calendar and Google Drive APIs...")
    try:
        cal_service, drive_service = get_google_services()
    except Exception as e:
        print(f"Google API authentication failed: {e}")
        return

    # ==========================================
    # 0. THE "MEMORY DRIVE" (DUPLICATE PREVENTION)
    # ==========================================
    print("Scanning calendar for existing events to prevent duplicates...")
    existing_events = set()
    try:
        # Grabs all events from the beginning of the year
        time_baseline = "2026-01-01T00:00:00Z"
        events_result = cal_service.events().list(
            calendarId='primary', 
            timeMin=time_baseline,
            maxResults=2500, 
            singleEvents=True,
            fields="items(summary)"
        ).execute()
        
        for ev in events_result.get('items', []):
            summary = ev.get('summary')
            if summary:
                existing_events.add(summary)
    except Exception as e:
        print(f"Warning: Could not fetch existing calendar events: {e}")

    # A "memory cache" so we don't ask Google to create the same folder 50 times
    folder_cache = {}

    # ==========================================
    # UPLOAD, SYNC, & CLEANUP LOOP
    # ==========================================
    for item in auctions:
        
        site_name = item.get('source', 'UNKNOWN').upper()
        full_title = item.get('title', 'Unknown Auction')
        expected_summary = f"[{site_name}] {full_title[:80]}"
        
        # --- FIXED: Duplicate Check Trigger ---
        if expected_summary in existing_events:
            print(f"⏭️ Skipping {expected_summary} (Already exists on calendar)")
            # Instantly delete the downloaded PDF so it doesn't clutter your hard drive
            if 'file_path' in item and os.path.exists(item['file_path']):
                try:
                    os.remove(item['file_path'])
                except:
                    pass
            continue # Move to the next auction without doing anything else
            
        # 1. DYNAMIC FOLDER ROUTING
        folder_name = f"{site_name} Auctions" 
        folder_id = None
        
        if folder_name not in folder_cache:
            try:
                # Check if this specific site's folder exists
                query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
                response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                folders = response.get('files', [])
                
                if folders:
                    folder_id = folders[0].get('id')
                else:
                    print(f"Creating new Drive folder for site: '{folder_name}'...")
                    folder_metadata = {
                        'name': folder_name,
                        'mimeType': 'application/vnd.google-apps.folder'
                    }
                    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                    folder_id = folder.get('id')
                    
                    # Make the new folder viewable
                    drive_service.permissions().create(
                        fileId=folder_id,
                        body={'type': 'anyone', 'role': 'reader'}
                    ).execute()
                
                # Save it to memory so the next PDF goes super fast
                folder_cache[folder_name] = folder_id
            except Exception as e:
                print(f"Folder routing failed for {folder_name}: {e}")
        else:
            folder_id = folder_cache[folder_name]

        # 2. UPLOAD TO THE SPECIFIC FOLDER
        drive_link = "No document attached"
        if 'file_path' in item and os.path.exists(item['file_path']):
            try:
                print(f"Uploading PDF to '{folder_name}'...")
                
                file_metadata = {
                    'name': f"[{site_name}] {item.get('title', 'Auction_PDF')}.pdf",
                    'parents': [folder_id] if folder_id else []
                }
                
                media = MediaFileUpload(item['file_path'], mimetype='application/pdf', resumable=False)
                drive_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
                drive_link = drive_file.get('webViewLink')
                
                item['pdf_link'] = drive_link
                
                # Instantly delete local file to save space
                try:
                    os.remove(item['file_path'])
                except Exception as e:
                    pass
                    
            except Exception as e:
                print(f"Failed to upload PDF to Drive: {e}")

        # ==========================================
        # 3. UNIFIED CALENDAR DATE ENGINE
        # ==========================================
        start_iso = "2026-07-20T12:00:00+05:30"
        end_iso = "2026-07-20T17:00:00+05:30"
        
        try:
            date_text = item.get('date', '').replace('/', '-').strip()
            parsed_dt = None
            
            # MULTI-FORMAT DICTIONARY
            date_formats = [
                "%Y-%m-%d %H:%M:%S", # MetalJunction (e.g., 2026-07-15 14:00:00)
                "%d-%m-%Y %H:%M:%S", # Alternative with seconds
                "%d-%m-%y %H:%M:%S", # IREPS ADDED (e.g., 29-08-26 10:30:00)
                "%d-%m-%Y %H:%M",    # MSTC 4-digit year (e.g., 15-07-2026 14:00)
                "%d-%m-%y %H:%M",    # MSTC 2-digit year (e.g., 15-07-26 14:00)
                "%Y-%m-%d %H:%M"     # MetalJunction without seconds
            ]
            
            for fmt in date_formats:
                try:
                    parsed_dt = datetime.strptime(date_text, fmt)
                    break 
                except ValueError:
                    continue
                    
            if not parsed_dt:
                match = re.search(r'\b(\d{2})-(\d{2})-(\d{2,4})\s+(\d{2}:\d{2})\b', date_text)
                if match:
                    d, m, y, t = match.groups()
                    if len(y) == 2:
                        parsed_dt = datetime.strptime(f"{d}-{m}-{y} {t}", "%d-%m-%y %H:%M")
                    else:
                        parsed_dt = datetime.strptime(f"{d}-{m}-{y} {t}", "%d-%m-%Y %H:%M")
                        
            # APPLY VERIFIED DATE TO EVENT PAYLOAD
            if parsed_dt:
                parsed_dt = parsed_dt.replace(year=2026) 
                start_iso = parsed_dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")
                end_iso = parsed_dt.replace(hour=min(parsed_dt.hour + 4, 23)).strftime("%Y-%m-%dT%H:%M:%S+05:30")
                
        except Exception as e:
            print(f"Calendar Routing Note: Using default fallback date because -> {e}")
            pass
            
        category = item.get('category', 'General Scrap')
        auction_time = item.get('date', 'Time not specified')
        location_text = item.get('location', 'State not listed')
        materials = item.get('materials', 'See details')
        emd_terms = item.get('paperwork', 'Check terms')
        
        description_body = (
            f"📌 FULL AUCTION ID:\n{full_title}\n\n"
            f"🏷️ CATEGORY:\n{category}\n\n"
            f"📍 LOT STATE:\n{location_text}\n\n"
            f"⏰ SCHEDULED DATE & TIME:\n{auction_time}\n\n"
            f"📦 EXACT LOT DESCRIPTIONS:\n{materials}\n\n"
            f"📑 EMD & PAPERWORK:\n{emd_terms}\n\n"
            f"🔗 SECURE PDF LINK:\n{drive_link}"
        )

        # ==========================================
        # 4. SMART HIGHLIGHT & COLOR CODING
        # ==========================================
        pin_color = '9' # Default to Blueberry (Blue) for MSTC
        reminder_mins = 60 # Default to 1-hour reminder
        
        if site_name == 'METALJUNCTION':
            pin_color = '6' # Default to Tangerine (Orange) for MetalJunction
        elif site_name == 'IREPS':
            pin_color = '10' # Default to Tomato (Red) for IREPS
            reminder_mins = 1440 # 24-hour reminder to download catalogue
            
        cat_lower = category.lower()
        mat_lower = materials.lower()
        
        # Override color with TOMATO (Bright Red) if the auction is Iron & Steel
        if 'iron and steel' in cat_lower or 'iron & steel' in cat_lower or 'iron & metal' in cat_lower or 'iron' in mat_lower:
            pin_color = '11' 

        event = {
            'summary': expected_summary, 
            'location': location_text[:100], 
            'description': description_body, 
            'colorId': pin_color,  
            'start': {'dateTime': start_iso, 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_iso, 'timeZone': 'Asia/Kolkata'},
            'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': reminder_mins}]}
        }
        
        try:
            cal_service.events().insert(calendarId='primary', body=event).execute()
            print(f"Successfully pinned event: {expected_summary[:35]}... (Color: {pin_color})")
        except Exception as e:
            print(f"Failed to insert slot: {e}")