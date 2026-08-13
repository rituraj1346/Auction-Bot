# scrapers/ireps_scraper.py
import os
import os.path
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

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

import config

# Combined scopes for Calendar, Drive, and Gmail
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.modify'
]

def fetch_ireps_otp(retries=15):
    """Uses the Gmail API to grab today's NEWEST OTP."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

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
                userId='me', 
                q='from:jitumission@gmail.com "OTP"', 
                maxResults=10
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

def run_scraper():
    print("Launching Precision IREPS Engine (Auto-Restart on 404 Enabled)...")
    extracted_records = []
    
    if not os.path.exists(config.DOWNLOAD_DIR):
        os.makedirs(config.DOWNLOAD_DIR)
    for old_file in glob.glob(os.path.join(config.DOWNLOAD_DIR, "*")):
        try: os.remove(old_file)
        except: pass

    options = webdriver.ChromeOptions()

    # --- SMART HEADLESS TOGGLE ---
    # Runs invisible by default. Shows UI only if '--visible' is typed in the terminal.
    import sys
    if "--visible" not in sys.argv:
       print("[SERVER] Running in Server Mode (Invisible Chrome)")
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
        # --- MASTER RETRY LOOP ---
        for master_attempt in range(3):
            print(f"\n====================================================")
            print(f"      STARTING PIPELINE - ATTEMPT {master_attempt + 1} OF 3      ")
            print(f"====================================================")
            
            try:
                # ==========================================
                # 1. NAVIGATION & INITIALIZATION
                # ==========================================
                if master_attempt == 0:
                    print("Navigating to IREPS Homepage...")
                    driver.get("https://ireps.gov.in/")
                    time.sleep(3)
                
                print("Refreshing the homepage to secure a clean Java session cookie...")
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

                print("Locating 'Search E-Auction Sale' button...")
                auction_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search e-auction sale')]")))
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", auction_btn)
                time.sleep(1)
                
                print("Modifying DOM to prevent cross-tab session loss...")
                driver.execute_script("arguments[0].removeAttribute('target');", auction_btn)
                driver.execute_script("window.open = function(url){ window.location.href = url; return window; };")
                
                print("Clicking auction button (loading in same tab)...")
                driver.execute_script("arguments[0].click();", auction_btn)
                time.sleep(5)
                    
                # ==========================================
                # 2. MOBILE & CAPTCHA INJECTION
                # ==========================================
                print("Injecting Registered Mobile Number...")
                mobile_xpath = "//input[contains(@name, 'mobile') or contains(@id, 'mobile')]"
                mobile_input = wait.until(EC.presence_of_element_located((By.XPATH, mobile_xpath)))
                mobile_input.clear()
                mobile_input.send_keys(config.IREPS_MOBILE)
                time.sleep(2)

                captcha_solved = False
                for captcha_attempt in range(4):
                    try:
                        captcha_xpath = (
                            "//img[contains(translate(@src, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'captcha')] | "
                            "//img[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'captcha')] | "
                            "//*[contains(text(), 'Verification Code')]/following::img[1] | "
                            "//img[ancestor::tr[contains(., 'Verification Code')]]"
                        )
                        captcha_img = wait.until(EC.presence_of_element_located((By.XPATH, captcha_xpath)))
                        
                        print(f"CAPTCHA isolated (Attempt {captcha_attempt + 1}). Ripping pixel data...")
                        js_canvas_rip = """
                            var img = arguments[0];
                            var canvas = document.createElement('canvas');
                            canvas.width = img.naturalWidth || img.width || 160;
                            canvas.height = img.naturalHeight || img.height || 60;
                            var ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0);
                            return canvas.toDataURL('image/png');
                        """
                        raw_data_url = driver.execute_script(js_canvas_rip, captcha_img)
                        img_base64 = raw_data_url.split(',')[1] 
                        
                        payload = {
                            'key': config.TWOCAPTCHA_API_KEY,
                            'method': 'base64',
                            'body': img_base64,
                            'json': 1
                        }
                        response = requests.post('http://2captcha.com/in.php', data=payload).json()
                        
                        if response.get('status') != 1: raise Exception("2Captcha rejected payload.")
                        request_id = response.get('request')
                        
                        captcha_answer = None
                        for _ in range(25): 
                            time.sleep(5)
                            res = requests.get(f"http://2captcha.com/res.php?key={config.TWOCAPTCHA_API_KEY}&action=get&id={request_id}&json=1").json()
                            if res.get('status') == 1:
                                captcha_answer = res.get('request')
                                break
                            elif res.get('request') != 'CAPCHA_NOT_READY':
                                raise Exception("Solver failure.")
                        
                        if not captcha_answer: raise Exception("2Captcha timeout.")
                        print(f"Success! CAPTCHA Solved: '{captcha_answer}'")
                        
                        captcha_input_xpath = "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verification code') or contains(@name, 'captcha')]"
                        captcha_input = driver.find_element(By.XPATH, captcha_input_xpath)
                        captcha_input.clear()
                        captcha_input.send_keys(captcha_answer)
                        time.sleep(2) 
                        
                        print("Clicking 'Get OTP' (Executing native sendOTP() function)...")
                        get_otp_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='imageField' and @value='Get OTP']")))
                        try:
                            driver.execute_script("sendOTP();")
                        except:
                            driver.execute_script("arguments[0].click();", get_otp_btn)
                        
                        print("Waiting 6 seconds for the server to process and dispatch the email...")
                        time.sleep(6)
                        
                        limit_reached = False
                        try:
                            alert = driver.switch_to.alert
                            alert_text = alert.text
                            print(f"Server Alert Intercepted: {alert_text}")
                            alert.accept()
                            
                            if "invalid" in alert_text.lower() or "wrong" in alert_text.lower() or "match" in alert_text.lower() or "enter" in alert_text.lower():
                                print("CAPTCHA was rejected by the server! Refreshing and retrying...")
                                refresh_btn = driver.find_element(By.XPATH, "//*[contains(@onclick, 'captcha') or contains(@class, 'refresh')]")
                                driver.execute_script("arguments[0].click();", refresh_btn)
                                time.sleep(3)
                                continue
                            # 🔴 FIX 1: Handle the "Maximum OTP limit exceeded" alert gracefully
                            elif "maximum" in alert_text.lower() or "limit" in alert_text.lower() or "exceeded" in alert_text.lower():
                                print("⚠️ Max OTP Limit Reached (2 per hour). Proceeding to use your existing valid OTP from Gmail...")
                                limit_reached = True
                        except:
                            print("No alert presented by the website.")
                            
                        # 🔴 FIX 2: Verify the green "OTP sent" message appeared if we didn't hit the hourly limit
                        if not limit_reached:
                            if "OTP sent" not in driver.page_source and "OTP Sent" not in driver.page_source:
                                raise Exception("Missing 'OTP sent' confirmation. The request failed silently.")
                        
                        print("Scanning Gmail for the OTP...")
                        retrieved_otp = fetch_ireps_otp(retries=15)
                        
                        captcha_solved = True
                        break
                        
                    except Exception as e:
                        print(f"⚠ CAPTCHA/OTP Attempt failed: {e}")
                        try:
                            refresh_btn = driver.find_element(By.XPATH, "//*[contains(@onclick, 'captcha') or contains(@class, 'refresh')]")
                            driver.execute_script("arguments[0].click();", refresh_btn)
                            time.sleep(3)
                        except: pass

                if not captcha_solved or not retrieved_otp:
                    print("CRITICAL FAILURE: Pipeline broke at CAPTCHA/OTP stage. Aborting.")
                    driver.quit()
                    return []

                # ==========================================
                # 3. LIVE OTP INJECTION & SUBMISSION
                # ==========================================
                print(f"INCOMING TRANSMISSION: OTP {retrieved_otp} secured! Injecting into portal...")
                
                try:
                    otp_xpath = "//input[@placeholder='Enter OTP' or contains(translate(@placeholder, 'OTP', 'otp'), 'otp')]"
                    otp_input = wait.until(EC.presence_of_element_located((By.XPATH, otp_xpath)))
                except:
                    otp_xpath = "//td[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'today')]/following-sibling::td//input"
                    otp_input = wait.until(EC.presence_of_element_located((By.XPATH, otp_xpath)))

                otp_input.clear()
                otp_input.send_keys(retrieved_otp)
                time.sleep(3) 
                
                print("Executing automated PROCEED click...")
                try:
                    proceed_btn = wait.until(EC.presence_of_element_located((By.ID, "proceedButton")))
                    driver.execute_script("arguments[0].click();", proceed_btn)
                except:
                    proceed_btn = driver.find_element(By.XPATH, "//input[@id='proceedButton' or @name='proceed' or @value='Proceed']")
                    driver.execute_script("arguments[0].click();", proceed_btn)
                    
                time.sleep(3)
                try:
                    alert = driver.switch_to.alert
                    print(f"System Alert Intercepted after Proceed: {alert.text}")
                    alert.accept()
                except: pass
                
                print("Checking server response state...")
                time.sleep(5)
                
                page_source = driver.page_source
                
                if "404 Page not found" in page_source or "Click here to go to IREPS home page" in page_source:
                    print("🚨 True 404 Error Detected! The server dropped the session token.")
                    print("Clicking 'Click here' to reset the connection and starting over...")
                    try:
                        click_here_link = driver.find_element(By.LINK_TEXT, "Click here")
                        driver.execute_script("arguments[0].click();", click_here_link)
                    except Exception as fallback_e:
                        print(f"Could not find link, falling back to manual redirect: {fallback_e}")
                        driver.get("https://ireps.gov.in/")
                        
                    time.sleep(5)
                    continue
                
                print("Access Granted (Dashboard Confirmed). Bypassing gatekeeper...")
                time.sleep(3)

                # ==========================================
                # 4. FILTERING & SORTING ALGORITHM
                # ==========================================
                print("Selecting 'View E-Auction Schedule' tab...")
                try:
                    schedule_tab = wait.until(EC.presence_of_element_located((By.ID, "viewAuctionSchedule")))
                    driver.execute_script("arguments[0].click();", schedule_tab)
                    time.sleep(4)
                    
                    print("Configuring Query Parameters (Indian Railway -> N F RLY -> Upcoming)...")
                    
                    # Organization Dropdown (id="organization")
                    org_select = Select(wait.until(EC.presence_of_element_located((By.ID, "organization"))))
                    org_select.select_by_visible_text("Indian Railway")
                    time.sleep(3) 
                    
                    # Railway Unit Dropdown (name="railUnit")
                    zone_select = Select(driver.find_element(By.NAME, "railUnit"))
                    zone_select.select_by_visible_text("N F RLY")
                    time.sleep(3)
                    
                    # Auction Status Dropdown (id="catelogstatus")
                    status_select = Select(driver.find_element(By.ID, "catelogstatus"))
                    status_select.select_by_visible_text("Upcoming Auction")
                    time.sleep(2)
                    
                    # Submit Button
                    filter_btn = driver.find_element(By.XPATH, "//input[@name='submit' and @value='Sort / Filter']")
                    driver.execute_script("arguments[0].click();", filter_btn)
                    print("Data parameters locked. Querying database...")
                    time.sleep(5)

                    # ==========================================
                    # 5. DATA EXTRACTION GRID MAPPING
                    # ==========================================
                    print("Extracting Auction Radar Data...")
                    
                    try:
                        entries_select = Select(driver.find_element(By.XPATH, "//select[contains(@name, 'length')]"))
                        entries_select.select_by_visible_text("100")
                        time.sleep(3)
                    except: pass

                    rows = driver.find_elements(By.XPATH, "//table[contains(@class, 'dataTable') or contains(@id, 'table')]/tbody/tr")
                    print(f"Detected {len(rows)} upcoming auction blocks on current grid.")
                    
                    for row in rows:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        
                        # --- CRITICAL FIX: REDUCED TO 5 COLUMNS TO MATCH THE ACTUAL TABLE ---
                        if len(cols) < 5:
                            continue 
                            
                        schedule_no = cols[0].text.strip()
                        railway_unit = cols[1].text.strip()
                        depot = cols[2].text.strip()
                        start_date_str = cols[4].text.strip()
                        
                        try:
                            # The date in the image is formatted like "29/08/26 10:30:00"
                            date_obj = datetime.strptime(start_date_str, "%d/%m/%y %H:%M:%S")
                            iso_date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            iso_date_str = start_date_str

                        ui_title = f"IREPS SCH: {schedule_no}"
                        loc_val = f"{depot} ({railway_unit})"
                        
                        extracted_records.append({
                            'title': ui_title,
                            'category': "Indian Railway Scrap", 
                            'date': iso_date_str, 
                            'location': loc_val, 
                            'materials': "Heavy Railway Scrap (Catalogue pending release)",
                            'paperwork': "NOTE: Login to IREPS 1 day prior to auction to download final PDF Catalogue.",
                            'source': 'IREPS', 
                            'file_path': 'NO_PDF_YET',
                            'colorId': '10'  # <-- 10 = Basil Green in Google Calendar API
                        })
                        print(f"Mapped Record -> Schedule: {schedule_no} | Depot: {depot} | Date: {iso_date_str}")
                        
                except Exception as filter_error:
                    print(f"Could not load dashboard or extract data: {filter_error}")

                # If the script successfully extracts data and reaches this line, 
                # we break out of the master retry loop because we are done!
                break

            except Exception as loop_e:
                print(f"Critical error encountered during Attempt {master_attempt + 1}: {loop_e}")
                if master_attempt < 2:
                    print("Restarting pipeline...")
                    time.sleep(5)
                else:
                    print("Maximum retries exhausted.")

    except Exception as e:
        print(f"Total operational fault in IREPS Engine: {e}")
    finally:
        driver.quit()
        
    return extracted_records