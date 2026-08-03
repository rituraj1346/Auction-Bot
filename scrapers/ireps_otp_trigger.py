<<<<<<< HEAD
import os
import sys
import time
import re
import base64
import requests
import traceback
from datetime import datetime, timedelta, timezone

# ==============================================================================
# PATH FIX FOR SUBFOLDER EXECUTION
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import config

TOKEN_PATH = os.path.join(parent_dir, 'token.json')
CREDS_PATH = os.path.join(parent_dir, 'credentials.json')
# ==============================================================================

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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_google_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds

def fetch_ireps_otp(creds, retries=15):
    service = build('gmail', 'v1', credentials=creds)

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    start_of_today_ist = datetime(now_ist.year, now_ist.month, now_ist.day, tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
    start_of_today_ms = int(start_of_today_ist.timestamp() * 1000)

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
                        print(f"📩 Successfully retrieved OTP: {match.group(1)}")
                        return match.group(1)
        except Exception:
            pass

        if retries > 1:
            print(f"⏳ Waiting for NEW OTP email... (Attempt {attempt+1}/{retries})")
            time.sleep(5)
    return None

def run_otp_trigger():
    print("🚀 Starting IREPS OTP Debugger...")
    creds = get_google_credentials()
    
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Explicitly tell Chrome to allow all popups just in case
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.popups": 1 
    })
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("🌐 Navigating to IREPS...")
        driver.get("https://ireps.gov.in/")
        time.sleep(3)
        driver.refresh()
        time.sleep(3)
        
        try:
            close_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close') or translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='close']"
            close_btns = driver.find_elements(By.XPATH, close_xpath)
            for btn in close_btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    break
        except: pass

        # ======================================================================
        # NEW METHOD: IMMUNE TO POPUP BLOCKERS
        # ======================================================================
        print("➡️ Entering E-Auction Sale Portal (URL Extraction Method)...")
        auction_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search e-auction sale')]")))
        
        # Extract the hidden URL destination from the button
        target_url = auction_btn.get_attribute("href")
        
        if target_url and "javascript" not in target_url and target_url != "#":
            print("🔗 Destination resolved! Generating new tab manually...")
            # Python creates the tab (Popup blockers cannot stop this)
            driver.switch_to.new_window('tab')
            driver.get(target_url)
        else:
            print("🔗 URL hidden. Using physical ActionChains click fallback...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", auction_btn)
            time.sleep(1)
            ActionChains(driver).move_to_element(auction_btn).click().perform()
            wait.until(EC.number_of_windows_to_be(2))
            driver.switch_to.window(driver.window_handles[-1])
            
        time.sleep(5)
        # ======================================================================
            
        print(f"📱 Entering Mobile Number: {config.IREPS_MOBILE}")
        mobile_xpath = "//input[contains(@name, 'mobile') or contains(@id, 'mobile')]"
        mobile_input = wait.until(EC.presence_of_element_located((By.XPATH, mobile_xpath)))
        mobile_input.clear()
        mobile_input.send_keys(config.IREPS_MOBILE)
        time.sleep(1)

        print("🧩 Solving Captcha via 2Captcha...")
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
        
        if response.get('status') != 1: 
            raise Exception("2Captcha Rejection")
        request_id = response.get('request')
        
        captcha_answer = None
        for _ in range(25):
            time.sleep(5)
            res = requests.get(f"http://2captcha.com/res.php?key={config.TWOCAPTCHA_API_KEY}&action=get&id={request_id}&json=1").json()
            if res.get('status') == 1:
                captcha_answer = res.get('request')
                break
        
        if not captcha_answer: 
            raise Exception("Captcha Solved Timeout")
        
        print(f"✅ Captcha Solved: {captcha_answer}")
        captcha_input = driver.find_element(By.XPATH, "//input[contains(@name, 'captcha') or contains(@placeholder, 'Code')]")
        captcha_input.clear()
        
        # Inject the captcha and hit TAB to trigger Javascript validation
        captcha_input.send_keys(captcha_answer)
        time.sleep(1)
        print("⌨️ Firing TAB key to register input...")
        captcha_input.send_keys(Keys.TAB)
        time.sleep(1)
        
        print("⚡ Executing Standard Native Click...")
        btn = driver.find_element(By.XPATH, "//input[@value='Get OTP']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(1)
        
        try:
            btn.click() # Standard physical click (often bypasses JS restrictions)
        except Exception as e:
            print("Standard click blocked. Using JS Click fallback...")
            driver.execute_script("arguments[0].click();", btn)

        time.sleep(3)
        
        # ======================================================================
        # THE CAMERA - SNAP A PICTURE
        # ======================================================================
        screenshot_path = os.path.join(parent_dir, "debug_otp_page.png")
        driver.save_screenshot(screenshot_path)
        print(f"📸 SNAP! Saved screenshot to: {screenshot_path}")
        
        # Check for alerts
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            print(f"⚠️ Alert Intercepted: '{alert_text}'")
        except: 
            print("✅ No alert boxes popped up.")
            
        # Check text on page for silent errors
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Invalid" in page_text or "wrong" in page_text.lower():
            print("🔴 WARNING: The page text contains the word 'Invalid' or 'Wrong'. Check the screenshot!")
            
        print("📡 Connecting to Gmail to retrieve OTP...")
        retrieved_otp = fetch_ireps_otp(creds, retries=5)
        
        if retrieved_otp:
            print(f"🎉 SUCCESS! Final OTP string captured: {retrieved_otp}")
        else:
            print("❌ Failed to retrieve OTP. Please open 'debug_otp_page.png' to see what went wrong.")

    except Exception as e:
        print(f"❌ Execution Fault:\n{traceback.format_exc()}")
        
    finally:
        print("🛑 Closing browser...")
        driver.quit()

if __name__ == "__main__":
=======
import os
import sys
import time
import re
import base64
import requests
import traceback
from datetime import datetime, timedelta, timezone

# ==============================================================================
# PATH FIX FOR SUBFOLDER EXECUTION
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import config

TOKEN_PATH = os.path.join(parent_dir, 'token.json')
CREDS_PATH = os.path.join(parent_dir, 'credentials.json')
# ==============================================================================

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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_google_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds

def fetch_ireps_otp(creds, retries=15):
    service = build('gmail', 'v1', credentials=creds)

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    start_of_today_ist = datetime(now_ist.year, now_ist.month, now_ist.day, tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
    start_of_today_ms = int(start_of_today_ist.timestamp() * 1000)

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
                        print(f"📩 Successfully retrieved OTP: {match.group(1)}")
                        return match.group(1)
        except Exception:
            pass

        if retries > 1:
            print(f"⏳ Waiting for NEW OTP email... (Attempt {attempt+1}/{retries})")
            time.sleep(5)
    return None

def run_otp_trigger():
    print("🚀 Starting IREPS OTP Debugger...")
    creds = get_google_credentials()
    
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Explicitly tell Chrome to allow all popups just in case
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.popups": 1 
    })
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("🌐 Navigating to IREPS...")
        driver.get("https://ireps.gov.in/")
        time.sleep(3)
        driver.refresh()
        time.sleep(3)
        
        try:
            close_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'close') or translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='close']"
            close_btns = driver.find_elements(By.XPATH, close_xpath)
            for btn in close_btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    break
        except: pass

        # ======================================================================
        # NEW METHOD: IMMUNE TO POPUP BLOCKERS
        # ======================================================================
        print("➡️ Entering E-Auction Sale Portal (URL Extraction Method)...")
        auction_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search e-auction sale')]")))
        
        # Extract the hidden URL destination from the button
        target_url = auction_btn.get_attribute("href")
        
        if target_url and "javascript" not in target_url and target_url != "#":
            print("🔗 Destination resolved! Generating new tab manually...")
            # Python creates the tab (Popup blockers cannot stop this)
            driver.switch_to.new_window('tab')
            driver.get(target_url)
        else:
            print("🔗 URL hidden. Using physical ActionChains click fallback...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", auction_btn)
            time.sleep(1)
            ActionChains(driver).move_to_element(auction_btn).click().perform()
            wait.until(EC.number_of_windows_to_be(2))
            driver.switch_to.window(driver.window_handles[-1])
            
        time.sleep(5)
        # ======================================================================
            
        print(f"📱 Entering Mobile Number: {config.IREPS_MOBILE}")
        mobile_xpath = "//input[contains(@name, 'mobile') or contains(@id, 'mobile')]"
        mobile_input = wait.until(EC.presence_of_element_located((By.XPATH, mobile_xpath)))
        mobile_input.clear()
        mobile_input.send_keys(config.IREPS_MOBILE)
        time.sleep(1)

        print("🧩 Solving Captcha via 2Captcha...")
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
        
        if response.get('status') != 1: 
            raise Exception("2Captcha Rejection")
        request_id = response.get('request')
        
        captcha_answer = None
        for _ in range(25):
            time.sleep(5)
            res = requests.get(f"http://2captcha.com/res.php?key={config.TWOCAPTCHA_API_KEY}&action=get&id={request_id}&json=1").json()
            if res.get('status') == 1:
                captcha_answer = res.get('request')
                break
        
        if not captcha_answer: 
            raise Exception("Captcha Solved Timeout")
        
        print(f"✅ Captcha Solved: {captcha_answer}")
        captcha_input = driver.find_element(By.XPATH, "//input[contains(@name, 'captcha') or contains(@placeholder, 'Code')]")
        captcha_input.clear()
        
        # Inject the captcha and hit TAB to trigger Javascript validation
        captcha_input.send_keys(captcha_answer)
        time.sleep(1)
        print("⌨️ Firing TAB key to register input...")
        captcha_input.send_keys(Keys.TAB)
        time.sleep(1)
        
        print("⚡ Executing Standard Native Click...")
        btn = driver.find_element(By.XPATH, "//input[@value='Get OTP']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(1)
        
        try:
            btn.click() # Standard physical click (often bypasses JS restrictions)
        except Exception as e:
            print("Standard click blocked. Using JS Click fallback...")
            driver.execute_script("arguments[0].click();", btn)

        time.sleep(3)
        
        # ======================================================================
        # THE CAMERA - SNAP A PICTURE
        # ======================================================================
        screenshot_path = os.path.join(parent_dir, "debug_otp_page.png")
        driver.save_screenshot(screenshot_path)
        print(f"📸 SNAP! Saved screenshot to: {screenshot_path}")
        
        # Check for alerts
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            print(f"⚠️ Alert Intercepted: '{alert_text}'")
        except: 
            print("✅ No alert boxes popped up.")
            
        # Check text on page for silent errors
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Invalid" in page_text or "wrong" in page_text.lower():
            print("🔴 WARNING: The page text contains the word 'Invalid' or 'Wrong'. Check the screenshot!")
            
        print("📡 Connecting to Gmail to retrieve OTP...")
        retrieved_otp = fetch_ireps_otp(creds, retries=5)
        
        if retrieved_otp:
            print(f"🎉 SUCCESS! Final OTP string captured: {retrieved_otp}")
        else:
            print("❌ Failed to retrieve OTP. Please open 'debug_otp_page.png' to see what went wrong.")

    except Exception as e:
        print(f"❌ Execution Fault:\n{traceback.format_exc()}")
        
    finally:
        print("🛑 Closing browser...")
        driver.quit()

if __name__ == "__main__":
>>>>>>> 67587b0 (fixed chrome invisible error and added ireps otp scrapper)
    run_otp_trigger()