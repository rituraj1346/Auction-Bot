# Auction Bot

**Author:** [Rituraj Deka](https://github.com/rituraj1346)

An automated scrap-auction tracker. It scrapes Indian e-auction portals for upcoming
**scrap** and **hazardous waste** auctions, downloads their catalogues, builds a PDF
summary, adds every auction to Google Calendar (with the catalogue in Google Drive), and
sends the report on WhatsApp.

> © 2026 Rituraj Deka. All rights reserved. This is **not** open-source software.
> You may not sell, copy, modify, or use it commercially without written permission.
> See [LICENSE](LICENSE).

## Supported portals

| Portal | Runner | Scraper |
|---|---|---|
| MSTC | `run_mstc.py` | `scrapers/mstc_scraper.py` |
| MetalJunction (mjunction) | `run_mjunction.py` | `scrapers/mjunction_scraper.py` |
| IREPS (Indian Railways) | `run_ireps.py` | `scrapers/ireps_scraper.py` |
| IREPS catalogues | `run_catalogues.py` | `scrapers/ireps_catalogue_scraper.py` |

## Pipeline

1. **Scrape** – Selenium (Chrome) opens the portal, filters scrap and hazardous-waste
   auctions, and downloads each catalogue PDF.
2. **Extract** – `pdfplumber` reads materials and locations out of the catalogues.
3. **Summarise** – `utils/pdf_generator.py` builds `Auction_Summary_Report.pdf`.
4. **Calendar & Drive** – `utils/calendar_sync.py` creates Google Calendar events and
   uploads catalogues to Google Drive.
5. **WhatsApp** – `utils/whatsapp_push.py` sends the report via the WhatsApp Cloud API.

## Requirements

- Windows, Python 3, Google Chrome
- Python packages:

```
pip install selenium pdfplumber fpdf2 requests python-dotenv google-api-python-client google-auth-oauthlib google-auth-httplib2
```

## Configuration

Secrets are never committed. Create these files in the project folder (all are in `.gitignore`):

**`.env`**
```
TWOCAPTCHA_API_KEY=
IREPS_MOBILE=
WA_PHONE_ID=
WA_BUSINESS_ID=
WA_TOKEN=
SEND_TO_NUMBER=
```

**`credentials.json`** – Google OAuth client (Calendar, Drive, Gmail scopes).
`token.json` is created automatically on first login.

Paths and target states are set in `config.py` (`BASE_DIR`, `TARGET_LOCATIONS`, `ACTIVE_SITES`).

## Usage

```
python run_mjunction.py            # headless (server mode)
python run_mjunction.py --visible  # show Chrome while it runs
```

Scheduled runs on the server:

- `run_weekly_fleet.bat` – MSTC → MetalJunction → IREPS
- `run_daily_catalogues.bat` – IREPS catalogues

Output is appended to `server_logs.txt`. `clear_calendar.py` removes events created by the bot.

## License

Proprietary – © 2026 Rituraj Deka. All rights reserved. See [LICENSE](LICENSE).
