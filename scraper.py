#!/usr/bin/env python3
"""
Carrier Enterprise Parts Scraper - Scrapes 78K+ HVAC parts
Usage: python scraper.py [--compare|--resume|--full|--visible]
Requirements: pip install playwright requests && playwright install chromium
"""
import json, sys, time, re, argparse
from datetime import datetime
from pathlib import Path

try:
      from playwright.sync_api import sync_playwright
      HAS_PLAYWRIGHT = True
except ImportError:
      HAS_PLAYWRIGHT = False

BASE_URL = "https://www.carrierenterprise.com"
PARTS_CATEGORY_ID = "1423187165617"
SEARCH_URL = f"{BASE_URL}/search?f=%7B%22category%22%3A%22{PARTS_CATEGORY_ID}%22%7D&inventory=all&page={{page}}&query=*"
ITEMS_PER_PAGE = 48
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STATE_FILE = DATA_DIR / "scrape_state.json"

def get_scrape_filename(date=None):
      return DATA_DIR / f"parts_scrape_{(date or datetime.now()).strftime('%Y-%m-%d')}.json"

def get_latest_scrape():
      scrapes = sorted(DATA_DIR.glob("parts_scrape_*.json"), reverse=True)
      return scrapes[0] if scrapes else None

def get_previous_scrape():
      scrapes = sorted(DATA_DIR.glob("parts_scrape_*.json"), reverse=True)
      return scrapes[1] if len(scrapes) > 1 else None

class CarrierPartsScraper:
      def __init__(self, headless=True):
                self.products, self.headless, self.total_pages, self.start_page = {}, headless, 0, 1

      def load_state(self):
                if STATE_FILE.exists():
                              with open(STATE_FILE) as f: state = json.load(f)
                                            self.products = state.get('products', {})
                              self.start_page = state.get('last_page', 1) + 1
                              self.total_pages = state.get('total_pages', 0)
                              print(f"Resuming from page {self.start_page}")
                              return True
                          return False

    def save_state(self, page):
              with open(STATE_FILE, 'w') as f:
                            json.dump({'products': self.products, 'last_page': page, 'total_pages': self.total_pages}, f)

          def clear_state(self):
                    if STATE_FILE.exists(): STATE_FILE.unlink()

                def scrape(self, resume=False):
                          if not HAS_PLAYWRIGHT:
                                        print("Install: pip install playwright && playwright install chromium")
                                        sys.exit(1)
                                    if resume: self.load_state()
                                              with sync_playwright() as p:
                                                            browser = p.chromium.launch(headless=self.headless)
                                                            page = browser.new_page()
                                                            page.set_default_timeout(60000)
                                                            if self.start_page == 1:
                                                                              page.goto(SEARCH_URL.format(page=1), wait_until='networkidle')
                                                                              time.sleep(2)
                                                                              match = re.search(r'of ([\d,]+) total', page.inner_text('body'))
                                                                              if match:
                                                                                                    total = int(match.group(1).replace(',', ''))
                                                                                                    self.total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
                                                                                                    print(f"Found {total:,} parts across {self.total_pages} pages")
                                                              else: self.total_pages = 1630
                                                                            for pg in range(self.start_page, self.total_pages + 1):
                                                                                              try:
                                                                                                                    print(f"Page {pg}/{self.total_pages} ({len(self.products):,} parts)")
                                                                                                                    if pg > 1:
                                                                                                                                              page.goto(SEARCH_URL.format(page=pg), wait_until='networkidle')
                                                                                                                                              time.sleep(1)
                                                                                                                                          prods = page.evaluate('''() => {
                                                                                                                        const p = [];
                                                                                                                        document.querySelectorAll('a[href^="/product/"]').forEach(link => {
                                                                                                                            const c = link.closest('li') || link.parentElement;
                                                                                                                            if (!c) return;
                                                                                                                            const t = c.innerText || '';
                                                                                                                            const item = t.match(/Item:\\s*([A-Z0-9\\-]{4,30})/i);
                                                                                                                            const mfr = t.match(/MFR:\\s*([A-Z0-9\\-]{4,30})/i);
                                                                                                                            const img = c.querySelector('img');
                                                                                                                            if (item) p.push({item_code: item[1].toUpperCase(), mfr_code: mfr ? mfr[1] : null,
                                                                                                                                name: img ? img.alt : '', url: 'https://www.carrierenterprise.com' + link.getAttribute('href')});
                                                                                                                        });
                                                                                                                        return p;
                                                                                                                    }''')
                                                                                                                    for prod in prods:
                                                                                                                                              if prod['item_code'] not in self.products:
                                                                                                                                                                            prod['first_seen'] = datetime.now().isoformat()
                                                                                                                                                                            self.products[prod['item_code']] = prod
                                                                                                                                                                    if pg % 10 == 0: self.save_state(pg)
                                                                                                                      except Exception as e:
                                                                                                                                            print(f"Error page {pg}: {e}")
                                                                                                                                            self.save_state(pg - 1)
                                                                                                                                    browser.close()
        self.clear_state()
        return self.products
            for pg in range(self.start_page, self.total_pages + 1):
                              try:
                                                    print(f"Page {pg}/{self.total_pages} ({len(self.products):,} parts)")
                    if pg > 1:
                                              page.goto(SEARCH_URL.format(page=pg), wait_until='networkidle')
                        time.sleep(1)
                    prods = page.evaluate('''() => {
                                            const p = [];
                                                                    document.querySelectorAll('a[href^="/product/"]').forEach(link => {
                                                                                                const c = link.closest('li') || link.parentElement;
                                                                                                                            if (!c) return;
                                                                                                                                                        const t = c.innerText || '';
                                                                                                                                                                                    const item = t.match(/Item:\\s*([A-Z0-9\\-]{4,30})/i);
                                                                                                                                                                                                                const mfr = t.match(/MFR:\\s*([A-Z0-9\\-]{4,30})/i);
                                                                                                                                                                                                                                            const img = c.querySelector('img');
                                                                                                                                                                                                                                                                        if (item) p.push({item_code: item[1].toUpperCase(), mfr_code: mfr ? mfr[1] : null,
                                                                                                                                                                                                                                                                                                        name: img ? img.alt : '', url: 'https://www.carrierenterprise.com' + link.getAttribute('href')});
                                                                                                                                                                                                                                                                                                                                });
                                                                                                                                                                                                                                                                                                                                                        return p;
                                                                                                                                                                                                                                                                                                                                                                            }''')
                    for prod in prods:
                                              if prod['item_code'] not in self.products:
                                                                            prod['first_seen'] = datetime.now().isoformat()
                            self.products[prod['item_code']] = prod
                    if pg % 10 == 0: self.save_state(pg)
