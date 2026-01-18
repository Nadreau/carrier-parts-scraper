#!/usr/bin/env python3
import json
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.carrierenterprise.com"

# Residential Equipment subcategories (from left sidebar)
SUBCATEGORIES = {
    "Air Conditioners": "1423187165527",
    "Boilers": "1423187165556",
    "Evaporator Coils": "1423187165541",
    "Fan Coils": "1423187165536",
    "Gas Furnaces": "1423187165547",
    "Generators": "1436905904712",
    "Geothermal": "1423187165567",
    "Heat Pumps": "1423187165532",
    "Oil Furnaces": "1423187165551",
    "Residential Accessories": "1457831480171091",
    "Small Packaged": "1423187165561",
    "Wall Furnaces": "152796032574834",
    "Water Heaters": "1401359791160",
}

def scrape_category(page, category_name, category_id, products):
    """Scrape a single category"""
    print(f"\n{'='*50}")
    print(f"Scraping: {category_name}")
    print(f"{'='*50}")

    page_num = 1
    category_count = 0

    while True:
        url = f"{BASE_URL}/search?f=%7B%22category%22%3A%22{category_id}%22%7D&inventory=all&page={page_num}&pageSize=48&query=*"
        print(f"  Page {page_num}...")

        page.goto(url, wait_until="networkidle")

        try:
            page.wait_for_selector('[class*="listItem"]', timeout=15000)
        except:
            pass

        # Scroll to load all items
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(2)

        items = page.query_selector_all('[class*="listItem"]')

        if not items:
            print(f"  No items found, done with {category_name}")
            break

        for item in items:
            try:
                text = item.inner_text()
                link_el = item.query_selector('a[href*="/product/"]')
                href = link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = BASE_URL + href
                lines = text.split("\n")
                name = lines[0] if lines else ""
                item_code = ""
                mfr_code = ""
                for line in lines:
                    if line.startswith("Item:"):
                        item_code = line.replace("Item:", "").strip()
                    elif line.startswith("MFR:"):
                        mfr_code = line.replace("MFR:", "").strip()
                if item_code and item_code not in products:
                    products[item_code] = {
                        "name": name,
                        "item_code": item_code,
                        "mfr_code": mfr_code,
                        "url": href,
                        "category": category_name
                    }
                    category_count += 1
            except Exception as e:
                print(f"  Error: {e}")

        print(f"  Page {page_num}: {len(items)} items, Category total: {category_count}")

        # Check for next page
        next_btn = page.query_selector('a:has-text("Next")')
        if not next_btn:
            break
        page_num += 1

    return category_count

def scrape_all_products():
    products = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for category_name, category_id in SUBCATEGORIES.items():
            count = scrape_category(page, category_name, category_id, products)
            print(f"  {category_name}: {count} products")

            # Save after each category
            with open("products.json", "w") as f:
                json.dump(list(products.values()), f, indent=2)
            print(f"  Progress saved! Total so far: {len(products)}")

        browser.close()

    print(f"\n{'='*50}")
    print(f"DONE! Total products scraped: {len(products)}")
    print(f"{'='*50}")
    return products

if __name__ == "__main__":
    scrape_all_products()
