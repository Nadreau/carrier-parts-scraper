#!/usr/bin/env python3
import json
import time
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.carrierenterprise.com"

CATEGORIES = {
    "Residential - Air Conditioners": "1423187165527",
    "Residential - Boilers": "1423187165556",
    "Residential - Evaporator Coils": "1423187165541",
    "Residential - Fan Coils": "1423187165536",
    "Residential - Gas Furnaces": "1423187165547",
    "Residential - Generators": "1436905904712",
    "Residential - Geothermal": "1423187165567",
    "Residential - Heat Pumps": "1423187165532",
    "Residential - Oil Furnaces": "1423187165551",
    "Residential - Residential Accessories": "1457831480171091",
    "Residential - Small Packaged": "1423187165561",
    "Residential - Wall Furnaces": "152796032574834",
    "Residential - Water Heaters": "1401359791160",
    "Commercial - Commercial Accessories": "5170358485568214",
    "Commercial - Indoor Packaged": "1423187165493",
    "Commercial - Packaged Rooftops": "1423187165507",
    "Commercial - Refrigeration": "1446478621476",
    "Commercial - Split Systems": "1423187165514",
    "Commercial - Thermostats Controls Zoning": "1423187165519",
    "Commercial - VRF": "1423187165503",
}

def scrape_page(page, url, max_retries=3):
    for attempt in range(max_retries):
        page.goto(url, wait_until="networkidle")
        try:
            page.wait_for_selector('[class*="listItem"]', timeout=15000)
        except:
            pass
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(2)
        items = page.query_selector_all('[class*="listItem"]')
        if items:
            return items
        if attempt < max_retries - 1:
            print(f"    Retry {attempt + 1}/{max_retries - 1} - no items found...")
            time.sleep(3)
    return []

def scrape_category(page, category_name, category_id, products):
    print(f"\n{'='*50}")
    print(f"Scraping: {category_name}")
    print(f"{'='*50}")
    page_num = 1
    category_count = 0
    consecutive_empty = 0
    
    while True:
        url = f"{BASE_URL}/search?f=%7B%22category%22%3A%22{category_id}%22%7D&inventory=all&page={page_num}&pageSize=48&query=*"
        print(f"  Page {page_num}...")
        items = scrape_page(page, url)
        
        if not items:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                print(f"  No items found on 2 consecutive pages, done with {category_name}")
                break
            print(f"  No items on page {page_num}, trying next page...")
            page_num += 1
            continue
        
        consecutive_empty = 0
        
        for item in items:
            try:
                text = item.inner_text()
                link_el = item.query_selector('a[href*="/product/"]')
                href = link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = BASE_URL + href
                lines = text.split("\n")
                name = lines[0].strip() if lines else ""
                item_code = ""
                mfr_code = ""
                for line in lines:
                    if line.startswith("Item:"):
                        item_code = line.replace("Item:", "").strip()
                    elif line.startswith("MFR:"):
                        mfr_code = line.replace("MFR:", "").strip()
                
                if href:
                    products.append({
                        "name": name,
                        "item_code": item_code,
                        "mfr_code": mfr_code,
                        "url": href,
                        "category": category_name
                    })
                    category_count += 1
            except Exception as e:
                print(f"  Error: {e}")
        print(f"  Page {page_num}: {len(items)} items, Category total: {category_count}")
        
        next_btn = page.query_selector('a:has-text("Next")')
        if not next_btn:
            break
        page_num += 1
    return category_count

def get_previous_file(current_filename):
    """Find the most recent products file that's not the current one"""
    files = [f for f in os.listdir('.') if f.startswith('products_') and f.endswith('.json')]
    files.sort(reverse=True)
    for f in files:
        if f != current_filename:
            return f
    return None

def compare_products(old_file, new_products):
    """Compare old and new products, return changes"""
    if not old_file or not os.path.exists(old_file):
        return {"added": new_products, "removed": [], "old_count": 0}
    
    with open(old_file, 'r') as f:
        old_products = json.load(f)
    
    old_urls = {p['url'] for p in old_products}
    new_urls = {p['url'] for p in new_products}
    
    added_urls = new_urls - old_urls
    removed_urls = old_urls - new_urls
    
    added = [p for p in new_products if p['url'] in added_urls]
    removed = [p for p in old_products if p['url'] in removed_urls]
    
    return {"added": added, "removed": removed, "old_count": len(old_products)}

def generate_report(changes, new_count, date_str):
    """Generate a text report of changes"""
    report = []
    report.append("=" * 60)
    report.append(f"CARRIER ENTERPRISE SCRAPE REPORT - {date_str}")
    report.append("=" * 60)
    report.append("")
    report.append(f"Total products scraped: {new_count}")
    report.append(f"Previous count: {changes['old_count']}")
    report.append(f"Net change: {new_count - changes['old_count']:+d}")
    report.append("")
    report.append(f"NEW PRODUCTS ADDED: {len(changes['added'])}")
    report.append("-" * 40)
    for p in changes['added'][:50]:
        report.append(f"  + {p['name'][:60]}")
        report.append(f"    Item: {p['item_code']} | Category: {p['category']}")
    if len(changes['added']) > 50:
        report.append(f"  ... and {len(changes['added']) - 50} more")
    report.append("")
    report.append(f"PRODUCTS REMOVED: {len(changes['removed'])}")
    report.append("-" * 40)
    for p in changes['removed'][:50]:
        report.append(f"  - {p['name'][:60]}")
        report.append(f"    Item: {p['item_code']} | Category: {p['category']}")
    if len(changes['removed']) > 50:
        report.append(f"  ... and {len(changes['removed']) - 50} more")
    report.append("")
    report.append("=" * 60)
    return "\n".join(report)

def scrape_all_products():
    products = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for category_name, category_id in CATEGORIES.items():
            count = scrape_category(page, category_name, category_id, products)
            print(f"  {category_name}: {count} products")
            with open("products.json", "w") as f:
                json.dump(products, f, indent=2)
            print(f"  Progress saved! Total so far: {len(products)}")
        browser.close()

    # Save dated file
    date_str = datetime.now().strftime("%Y-%m-%d")
    dated_filename = f"products_{date_str}.json"
    with open(dated_filename, "w") as f:
        json.dump(products, f, indent=2)
    
    # Compare with previous run (not today's file)
    previous_file = get_previous_file(dated_filename)
    print(f"Comparing to previous file: {previous_file}")
    
    if previous_file:
        changes = compare_products(previous_file, products)
    else:
        changes = {"added": [], "removed": [], "old_count": 0}
    
    # Generate report
    report = generate_report(changes, len(products), date_str)
    report_filename = f"report_{date_str}.txt"
    with open(report_filename, "w") as f:
        f.write(report)
    
    print(f"\n{'='*50}")
    print(f"DONE! Total products scraped: {len(products)}")
    print(f"Saved to: {dated_filename}")
    print(f"Report: {report_filename}")
    print(f"{'='*50}")
    print(report)
    
    return products

if __name__ == "__main__":
    scrape_all_products()
