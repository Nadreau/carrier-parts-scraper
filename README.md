# Carrier Enterprise Parts Scraper

Scrapes all HVAC parts from [Carrier Enterprise Part Finder](https://www.carrierenterprise.com/part-finder) and sends weekly email reports of new products.

## Features

- **Full catalog scraping** - Captures all parts with item codes, MFR codes, names, and URLs
- **Change detection** - Compares scrapes to identify new/removed parts
- **Email notifications** - Sends nicely formatted HTML email reports of new products
- **Weekly automation** - GitHub Actions workflow runs every Sunday
- **Progress saving** - Saves state after each category for reliability

## Installation

```bash
# Clone the repository
git clone https://github.com/Nadreau/carrier-parts-scraper.git
cd carrier-parts-scraper

# Install dependencies
pip install -r requirements.txt

# Install browser
playwright install chromium
```

## Usage

```bash
# Run scraper
python scraper.py
```

### With Email Notifications (Local)

```bash
# Set environment variables for email
export EMAIL_USER="your-email@gmail.com"
export EMAIL_PASS="your-app-password"
export EMAIL_TO="recipient@gmail.com"  # Optional, defaults to EMAIL_USER

python scraper.py
```

## Email Setup (Gmail)

To enable email notifications, you need a Gmail App Password:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification if not already enabled
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Select "Mail" and "Other (Custom name)"
5. Enter "Carrier Scraper" and click Generate
6. Copy the 16-character password (no spaces)

### GitHub Actions Setup

Add these secrets to your repository (Settings > Secrets and variables > Actions):

| Secret | Value |
|--------|-------|
| `EMAIL_USER` | `nikonadreau3.14@gmail.com` |
| `EMAIL_PASS` | Your Gmail App Password |
| `EMAIL_TO` | `nikonadreau3.14@gmail.com` (optional, defaults to EMAIL_USER) |

## Automation

The scraper runs automatically every Sunday at midnight UTC via GitHub Actions.

To manually trigger a run:
1. Go to Actions tab in your repository
2. Select "Scrape Carrier Enterprise"
3. Click "Run workflow"

## Output Files

| File | Description |
|------|-------------|
| `products.json` | Current products (always updated) |
| `products_YYYY-MM-DD.json` | Date-stamped backup |
| `report_YYYY-MM-DD.txt` | Text report of changes |

### Sample Product Data

```json
{
  "name": "2.5 Ton Up to 16 SEER2 Residential Air Conditioner",
  "item_code": "GA5SAN43000W",
  "mfr_code": "GA5SAN43000W",
  "url": "https://www.carrierenterprise.com/product/1604089113546844",
  "category": "Residential - Air Conditioners"
}
```

## Categories Scraped

**Residential (13 categories):**
Air Conditioners, Boilers, Evaporator Coils, Fan Coils, Gas Furnaces, Generators, Geothermal, Heat Pumps, Oil Furnaces, Residential Accessories, Small Packaged, Wall Furnaces, Water Heaters

**Commercial (7 categories):**
Commercial Accessories, Indoor Packaged, Packaged Rooftops, Refrigeration, Split Systems, Thermostats Controls Zoning, VRF
