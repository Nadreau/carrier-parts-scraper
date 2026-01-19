#!/usr/bin/env python3
import json
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

    # Send email notification
    send_email_report(changes, len(products), date_str, report)

    return products

if __name__ == "__main__":
    scrape_all_products()
