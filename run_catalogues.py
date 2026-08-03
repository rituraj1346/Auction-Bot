# run_catalogues.py
import config
from scrapers import ireps_catalogue_scraper

def main():
    print("====================================================")
    print("     LAUNCHING IREPS CATALOGUE DOWNLOAD ENGINE      ")
    print("====================================================")
    
    if 'ireps' in config.ACTIVE_SITES:
        print("Initiating daily upcoming catalogue download pipeline...")
        # Fire off the dedicated catalogue extraction engine
        ireps_catalogue_scraper.run_catalogues_downloader()
    else:
        print("Error: 'ireps' is not enabled in config.ACTIVE_SITES.")

if __name__ == "__main__":
    main()