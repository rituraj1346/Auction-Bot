# scrapers/mstc_scraper.py
import os
import glob
import time
import re
import pdfplumber
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import config

def run_scraper():
    print("Launching MSTC Public Extraction Engine (Multi-State + Auto-Captcha)...")
    extracted_records = []
    
    # 1. Workspace Cleanup
    if not os.path.exists(config.DOWNLOAD_DIR):
        os.makedirs(config.DOWNLOAD_DIR)
    for old_file in glob.glob(os.path.join(config.DOWNLOAD_DIR, "*")):
        os.remove(old_file)

    # 2. Boot Chrome in Silent Download Mode
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
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    
    try:
        # ==========================================
        # AUTOMATED UI NAVIGATION 
        # ==========================================
        print("Navigating to MSTC Homepage...")
        driver.get("https://www.mstcecommerce.com/")
        
        time.sleep(2) 
        search_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search auction')]")))
        driver.execute_script("arguments[0].click();", search_btn)
        
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[1])
            
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Upcoming Auctions')]"))).click()
        time.sleep(1)
        
        print("Selecting 'All' upcoming dates...")
        try:
            all_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//*[normalize-space(text())='All']")))
            driver.execute_script("arguments[0].click();", all_btn)
        except Exception:
            pass
        time.sleep(1)
        
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Filter by Location')]"))).click()
        time.sleep(1)
        
        print(f"Applying {len(config.TARGET_LOCATIONS)} State Filters...")
        dropdown_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'None selected') or contains(text(), 'selected')]")))
        driver.execute_script("arguments[0].click();", dropdown_button)
        time.sleep(1)
        
        for state in config.TARGET_LOCATIONS:
            try:
                state_lbl = driver.find_element(By.XPATH, f"//label[contains(text(), '{state}')]")
                driver.execute_script("arguments[0].click();", state_lbl)
                time.sleep(0.3) 
            except:
                print(f"Warning: Could not find '{state}' in the dropdown list.")
                
        print("Triggering CAPTCHA popup...")
        search_btn_final = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Search')]")))
        driver.execute_script("arguments[0].click();", search_btn_final)
        
        try:
            WebDriverWait(driver, 2).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert.accept()
        except:
            pass
        
        # ==========================================
        # AUTOMATED CAPTCHA SOLVING VIA 2CAPTCHA
        # ==========================================
        print("\n====================================================")
        print("      INITIATING GHOST SOLVER (2Captcha API)      ")
        print("====================================================")
        
        captcha_solved = False
        for captcha_attempt in range(4): 
            try:
                # 1. Isolate the exact Popup Box
                input_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Verification Code' or contains(@name, 'captcha') or contains(@id, 'captcha')]")))
                modal = input_box.find_element(By.XPATH, "./ancestor::*[contains(@class, 'modal') or @role='dialog' or contains(@class, 'popup') or contains(@style, 'z-index')][1]")
                
                captcha_img = modal.find_element(By.XPATH, ".//img")
                
                print(f"CAPTCHA image isolated perfectly (Attempt {captcha_attempt + 1}). Extracting raw pixel data via Canvas...")
                
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
                
                # 2. Transmit to 2Captcha
                print("Transmitting to 2Captcha network...")
                payload = {
                    'key': config.TWOCAPTCHA_API_KEY,
                    'method': 'base64',
                    'body': img_base64,
                    'json': 1
                }
                response = requests.post('http://2captcha.com/in.php', data=payload).json()
                
                if response.get('status') != 1:
                    raise Exception(f"2Captcha rejection: {response.get('request')}")
                    
                request_id = response.get('request')
                print(f"Image accepted (Request ID: {request_id}). Awaiting remote worker...")
                
                # 3. Poll for the solution
                captcha_answer = None
                for poll_attempt in range(25): 
                    time.sleep(5)
                    res = requests.get(f"http://2captcha.com/res.php?key={config.TWOCAPTCHA_API_KEY}&action=get&id={request_id}&json=1").json()
                    
                    if res.get('status') == 1:
                        captcha_answer = res.get('request')
                        break
                    elif res.get('request') != 'CAPCHA_NOT_READY':
                        raise Exception(res.get('request'))
                        
                    print(f"Worker thinking... (Tick {poll_attempt+1})")
                
                if not captcha_answer:
                    raise Exception("2Captcha timeout. Worker took too long.")
                    
                print(f"Success! CAPTCHA Solved: '{captcha_answer}'")
                
                # 4. Inject answer and Submit
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", input_box)
                time.sleep(0.5)
                
                driver.execute_script("arguments[0].value = arguments[1];", input_box, captcha_answer)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_box)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", input_box)
                time.sleep(0.5)
                
                submit_btn = driver.find_element(By.ID, "capbtn")
                driver.execute_script("arguments[0].click();", submit_btn)
                
                print("Payload submitted. Waiting for security modal to close and results to load...")
                
                try:
                    WebDriverWait(driver, 10).until(EC.invisibility_of_element(modal))
                    print("Modal closed! Downloading auction tables...")
                except:
                    print("Warning: Modal did not close cleanly, but attempting to proceed...")
                
                time.sleep(12) 
                captcha_solved = True
                break 
                
            except Exception as e:
                error_msg = str(e)
                print(f"⚠ CAPTCHA Attempt {captcha_attempt + 1} failed: {error_msg}")
                
                if ("ERROR_CAPTCHA_UNSOLVABLE" in error_msg or "unsolvable" in error_msg.lower()) and captcha_attempt < 3:
                    print("Clicking 'Refresh' to generate a new CAPTCHA variation...")
                    try:
                        refresh_btn = modal.find_element(By.XPATH, ".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'refresh')]")
                        driver.execute_script("arguments[0].click();", refresh_btn)
                        time.sleep(3) 
                    except:
                        print("Could not trigger refresh component. Retrying engine natively.")
                else:
                    if captcha_attempt >= 3:
                        print("Max CAPTCHA retries reached. Aborting to save API funds.")
                        driver.quit()
                        return []

        if not captcha_solved:
            driver.quit()
            return []

    except Exception as e:
        print(f"Navigation error: {e}")
        driver.quit()
        return []

    # ==========================================
    # AUTOMATED DOWNLOADING: DEEP TEXT SEARCH
    # ==========================================
    try:
        print("Executing Deep Text Dragnet: Searching nested elements...")
        
        pdf_triggers = driver.find_elements(By.XPATH, "//a[contains(., 'MSTC/')]")
        
        if not pdf_triggers:
            print("Auction IDs are not links. Searching for 'Download PDF' text blocks...")
            pdf_triggers = driver.find_elements(By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download pdf')]")
            
        if not pdf_triggers:
            print("No text links found. Searching for raw Javascript buttons...")
            pdf_triggers = driver.find_elements(By.XPATH, "//*[contains(@onclick, 'pdf') or contains(@href, 'pdf')]")
            
        if not pdf_triggers:
            print("Deep search triggered: Grabbing all visible links inside the results table...")
            pdf_triggers = driver.find_elements(By.XPATH, "//table//a | //*[contains(@class, 'search-result')]//a")

        print(f"Found {len(pdf_triggers)} actionable document triggers. Initiating download sequence...")
        
        for trigger in pdf_triggers:
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", trigger)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", trigger)
                time.sleep(3) 
            except Exception as e:
                print(f"Skipped a trigger due to interaction error: {e}")
                
        print("Download sequence complete. Waiting 10 seconds for background network tasks to finalize...")
        time.sleep(10)  
    except Exception as e:
        print(f"Critical failure during download sequence: {e}")

    driver.quit()

    # ==========================================
    # PARSING THE SINGLE PDFS (WITH TABLE EXTRACTION)
    # ==========================================
    print("Parsing downloaded PDFs with Aggressive Extraction Engine...")
    downloaded_files = glob.glob(os.path.join(config.DOWNLOAD_DIR, "*.pdf"))
    
    if not downloaded_files:
        print("Error: No PDF files were successfully downloaded to the folder.")
    
    for file_path in downloaded_files:
        try:
            pdf_text = ""
            lot_descriptions = []
            lot_locations = []
            
            with pdfplumber.open(file_path) as pdf:
                pdf_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table: continue
                        for row in table:
                            if not row: continue
                            row_text = " | ".join([str(cell).replace('\n', ' ') for cell in row if cell])
                            
                            desc_match = re.search(r'Lot Name\s*[-:]\s*([^|]+)', row_text, re.IGNORECASE)
                            if desc_match:
                                clean_desc = desc_match.group(1).strip()
                                if clean_desc and clean_desc not in lot_descriptions:
                                    lot_descriptions.append(clean_desc)
                            
                            loc_match = re.search(r'Lot State\s*[-:]\s*([^|]+)', row_text, re.IGNORECASE)
                            if not loc_match:
                                loc_match = re.search(r'State\s*:\s*([^|]+)', row_text, re.IGNORECASE)
                            if loc_match:
                                clean_loc = loc_match.group(1).strip()
                                if clean_loc and clean_loc not in lot_locations:
                                    lot_locations.append(clean_loc)

            title_match = re.search(r'(MSTC/[^\s]+)', pdf_text, re.IGNORECASE)
            date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{2,4}\s+\d{2}:\d{2}(?::\d{2})?)', pdf_text)
            emd_match = re.search(r'EMD.*?((?:Rs\.?|INR)?\s*[\d,]+(?:\.\d+)?|\d+(?:\.\d+)?\s*%)', pdf_text, re.IGNORECASE)

            title_val = title_match.group(1).strip() if title_match else os.path.basename(file_path)
            date_val = date_match.group(1).strip() if date_match else "Verify Date inside Document"
            emd_val = f"EMD: {emd_match.group(1).strip()}" if emd_match else "Refer to catalogue provisions"
            
            if lot_locations:
                location_val = ", ".join(list(set(lot_locations)))
            else:
                location_val = "Location listed in PDF"

            if lot_descriptions:
                mat_val = " | ".join(lot_descriptions[:5]) 
            else:
                mat_val = "Industrial Material (View PDF for details)"

            # Smart Categorization Engine
            category_val = "General Scrap / Assorted"
            mat_text_lower = mat_val.lower()
            if any(w in mat_text_lower for w in ["vehicle", "car", "truck", "engine", "tyre"]): category_val = "Vehicles & Auto Scrap"
            elif any(w in mat_text_lower for w in ["cable", "wire", "conductor", "copper"]): category_val = "Electrical & Cable Scrap"
            elif any(w in mat_text_lower for w in ["transformer"]): category_val = "Transformers & Heavy Electrical"
            elif any(w in mat_text_lower for w in ["battery"]): category_val = "Used Batteries"
            elif any(w in mat_text_lower for w in ["oil", "lube", "petroleum", "brunt"]): category_val = "Used / Waste Oil"
            elif any(w in mat_text_lower for w in ["furniture"]): category_val = "Office Furniture & Equipment"
            elif any(w in mat_text_lower for w in ["iron", "scrap", "steel"]): category_val = "Iron & Metal Scrap"

            extracted_records.append({
                'title': title_val,
                'category': category_val, 
                'date': date_val,
                'location': location_val, 
                'materials': mat_val,
                'paperwork': emd_val,
                'source': 'MSTC',
                'file_path': file_path  
            })
        except Exception as e:
            print(f"Failed to read file {file_path}: {e}")
            
    return extracted_records