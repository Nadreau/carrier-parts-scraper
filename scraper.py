#!/usr/bin/env python3
import json
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.carrierenterprise.com"
PARTS_CATEGORY_ID = "1423187165617"
SEARCH_URL = f"{BASE_URL}/search?f=%7B%22category%22%3A%22{PARTS_CATEGORY_ID}%22%7D&inventory=all&page={{page}}&query=*"

def scrape_all_products():
    products = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page_num = 1
        while True:
            url = SEARCH_URL.format(page=page_num)
            print(f"Scraping page {page_num}...")
            page.goto(url, wait_until="networkidle")
            time.sleep(3)
            items = page.query_selector_all('[class*="collectionProduct-gridItem"]')
            if not items:
                print(f"No items found on page {page_num}, stopping")
                break
            for item in items:
                try:
                    text = item.inner_text()
                    link_el = item.query_selector('a[href*="/product/"]')
                    href = link_el.get_attribute("href") if link_el else ""
                    lines = text.split("\n")
                    name = lines[0] if lines else ""
                    item_code = ""
                    mfr_code = ""
                    for line in lines:
                        if line.startswith("Item:"):
                            item_code = line.replace("Item:", "").strip()
                        elif line.startswith("MFR:"):
                            mfr_code = line.replace("MFR:", "").strip()
                    if item_code:
                        products[item_code] = {
                            "name": name,
                            "item_code": item_code,
                            "mfr_code": mfr_code,
                            "url": href
                        }
                except Exception as e:
                    print(f"Error: {e}")
            print(f"Page {page_num}: {len(items)} items, Total: {len(products)}")
            page_num += 1
            if len(items) < 48:
                break
        browser.close()
    with open("products.json", "w") as f:
        json.dump(list(products.values()), f, indent=2)
    print(f"Done! Scraped {len(products)} products")
    return products

if __name__ == "__main__":
    scrape_all_products()
