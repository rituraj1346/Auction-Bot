# main.py
import config
from scrapers import mstc_scraper
from utils.pdf_generator import generate_summary
from utils.calendar_sync import sync_to_calendar
from utils.whatsapp_push import send_whatsapp_report

def main():
    print("====================================================")
    print("         LAUNCHING MASTER AUCTION ENGINE            ")
    print("====================================================\n")
    
    unified_auction_payload = []

    # Step 1: Data Gathering Lifecycle Loop
    if 'mstc' in config.ACTIVE_SITES:
        try:
            mstc_results = mstc_scraper.run_scraper()
            unified_auction_payload.extend(mstc_results)
            print(f"MSTC Adapter processing successfully completed. Added {len(mstc_results)} targets.")
        except Exception as e:
            print(f"Critical operational error processing MSTC interface adapter: {e}")

    if not unified_auction_payload:
        print("\nPipeline terminated: No matching auctions extracted from active channels.")
        return

    print(f"\nConsolidated Processing Matrix matched total of {len(unified_auction_payload)} entries.")

    # Step 2: Run Universal Utility Engines
    print("\nExecuting Tier 2 Engine: Generating Master Summary Document...")
    pdf_report_path = generate_summary(unified_auction_payload)
    
    print("\nExecuting Tier 3 Engine: Syncing Calendar Slots to Google API Platform...")
    sync_to_calendar(unified_auction_payload)
    
    print("\nExecuting Tier 4 Engine: Sending PDF Summary via Meta WhatsApp Channels...")
    send_whatsapp_report(pdf_report_path)

    print("\n====================================================")
    print("       PIPELINE SUCCESSFULLY COMPLETED              ")
    print("====================================================")

if __name__ == '__main__':
    main()