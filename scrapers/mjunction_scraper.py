# scrapers/mjunction_scraper.py
import os
import glob
import time
import re
import pdfplumber
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config

def run_scraper():
    print("Launching Precision MetalJunction Engine (Bulletproof Date Engine)...")
    extracted_records = []
    
    # 1. Clean workspace to prevent file contamination
    if not os.path.exists(config.DOWNLOAD_DIR):
        os.makedirs(config.DOWNLOAD_DIR)
    for old_file in glob.glob(os.path.join(config.DOWNLOAD_DIR, "*")):
        try:
            os.remove(old_file)
        except:
            pass
        
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
        # STEP 1: PUBLIC REGIONAL NAVIGATION
        # ==========================================
        print("Navigating to MetalJunction Homepage...")
        driver.get("https://auction1.metaljunction.com/") 
        time.sleep(4)
        
        print("Opening 'Auctions' top menu...")
        auctions_menu = wait.until(EC.presence_of_element_located((By.XPATH, "//*[normalize-space(text())='Auctions']")))
        driver.execute_script("arguments[0].click();", auctions_menu)
        time.sleep(2)
        
        print("Clicking 'All Auctions' from the dropdown option...")
        all_auctions_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'All Auctions')] | //*[normalize-space(text())='All Auctions']")))
        driver.execute_script("arguments[0].click();", all_auctions_btn)
        time.sleep(4)
        
        print("Selecting 'Upcoming Auctions' tab...")
        upcoming_tabs = driver.find_elements(By.XPATH, "//*[contains(text(), 'Upcoming Auctions')]")
        if upcoming_tabs:
            for tab in upcoming_tabs:
                try:
                    driver.execute_script("arguments[0].click();", tab)
                    break
                except:
                    pass
        time.sleep(5) 

        # ==========================================
        # STEP 2: MULTI-PAGE PROCESSING LOOP
        # ==========================================
        current_page = 1
        previous_page_first_title = ""
        
        while True:
            print(f"\n--- PROCESSING PAGE {current_page} ---")
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1.5)
            
            time_anchors = driver.find_elements(By.XPATH, "//*[contains(text(), 'Starts at:')]")
            num_cards = len(time_anchors)
            print(f"Found {num_cards} text anchors to scan on this page.")
            
            if num_cards == 0:
                print("No active cards detected on this page grid.")
                break
                
            # Infinite Loop Prevention
            try:
                first_card = time_anchors[0].find_element(By.XPATH, "./ancestor::mat-grid-tile[1] | ./ancestor::*[contains(@class, 'card')][1]")
                first_card_sample = first_card.text
                if first_card_sample == previous_page_first_title:
                    print("⚠ Pagination Terminal Signal: Page contents identical to last loop step. Reached final page!")
                    break
                previous_page_first_title = first_card_sample
            except Exception:
                pass

            processed_card_ids = set()

            for i in range(num_cards):
                try:
                    current_anchors = driver.find_elements(By.XPATH, "//*[contains(text(), 'Starts at:')]")
                    if i >= len(current_anchors):
                        break
                    anchor = current_anchors[i]
                    
                    # 1. Isolate the specific overarching card container
                    try:
                        card_container = anchor.find_element(By.XPATH, "./ancestor::mat-grid-tile[1] | ./ancestor::mat-card[1] | ./ancestor::*[contains(@class, 'card')][1]")
                    except:
                        card_container = anchor.find_element(By.XPATH, "../../../..")
                        
                    if card_container.id in processed_card_ids:
                        continue
                    processed_card_ids.add(card_container.id)
                        
                    # ==========================================
                    # PROTOCOL 1: BULLETPROOF DATA EXTRACTION
                    # ==========================================
                    card_text_raw = card_container.text
                    card_inner_raw = card_container.get_attribute("textContent")
                    combined_text_raw = card_text_raw + " " + card_inner_raw
                    combined_text_upper = combined_text_raw.upper()
                    
                    is_scrap = "SCRAP" in combined_text_upper or "WASTE" in combined_text_upper
                    is_hazardous = "HAZARDOUS" in combined_text_upper
                    
                    if not is_scrap and not is_hazardous:
                        continue 
                    
                    assigned_category = "Hazardous Waste" if is_hazardous else "Scrap & Assorted Materials"
                    
                    # --- FIXED: Manual Regex Date Parsing ---
                    # We bypass Python's built-in date parser entirely because hidden HTML spaces crash it.
                    # This guarantees we rip the exact numbers out of the string safely.
                    date_match = re.search(r'([a-zA-Z]+),\s*([a-zA-Z]+)\s*(\d{1,2}),\s*(\d{4})', combined_text_raw)
                    time_match = re.search(r'Starts at:\s*(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)', combined_text_raw)
                    
                    if date_match and time_match:
                        month_str = date_match.group(2)[:3].upper() # Forces 'JUL'
                        day_num = int(date_match.group(3))
                        year_num = int(date_match.group(4))
                        
                        hour_num = int(time_match.group(1))
                        minute_str = time_match.group(2)
                        ampm = time_match.group(3).upper()
                        
                        months = {"JAN":1, "FEB":2, "MAR":3, "APR":4, "MAY":5, "JUN":6, "JUL":7, "AUG":8, "SEP":9, "OCT":10, "NOV":11, "DEC":12}
                        month_num = months.get(month_str, 1)
                        
                        if ampm == 'PM' and hour_num != 12:
                            hour_num += 12
                        elif ampm == 'AM' and hour_num == 12:
                            hour_num = 0
                            
                        # Universal ISO format (YYYY-MM-DD) to prevent the calendar script from ever confusing Month vs Day
                        combined_date = f"{year_num:04d}-{month_num:02d}-{day_num:02d} {hour_num:02d}:{minute_str}:00"
                        
                        # Custom filename format honoring your Month-Day-Year layout
                        pdf_safe_date = f"{month_str}-{day_num:02d}-{year_num:04d}"
                    else:
                        print("⚠ Date extraction missed on this card, falling back to manual review.")
                        combined_date = "Check PDF for Time"
                        pdf_safe_date = "UnknownDate"
                    
                    # Clean Title extraction
                    lines = [line.strip() for line in card_text_raw.split('\n') if line.strip()]
                    filtered_lines = [l for l in lines if not any(x in l.lower() for x in ['image not', 'available', 'starts at', 'version'])]
                    ui_title = filtered_lines[0][:80] if filtered_lines else "Unknown Auction Title"
                    
                    print(f"\n[MATCH] Target Identified: {ui_title}")
                    print(f"[*] Scheduled Date: {combined_date}")
                    
                    files_before = set(glob.glob(os.path.join(config.DOWNLOAD_DIR, "*.pdf")))
                    
                    # ==========================================
                    # PROTOCOL 2: SECURE PDF DOWNLOAD
                    # ==========================================
                    interactive_elements = card_container.find_elements(By.XPATH, ".//a | .//button | .//*[local-name()='svg'] | .//mat-icon")
                    
                    if not interactive_elements:
                        print("No interactive download button found on this card. Skipping.")
                        continue
                        
                    download_btn = interactive_elements[-1]
                    
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", download_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", download_btn)
                    print("Direct download triggered. Awaiting document stream...")
                    
                    target_pdf = None
                    for _ in range(30): 
                        time.sleep(0.5)
                        cr_downloads = glob.glob(os.path.join(config.DOWNLOAD_DIR, "*.crdownload"))
                        if cr_downloads:
                            continue 
                            
                        files_after = set(glob.glob(os.path.join(config.DOWNLOAD_DIR, "*.pdf")))
                        new_files = files_after - files_before
                        
                        if new_files:
                            target_pdf = list(new_files)[0]
                            break
                            
                    if not target_pdf or not os.path.exists(target_pdf):
                        print("⚠ Document link timeout. Skipping compilation.")
                        continue
                        
                    unique_timestamp = int(time.time() * 1000)
                    new_filename = f"{pdf_safe_date}_mj_{unique_timestamp}.pdf"
                    new_path = os.path.join(config.DOWNLOAD_DIR, new_filename)
                    
                    os.rename(target_pdf, new_path)
                    target_pdf = new_path
                    print(f"File downloaded & renamed to: {new_filename}")
                    
                    # ==========================================
                    # PROTOCOL 3: OMNI-READER PDF EXTRACTION
                    # ==========================================
                    lot_descriptions = []
                    lot_locations = []
                    
                    try:
                        with pdfplumber.open(target_pdf) as pdf:
                            for page in pdf.pages:
                                tables = page.extract_tables()
                                for table in tables:
                                    if not table: continue
                                    for row in table:
                                        if not row: continue
                                        clean_row = [str(cell).replace('\n', ' ').strip() for cell in row if cell]
                                        if not clean_row: continue
                                        
                                        row_text = " | ".join(clean_row)
                                        
                                        desc_match = re.search(r'(?:Description|Material|Product|Item|Lot Name)\s*(?:[-:]|\|)?\s*([^|]+)', row_text, re.IGNORECASE)
                                        if desc_match and len(desc_match.group(1)) > 3:
                                            lot_descriptions.append(desc_match.group(1).strip())
                                            
                                        loc_match = re.search(r'(?:Location|Plant|State|City|Site|Unit)\s*(?:[-:]|\|)?\s*([^|]+)', row_text, re.IGNORECASE)
                                        if loc_match and len(loc_match.group(1)) > 3:
                                            lot_locations.append(loc_match.group(1).strip())

                                text = page.extract_text()
                                if text:
                                    for line in text.split('\n'):
                                        line = line.strip()
                                        desc_match = re.search(r'(?:Description|Material|Product|Item|Lot Name)\s*[:\-]\s*(.+)', line, re.IGNORECASE)
                                        if desc_match and len(desc_match.group(1)) > 3:
                                            lot_descriptions.append(desc_match.group(1).strip())
                                            
                                        loc_match = re.search(r'(?:Location|Plant|State|City|Site|Unit)\s*[:\-]\s*(.+)', line, re.IGNORECASE)
                                        if loc_match and len(loc_match.group(1)) > 3:
                                            lot_locations.append(loc_match.group(1).strip())
                                            
                    except Exception as e:
                        print(f"⚠ Minor PDF Read Error (Safely bypassed): {e}")

                    lot_descriptions = list(set(lot_descriptions))
                    lot_locations = list(set(lot_locations))
                    
                    mat_val = " | ".join(lot_descriptions[:4]) if lot_descriptions else "Scrap Material (View attached PDF for exact details)"
                    loc_val = ", ".join(lot_locations[:3]) if lot_locations else "Location detailed in PDF"
                    
                    extracted_records.append({
                        'title': ui_title,
                        'category': assigned_category, 
                        'date': combined_date, 
                        'location': loc_val, 
                        'materials': mat_val,
                        'paperwork': "EMD Info inside attached PDF",
                        'source': 'METALJUNCTION', 
                        'file_path': target_pdf 
                    })
                    print("Data mapping completed successfully.")

                except Exception as e:
                    print(f"Skipped card due to extraction error: {e}")

            # ==========================================
            # STEP 3: PAGINATION ROUTER
            # ==========================================
            try:
                print("\nReaching end of current page block. Locating 'Next' button...")
                next_btn = driver.find_element(By.XPATH, "//*[normalize-space(text())='Next'] | //button[contains(., 'Next')]")
                
                is_disabled = (
                    next_btn.get_attribute("disabled") == "true" or
                    next_btn.get_attribute("disabled") == "" or
                    "disabled" in next_btn.get_attribute("class") or
                    next_btn.get_attribute("aria-disabled") == "true"
                )
                
                if is_disabled:
                    print("Pagination terminal reached: 'Next' button is visibly disabled.")
                    break
                    
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", next_btn)
                
                current_page += 1
                print(f"Advancing grid view to page {current_page}...")
                time.sleep(5) 
                
            except Exception:
                print("Pagination component absent or terminal page index reached.")
                break

    except Exception as e:
        print(f"Critical operational fault: {e}")
    finally:
        driver.quit()
        
    return extracted_records