except Exception as e:
                    print(f"Error page {pg}: {e}")
                    self.save_state(pg - 1)
            browser.close()
        self.clear_state()
        return self.products

    def save_scrape(self, products, filename=None):
              if not filename: filename = get_scrape_filename()
                        with open(filename, 'w') as f:
                                      json.dump({'scrape_date': datetime.now().isoformat(), 'total_products': len(products), 'products': products}, f, indent=2)
        print(f"Saved {len(products):,} products to {filename}")

def compare_scrapes(curr, prev):
      with open(curr) as f: c = json.load(f)
            with open(prev) as f: p = json.load(f)
                  ci, pi = set(c['products'].keys()), set(p['products'].keys())
    return {'new': ci - pi, 'removed': pi - ci, 'curr_total': len(ci), 'prev_total': len(pi)}

def main():
      parser = argparse.ArgumentParser(description='Carrier Enterprise Parts Scraper')
    parser.add_argument('--compare', action='store_true', help='Compare last two scrapes')
    parser.add_argument('--resume', action='store_true', help='Resume interrupted scrape')
    parser.add_argument('--full', action='store_true', help='Force full re-scrape')
    parser.add_argument('--visible', action='store_true', help='Show browser window')
    args = parser.parse_args()

    if args.compare:
              c, p = get_latest_scrape(), get_previous_scrape()
        if c and p:
                      r = compare_scrapes(c, p)
            print(f"New: {len(r['new'])}, Removed: {len(r['removed'])}")
            for code in list(r['new'])[:10]: print(f"  + {code}")
else: print("Need at least 2 scrapes to compare")
else:
        f = get_scrape_filename()
        if f.exists() and not args.full and not args.resume:
                      print(f"Scrape exists: {f}. Use --full to re-scrape or --resume to continue")
            return
        scraper = CarrierPartsScraper(headless=not args.visible)
        products = scraper.scrape(resume=args.resume)
        if products: scraper.save_scrape(products)

if __name__ == '__main__':
      main()
