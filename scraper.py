#!/usr/bin/env python3
import json
import time
import os
import sys
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from playwright.sync_api import sync_playwright

# Check for test mode
TEST_MODE = "--test" in sys.argv
TEST_EMAIL = "--test-email" in sys.argv

# Notion configuration
NOTION_API_KEY = os.environ.get('NOTION_API_KEY')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '2ed576a5c12d803a9025f73425b97c19')

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

def scrape_category(page, category_name, category_id, products, max_pages=None):
    print(f"\n{'='*50}")
    print(f"Scraping: {category_name}")
    if max_pages:
        print(f"(TEST MODE: max {max_pages} pages)")
    print(f"{'='*50}")
    page_num = 1
    category_count = 0
    consecutive_empty = 0

    while True:
        # In test mode, limit pages
        if max_pages and page_num > max_pages:
            print(f"  TEST MODE: Stopping at {max_pages} pages")
            break
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
    # In test mode, only compare with other test files
    if TEST_MODE:
        files = [f for f in os.listdir('.') if f.startswith('products_test_') and f.endswith('.json')]
    else:
        # In normal mode, exclude test files
        files = [f for f in os.listdir('.') if f.startswith('products_') and f.endswith('.json') and '_test_' not in f]
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


def generate_html_email(changes, new_count, date_str):
    """Generate a nicely formatted HTML email for new products"""
    added = changes.get('added', [])
    removed = changes.get('removed', [])
    old_count = changes.get('old_count', 0)

    # Group new products by category
    by_category = {}
    for p in added:
        cat = p.get('category', 'Unknown')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(p)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        h3 {{ color: #0066cc; margin-top: 20px; border-left: 4px solid #0066cc; padding-left: 10px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .summary-item {{ display: inline-block; margin-right: 30px; }}
        .number {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
        .label {{ color: #666; font-size: 12px; }}
        .product {{ background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 12px; margin: 10px 0; }}
        .product-name {{ font-weight: bold; color: #333; margin-bottom: 5px; }}
        .product-details {{ color: #666; font-size: 13px; }}
        .product a {{ color: #0066cc; text-decoration: none; }}
        .product a:hover {{ text-decoration: underline; }}
        .badge {{ display: inline-block; background: #28a745; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 10px; }}
        .badge-removed {{ background: #dc3545; }}
        .category-count {{ color: #666; font-size: 14px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>🔧 Carrier Enterprise Weekly Report</h1>
    <p style="color: #666;">Report generated on {date_str}</p>

    <div class="summary">
        <div class="summary-item">
            <div class="number">{new_count:,}</div>
            <div class="label">Total Products</div>
        </div>
        <div class="summary-item">
            <div class="number" style="color: #28a745;">+{len(added):,}</div>
            <div class="label">New This Week</div>
        </div>
        <div class="summary-item">
            <div class="number" style="color: #dc3545;">-{len(removed):,}</div>
            <div class="label">Removed</div>
        </div>
        <div class="summary-item">
            <div class="number">{new_count - old_count:+,}</div>
            <div class="label">Net Change</div>
        </div>
    </div>
"""

    if added:
        html += f"""
    <h2>✨ New Products Added <span class="badge">{len(added)}</span></h2>
"""
        # Show products grouped by category
        for category in sorted(by_category.keys()):
            products = by_category[category]
            html += f"""
    <h3>{category} <span class="category-count">({len(products)} new)</span></h3>
"""
            # Limit to 10 products per category in email, with "and X more" message
            display_products = products[:10]
            for p in display_products:
                html += f"""
    <div class="product">
        <div class="product-name"><a href="{p['url']}">{p['name']}</a></div>
        <div class="product-details">
            Item: <strong>{p['item_code']}</strong> | MFR: {p['mfr_code']}
        </div>
    </div>
"""
            if len(products) > 10:
                html += f"""
    <p style="color: #666; font-style: italic;">... and {len(products) - 10} more in {category}</p>
"""
    else:
        html += """
    <h2>No New Products This Week</h2>
    <p>No new products were added since the last scrape.</p>
"""

    if removed:
        html += f"""
    <h2>🗑️ Products Removed <span class="badge badge-removed">{len(removed)}</span></h2>
"""
        for p in removed[:20]:
            html += f"""
    <div class="product" style="border-color: #dc3545;">
        <div class="product-name" style="color: #dc3545;">{p['name']}</div>
        <div class="product-details">
            Item: <strong>{p['item_code']}</strong> | Category: {p['category']}
        </div>
    </div>
"""
        if len(removed) > 20:
            html += f"""
    <p style="color: #666; font-style: italic;">... and {len(removed) - 20} more removed</p>
"""

    html += """
    <div class="footer">
        <p>This report was automatically generated by the Carrier Enterprise Product Scraper.</p>
        <p>Data source: <a href="https://www.carrierenterprise.com/part-finder">carrierenterprise.com/part-finder</a></p>
    </div>
</body>
</html>
"""
    return html


def send_email_report(changes, new_count, date_str, text_report):
    """Send email report of new products"""
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASS')
    email_to = os.environ.get('EMAIL_TO', email_user)

    if not email_user or not email_pass:
        print("Email credentials not configured. Skipping email notification.")
        print("Set EMAIL_USER and EMAIL_PASS environment variables to enable email.")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔧 Carrier Enterprise Report - {len(changes.get('added', []))} New Products ({date_str})"
        msg['From'] = email_user
        msg['To'] = email_to

        # Plain text version
        text_part = MIMEText(text_report, 'plain')
        msg.attach(text_part)

        # HTML version
        html_content = generate_html_email(changes, new_count, date_str)
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Send via Gmail SMTP
        print(f"Sending email report to {email_to}...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)

        print(f"Email sent successfully to {email_to}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def add_to_notion(products, date_str):
    """Add new products to Notion database"""
    if not NOTION_API_KEY:
        print("Notion API key not configured. Skipping Notion sync.")
        print("Set NOTION_API_KEY environment variable to enable Notion integration.")
        return False

    if not products:
        print("No new products to add to Notion.")
        return True

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    success_count = 0
    fail_count = 0

    print(f"\nAdding {len(products)} new products to Notion...")

    for product in products:
        # Build the page properties matching your database schema
        page_data = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Name": {
                    "title": [
                        {"text": {"content": product.get('name', 'Unknown')[:2000]}}
                    ]
                },
                "Item Code": {
                    "rich_text": [
                        {"text": {"content": product.get('item_code', '')}}
                    ]
                },
                "MFR Code": {
                    "rich_text": [
                        {"text": {"content": product.get('mfr_code', '')}}
                    ]
                },
                "Category": {
                    "multi_select": [{"name": product.get('category', 'Unknown')}]
                },
                "URL": {
                    "url": product.get('url', '')
                },
                "Date Added": {
                    "date": {"start": date_str}
                }
            }
        }

        try:
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=page_data
            )

            if response.status_code == 200:
                success_count += 1
            else:
                fail_count += 1
                print(f"  Failed to add {product.get('item_code', 'unknown')}: {response.status_code}")
                if fail_count <= 3:  # Only show first few errors
                    print(f"    Response: {response.text[:200]}")
        except Exception as e:
            fail_count += 1
            print(f"  Error adding {product.get('item_code', 'unknown')}: {e}")

        # Small delay to avoid rate limiting
        time.sleep(0.3)

    print(f"Notion sync complete: {success_count} added, {fail_count} failed")
    return fail_count == 0


def scrape_all_products():
    products = []

    # In test mode, only scrape 2 categories with 1 page each
    if TEST_MODE:
        print("\n" + "="*50)
        print("TEST MODE ENABLED")
        print("Scraping only 2 categories with 1 page each")
        print("="*50)
        categories_to_scrape = dict(list(CATEGORIES.items())[:2])
        max_pages = 1
    else:
        categories_to_scrape = CATEGORIES
        max_pages = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for category_name, category_id in categories_to_scrape.items():
            count = scrape_category(page, category_name, category_id, products, max_pages=max_pages)
            print(f"  {category_name}: {count} products")
            with open("products.json", "w") as f:
                json.dump(products, f, indent=2)
            print(f"  Progress saved! Total so far: {len(products)}")
        browser.close()

    # Save dated file
    date_str = datetime.now().strftime("%Y-%m-%d")
    if TEST_MODE:
        dated_filename = f"products_test_{date_str}.json"
    else:
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
    if TEST_MODE:
        report_filename = f"report_test_{date_str}.txt"
    else:
        report_filename = f"report_{date_str}.txt"
    with open(report_filename, "w") as f:
        f.write(report)
    
    print(f"\n{'='*50}")
    print(f"DONE! Total products scraped: {len(products)}")
    print(f"Saved to: {dated_filename}")
    print(f"Report: {report_filename}")
    print(f"{'='*50}")
    print(report)

    # Send email notification
    send_email_report(changes, len(products), date_str, report)

    # Add new products to Notion
    if changes.get('added'):
        add_to_notion(changes['added'], date_str)

    return products

def test_email_with_fake_products():
    """Test the email functionality with simulated new products"""
    print("\n" + "="*50)
    print("EMAIL TEST MODE")
    print("Simulating new products to test email formatting")
    print("="*50 + "\n")

    date_str = datetime.now().strftime("%Y-%m-%d")

    # Load existing products if available
    if os.path.exists("products.json"):
        with open("products.json", "r") as f:
            existing_products = json.load(f)
        total_count = len(existing_products)
    else:
        existing_products = []
        total_count = 100  # Fake count

    # Create fake new products to simulate what the email would look like
    fake_new_products = [
        {
            "name": "TEST - New 3 Ton Heat Pump Unit (THIS IS A TEST)",
            "item_code": "TEST-HP-3TON",
            "mfr_code": "TEST-MFR-001",
            "url": "https://www.carrierenterprise.com/product/test1",
            "category": "Residential - Heat Pumps"
        },
        {
            "name": "TEST - New Commercial Rooftop AC 10 Ton (THIS IS A TEST)",
            "item_code": "TEST-RTU-10T",
            "mfr_code": "TEST-MFR-002",
            "url": "https://www.carrierenterprise.com/product/test2",
            "category": "Commercial - Packaged Rooftops"
        },
        {
            "name": "TEST - New Gas Furnace 80K BTU (THIS IS A TEST)",
            "item_code": "TEST-FURN-80K",
            "mfr_code": "TEST-MFR-003",
            "url": "https://www.carrierenterprise.com/product/test3",
            "category": "Residential - Gas Furnaces"
        },
    ]

    fake_removed_products = [
        {
            "name": "TEST - Discontinued Old Model (THIS IS A TEST)",
            "item_code": "TEST-OLD-001",
            "mfr_code": "TEST-OLD-MFR",
            "url": "https://www.carrierenterprise.com/product/old1",
            "category": "Residential - Air Conditioners"
        }
    ]

    # Create fake changes
    changes = {
        "added": fake_new_products,
        "removed": fake_removed_products,
        "old_count": total_count - 2
    }

    # Generate report
    report = generate_report(changes, total_count, date_str)
    print(report)

    # Send test email
    print("\nSending test email...")
    success = send_email_report(changes, total_count, date_str, report)

    if success:
        print("\n✓ Test email sent! Check your inbox.")
        print("  The email shows 3 fake 'new' products and 1 fake 'removed' product.")
    else:
        print("\n✗ Email failed. Check your EMAIL_USER and EMAIL_PASS environment variables.")

    # Test Notion integration
    print("\nTesting Notion integration...")
    notion_success = add_to_notion(fake_new_products, date_str)
    if notion_success:
        print("✓ Test products added to Notion! Check your database.")
        print("  (You can delete the test entries from Notion manually)")
    else:
        print("✗ Notion failed. Check NOTION_API_KEY and database permissions.")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Carrier Enterprise Product Scraper

Usage:
  python scraper.py              Full scrape (all categories, all pages)
  python scraper.py --test       Quick test (2 categories, 1 page each)
  python scraper.py --test-email Test email & Notion with fake products (no scraping)

Environment variables:
  EMAIL_USER        Gmail address to send from
  EMAIL_PASS        Gmail App Password (not your regular password!)
  EMAIL_TO          Recipient email (defaults to EMAIL_USER)
  NOTION_API_KEY    Notion integration secret
  NOTION_DATABASE_ID  Notion database ID (optional, has default)

Test mode creates separate files (products_test_*.json) so you can
run it multiple times to verify the comparison and email work.
""")
    elif TEST_EMAIL:
        test_email_with_fake_products()
    else:
        scrape_all_products()
