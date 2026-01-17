# Carrier Enterprise Parts Scraper

Scrapes all 78,000+ HVAC parts from [Carrier Enterprise Part Finder](https://www.carrierenterprise.com/part-finder).

## Features

- **Full catalog scraping** - Captures all parts with item codes, MFR codes, names, and URLs
- - **Resume capability** - Saves state every 10 pages, can resume interrupted scrapes
  - - **Change detection** - Compare scrapes to identify new/removed parts
    - - **Headless or visible** - Run with or without browser window
     
      - ## Installation
     
      - ```bash
        # Clone the repository
        git clone https://github.com/Nadreau/carrier-parts-scraper.git
        cd carrier-parts-scraper

        # Install dependencies
        pip install playwright requests

        # Install browser
        playwright install chromium
        ```

        ## Usage

        ```bash
        # Run full scrape (takes several hours for 78K+ parts)
        python scraper.py

        # Resume an interrupted scrape
        python scraper.py --resume

        # Force full re-scrape (ignore existing data)
        python scraper.py --full

        # Show browser window while scraping
        python scraper.py --visible

        # Compare last two scrapes
        python scraper.py --compare
        ```

        ## Output

        Data is saved to `data/parts_scrape_YYYY-MM-DD.json`:

        ```json
        {
          "scrape_date": "2024-01-15T10:30:00",
          "total_products": 78199,
          "products": {
            "TP-C25-1SP2": {
              "item_code": "TP-C25-1SP2",
              "mfr_code": "TP-C25-1SP2",
              "name": "TRADEPRO - Condenser Motor...",
              "url": "https://www.carrierenterprise.com/product/...",
              "first_seen": "2024-01-15T10:30:00"
            }
          }
        }
        ```

        ## Notes

        - Full scrape takes 3-5 hours depending on network speed
        - - State is saved every 10 pages to `data/scrape_state.json`
          - - Uses Playwright for reliable browser automation
            - - Respects rate limits with built-in delays
