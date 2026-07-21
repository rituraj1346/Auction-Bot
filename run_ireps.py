# run_ireps.py
import config
from scrapers import ireps_scraper
from utils import calendar_sync

def main():
    print("====================================================")
    print("         LAUNCHING IREPS RAILWAY ENGINE             ")
    print("====================================================")
    
    if 'ireps' in config.ACTIVE_SITES:
        auctions = ireps_scraper.run_scraper()
        if auctions:
            print(f"IREPS Engine extracted {len(auctions)} targets. Syncing to Calendar...")
            calendar_sync.sync_to_calendar(auctions)
        else:
            print("Pipeline terminated: No matching auctions extracted from IREPS.")
    else:
        print("Error: 'ireps' is not enabled in config.ACTIVE_SITES.")

if __name__ == "__main__":
    main()