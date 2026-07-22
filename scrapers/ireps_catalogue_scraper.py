# scrapers/ireps_catalogue_scraper.py
import os
import glob
import time
import re
import base64
import requests
from datetime import datetime, timedelta

# Google API Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.modify'
]

def get_google_credentials():
    """Centralized credential loader for all Google APIs."""
    creds = None
    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(config.TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def fetch_ireps_otp(creds, retries=15):
    """Uses the Gmail API to grab today's NEWEST OTP."""
    service = build('gmail', 'v1', credentials=creds)

    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    start_of_today_ist = datetime(now_ist.year, now_ist.month, now_ist.day)
    start_of_today_utc = start_of_today_ist - timedelta(hours=5, minutes=30)
    start_of_today_ms = int(start_of_today_utc.timestamp() * 1000)

    def extract_body(payload):
        text = ""
        if 'parts' in payload:
            for part in payload['parts']:
                text += extract_body(part)
        elif 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            data += "=" * ((4 - len(data) % 4) % 4)
            text += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore') + " "
        return text

    for attempt in range(retries):
        try:
            results = service.users().messages().list(
                userId='me', q='from:jitumission@gmail.com "OTP"', maxResults=10
            ).execute()
            messages = results.get('messages', [])

            for msg in messages:
                message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                internal_date = int(message['internalDate'])
                
                if internal_date >= start_of_today_ms:
                    raw_body = message.get('snippet', '') + " " + extract_body(message.get('payload', {}))
                    clean_body = re.sub(r'<[^>]+>', ' ', raw_body)
                    clean_body = re.sub(r'\s+', ' ', clean_body).strip()
                    
                    match = re.search(r'(\d{6})\s*is the OTP', clean_body, re.IGNORECASE)
                    if match:
                        return match.group(1)
        except Exception as e:
            print(f"Gmail API lookup warning: {e}")

        if retries > 1:
            print(f"Waiting for NEW OTP email... (Attempt {attempt+1}/{retries})")
            time.sleep(5)
    return None

def check_if_calendar_event_exists(creds, schedule_no):
    """Verifies if the Schedule No is actually in the calendar before downloading."""
    cal_service = build('calendar', 'v3', credentials=creds)
    now = datetime.utcnow().isoformat() + 'Z'
    try:
        events_result = cal_service.events().list(
            calendarId='primary', timeMin=now, q=schedule_no, singleEvents=True
        ).execute()
        return len(events_result.get('items', [])) > 0
    except Exception as e:
        print(f"Calendar pre-check failed: {e}")
        return False

def wait_for_download_and_rename(download_dir, schedule_no, timeout=35):
    """Monitors disk for the file and renames it to the Schedule No."""
    print(f"Waiting for local disk synchronization for Schedule: {schedule_no}...")
    end_time = time.time() + timeout
    
    while time.time() < end_time:
        files = glob.glob(os.path.join(download_dir, '*'))
        active_files = [f for f in files if not os.path.basename(f).startswith(schedule_no)]
        
        if active_files:
            latest_file = max(active_files, key=os.path.getctime)
            if not latest_file.endswith('.crdownload') and not latest_file.endswith('.tmp'):
                file_extension = os.path.splitext(latest_file)[1] or ".htm"
                new_file_path = os.path.join(download_dir, f"{schedule_no}{file_extension}")
                
                try:
                    if os.path.exists(new_file_path):
                        os.remove(new_file_path)
                    os.rename(latest_file, new_file_path)
                    print(f"✅ Download Verified & Renamed: {schedule_no}{file_extension}")
                    return new_file_path
                except Exception as rename_err:
                    print(f"File lock collision, retrying rename: {rename_err}")
        time.sleep(1.5)
    
    print(f"⚠ Timeout: No new document tracked for Schedule {schedule_no}")
    return None

def upload_and_link_to_calendar(creds, local_file_path, schedule_no):
    """Uploads file to Google Drive and injects the URL into the matching Calendar Event."""
    drive_service = build('drive', 'v3', credentials=creds)
    cal_service = build('calendar', 'v3', credentials=creds)
    
    file_ext = os.path.splitext(local_file_path)[1].lower()
    mimetype = 'application/pdf' if file_ext == '.pdf' else 'text/html'
    file_name = os.path.basename(local_file_path)
    
    print(f"Uploading {file_name} to Google Drive...")
    try:
        media = MediaFileUpload(local_file_path, mimetype=mimetype)
        file_metadata = {'name': file_name}
        
        uploaded_file = drive_service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink'
        ).execute()
        
        file_id = uploaded_file.get('id')
        drive_link = uploaded_file.get('webViewLink')
        
        drive_service.permissions().create(
            fileId=file_id, body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        print("☁ File secured in Google Drive.")
        
    except Exception as e:
        print(f"❌ Failed to upload to Drive: {e}")
        return

    try:
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = cal_service.events().list(
            calendarId='primary', timeMin=now, q=schedule_no, singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
            
        for event in events:
            old_desc = event.get('description', '')
            if "Catalogue Link:" not in old_desc:
                new_desc = f"{old_desc}\n\n<br><br><b>Catalogue Link:</b> <a href='{drive_link}'>View Document</a>"
                event['description'] = new_desc
                cal_service.events().update(
                    calendarId='primary', eventId=event['id'], body=event
                ).execute()
                print(f"🔗 Success! Linked Drive document to event: {event.get('summary')}")
            else:
                print(f"Event '{event.get('summary')}' already has a catalogue attached.")
                
    except Exception as e:
        print(f"❌ Failed to update Google Calendar: {e}")

def run_catalogues_downloader():
    """Main execution block called by the external runner script."""
    creds = get_google_credentials()
    
    if not os.path.exists(config.DOWNLOAD_DIR):
        os.makedirs(config.DOWNLOAD_DIR)

    options = webdriver.ChromeOptions()

    # --- SMART HEADLESS TOGGLE ---
    # Runs invisible by default. Shows UI only if '--visible' is typed in the terminal.
    import sys
    if "--visible" not in sys.argv:
        print("🖥️ Running in Server Mode (Invisible Chrome)")
        options.add_argument("--headless=new") 
        options.add_argument("--no-sandbox") 
        options.add_argument("--disable-dev-shm-usage")
    else:
        print("👀 Running in Manual Test Mode (Visible Chrome)")

    # Keep your existing prefs below this...
    options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(config.DOWNLOAD_DIR),
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_setting_values.automatic_downloads": 1
    })
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        for master_attempt in range(3):
            print(f"\n[Master Pipeline Sequence - Attempt {master_attempt + 1} of 3]")
            
            try:
                if master_attempt == 0:
                    driver.get("https://ireps.gov.in/")
                    time.sleep(3)
                
                driver.refresh()
                time.sleep(4)
                
                try:
                    close_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close') or translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='close']"
                    close_btns = driver.find_elements(By.XPATH, close_xpath)
                    for btn in close_btns:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                            break
                except: pass

                auction_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search e-auction sale')]")))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", auction_btn)
                driver.execute_script("arguments[0].removeAttribute('target');", auction_btn)
                driver.execute_script("window.open = function(url){ window.location.href = url; return window; };")
                driver.execute_script("arguments[0].click();", auction_btn)
                time.sleep(5)
                    
                mobile_xpath = "//input[contains(@name, 'mobile') or contains(@id, 'mobile')]"
                mobile_input = wait.until(EC.presence_of_element_located((By.XPATH, mobile_xpath)))
                mobile_input.clear()
                mobile_input.send_keys(config.IREPS_MOBILE)
                time.sleep(2)

                captcha_solved = False
                retrieved_otp = None
                
                for captcha_attempt in range(4):
                    try:
                        captcha_xpath = "//img[contains(translate(@src, 'ABCDEF', 'abcdef'), 'captcha')] | //img[contains(translate(@id, 'ABCDEF', 'abcdef'), 'captcha')] | //*[contains(text(), 'Verification Code')]/following::img[1]"
                        captcha_img = wait.until(EC.presence_of_element_located((By.XPATH, captcha_xpath)))
                        
                        js_canvas_rip = """
                            var img = arguments[0];
                            var canvas = document.createElement('canvas');
                            canvas.width = img.naturalWidth || img.width;
                            canvas.height = img.naturalHeight || img.height;
                            var ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0);
                            return canvas.toDataURL('image/png');
                        """
                        img_base64 = driver.execute_script(js_canvas_rip, captcha_img).split(',')[1]
                        
                        payload = {'key': config.TWOCAPTCHA_API_KEY, 'method': 'base64', 'body': img_base64, 'json': 1}
                        response = requests.post('http://2captcha.com/in.php', data=payload).json()
                        
                        if response.get('status') != 1: raise Exception("2Captcha Rejection")
                        request_id = response.get('request')
                        
                        captcha_answer = None
                        for _ in range(25):
                            time.sleep(5)
                            res = requests.get(f"http://2captcha.com/res.php?key={config.TWOCAPTCHA_API_KEY}&action=get&id={request_id}&json=1").json()
                            if res.get('status') == 1:
                                captcha_answer = res.get('request')
                                break
                        
                        if not captcha_answer: raise Exception("Captcha Solved Timeout")
                        
                        captcha_input = driver.find_element(By.XPATH, "//input[contains(@name, 'captcha') or contains(@placeholder, 'Code')]")
                        captcha_input.clear()
                        captcha_input.send_keys(captcha_answer)
                        time.sleep(2)
                        
                        try: driver.execute_script("sendOTP();")
                        except: driver.find_element(By.XPATH, "//input[@value='Get OTP']").click()
                        
                        time.sleep(6)
                        
                        # --- NEW: Smart OTP Alert Handler (No Pause) ---
                        try:
                            alert = driver.switch_to.alert
                            alert_text = alert.text
                            alert.accept()
                            
                            if "maximum" in alert_text.lower() or "limit" in alert_text.lower():
                                print(f"ℹ️ Intercepted: '{alert_text}'.")
                                print("Proceeding to login using the existing valid OTP from Gmail...")
                                # We do NOTHING here. The code will naturally drop down to fetch_ireps_otp.
                                
                            elif any(x in alert_text.lower() for x in ["invalid", "wrong", "match"]):
                                print(f"⚠️ Intercepted Captcha Error: '{alert_text}'. Retrying...")
                                driver.find_element(By.XPATH, "//*[contains(@onclick, 'captcha') or contains(@class, 'refresh')]").click()
                                time.sleep(3)
                                continue
                        except: 
                            pass # No alert present, move on safely
                        # -----------------------------------------------
                        
                        retrieved_otp = fetch_ireps_otp(creds, retries=15)
                        captcha_solved = True
                        break
                    except Exception as e:
                        print(f"Captcha verification cycle noise: {e}")
                        time.sleep(3)

                if not captcha_solved or not retrieved_otp:
                    print("Gatekeeper authentication timeout. Resetting context...")
                    continue

                otp_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter OTP' or contains(@placeholder, 'OTP')]")))
                otp_input.clear()
                otp_input.send_keys(retrieved_otp)
                time.sleep(2)
                
                proceed_btn = driver.find_element(By.ID, "proceedButton")
                driver.execute_script("arguments[0].click();", proceed_btn)
                time.sleep(5)
                
                try: driver.switch_to.alert.accept()
                except: pass
                
                if "404 Page not found" in driver.page_source:
                    print("🚨 Session Drop Intercepted. Reloading...")
                    driver.get("https://ireps.gov.in/")
                    time.sleep(4)
                    continue
                
                print("🔒 Secure Login Session Authenticated.")
                
                print("Navigating to Forthcoming Auction Matrix...")
                forthcoming_tab = wait.until(EC.presence_of_element_located((By.ID, "forthcomingAuction")))
                driver.execute_script("arguments[0].click();", forthcoming_tab)
                time.sleep(5)
                
              # --- REMOVED SEARCH BOX INJECTION ---
                
                print("Expanding table to show 100 entries so Python can scan everything...")
                try:
                    from selenium.webdriver.support.ui import Select # Added this import to prevent a NameError!
                    entries_select = Select(driver.find_element(By.XPATH, "//select[contains(@name, 'length')]"))
                    entries_select.select_by_visible_text("100")
                    time.sleep(3)
                except Exception as e: 
                    print(f"Warning: Could not change dropdown to 100. {e}")
                
                grid_rows = driver.find_elements(By.XPATH, "//table[contains(@class, 'dataTable') or contains(@id, 'table')]/tbody/tr")
                total_records = len(grid_rows)
                print(f"Scanning all {total_records} upcoming catalogues on the page for 'N F RLY'...")
                
                for idx in range(total_records):
                    # --- NEW: Force table back to 100 entries after navigating back! ---
                    try:
                        from selenium.webdriver.support.ui import Select
                        entries_select = Select(driver.find_element(By.XPATH, "//select[contains(@name, 'length')]"))
                        # If the dropdown reset to 10 after pressing 'back', fix it:
                        if entries_select.first_selected_option.text != "100":
                            print("Restoring table view to 100 entries...")
                            entries_select.select_by_visible_text("100")
                            time.sleep(3)
                    except: pass
                    # -------------------------------------------------------------------
                    
                    # Re-fetch rows inside the loop to avoid StaleElementReferenceException
                    current_snapshot_rows = driver.find_elements(By.XPATH, "//table[contains(@class, 'dataTable') or contains(@id, 'table')]/tbody/tr")
                    
                    if idx >= len(current_snapshot_rows): 
                        print(f"End of visible table reached at row {idx}. Breaking loop.")
                        break
                    
                    row_cols = current_snapshot_rows[idx].find_elements(By.TAG_NAME, "td")
                    if len(row_cols) < 5: continue
                    
                    # --- THE PYTHON FILTER ---
                    # Check column 0 (Railway.) for the text "N F RLY"
                    railway_name = row_cols[0].text.strip()
                    
                    if "N F RLY" not in railway_name:
                        # If it is NOT N F RLY, skip to the next row silently
                        continue 
                        
                    schedule_no = row_cols[2].text.strip()
                    catalogue_text = row_cols[3].text.strip()
                    
                    print(f"\n✅ Found N F RLY Match! Processing Row [{idx+1}/{total_records}] | Schedule ID: {schedule_no} | Catalogue: {catalogue_text}")
                    
                
                    # --- NEW: The Pre-Check Logic ---
                    if not check_if_calendar_event_exists(creds, schedule_no):
                        print(f"⏩ Schedule {schedule_no} not found in Calendar. Skipping as this is a non-target auction.")
                        continue
                    
                    try:
                        # ALL of these lines must have the exact same starting column
                        catalogue_link = row_cols[3].find_element(By.TAG_NAME, "a")
                        driver.execute_script("arguments[0].click();", catalogue_link)
                        time.sleep(4)
                        
                        print_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Save / Print Catalogue']")))
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", print_btn)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", print_btn)
                        time.sleep(4)
                        
                        # --- NEW: Python Native Save (Bypasses broken JS button) ---
                        print("Bypassing legacy JS save button. Writing HTML directly to disk...")
                        
                        html_content = driver.page_source
                        final_file_path = os.path.join(config.DOWNLOAD_DIR, f"{schedule_no}.htm")
                        
                        with open(final_file_path, "w", encoding="utf-8") as f:
                            f.write(html_content)
                            
                        print(f"✅ Saved safely by Python: {schedule_no}.htm")
                        # -----------------------------------------------------------
                        
                        if final_file_path:
                            upload_and_link_to_calendar(creds, final_file_path, schedule_no)
                            
                        print("Re-anchoring back onto dashboard interface...")
                        driver.back()
                        time.sleep(2)
                        driver.back()
                        time.sleep(4)
                        
                    except Exception as inner_row_error:
                        print(f"Skipping row execution fault on {schedule_no}: {inner_row_error}")
                        driver.get("https://ireps.gov.in/eps/admin/AnnonumousAction.do")
                        time.sleep(4)
                        forthcoming_tab = wait.until(EC.presence_of_element_located((By.ID, "forthcomingAuction")))
                        driver.execute_script("arguments[0].click();", forthcoming_tab)
                        time.sleep(3)
                
                print("\n====================================================")
                print("         CATALOGUE PURGE CYCLE CONCLUDED            ")
                print("====================================================")
                break
                
            except Exception as loop_fault:
                print(f"Exception sequence fault trapped in runtime loop: {loop_fault}")
                time.sleep(5)
                
    finally:
        driver.quit()