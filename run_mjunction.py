# run_mjunction.py
from scrapers import mjunction_scraper
from utils.pdf_generator import generate_summary
from utils.calendar_sync import sync_to_calendar
from utils.whatsapp_push import send_whatsapp_report

def main():
    print("====================================================")
    print("      LAUNCHING METALJUNCTION AUCTION ENGINE        ")
    print("====================================================\n")
    
    results = mjunction_scraper.run_scraper()
    
    if not results:
        print("Pipeline terminated: No matching Scrap/Hazardous auctions found.")
        return

    print("\nExecuting Tier 2: Generating PDF Summary...")
    pdf_report_path = generate_summary(results)
    
    print("\nExecuting Tier 3: Syncing to Google Calendar & Drive...")
    sync_to_calendar(results)
    
    print("\nExecuting Tier 4: Sending WhatsApp Report...")
    send_whatsapp_report(pdf_report_path)
    print("\n[METALJUNCTION PIPELINE COMPLETE]")

if __name__ == '__main__':
    main()