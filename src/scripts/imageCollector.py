from playwright.sync_api import sync_playwright
import pandas as pd
from flask_app import db
from flask_app.models import Image
import time
from datetime import datetime
from cookieManager import CookieManager
from imageScraper import ImageScraper
import os

class ImageCollector:
    def __init__(self, limit):
        self.limit = limit
        self.seen_ids = self.get_seen_ids()

    def get_seen_ids(self):
        id_set = set()
        ids = db.session.query(Image.image_id).all()
        for id in ids:
            id_set.add(id[0])
        return id_set

    def filter_upscale_only(self, page):
        try:
            # Check if the filters dropdown is already open
            filters_open = page.is_visible('div.flex.flex-col.gap-4.border-t.border-light-50.dark\\:border-dark-800.p-3.empty\\:hidden.overflow-auto.microScrollbar')

            if not filters_open:
                # Click the Filters button to expand the filters menu
                page.click('button:has-text("Filters")')
                print("Clicked Filters button.")
                time.sleep(1)  # Wait for the filters menu to expand

            # Wait for the Upscales button to be visible and click it
            page.wait_for_selector('button:has-text("Upscales")', state='visible', timeout=60000)
            page.click('button:has-text("Upscales")')
            print("Clicked Upscales button.")
            time.sleep(1)  # Wait for the page to update

        except Exception as e:
            print(f"Error clicking filter buttons: {e}")
            return []

    def make_images_small(self, page):
        try:
            page.click('button:has-text("View Options")')
            print("Clicked Options button.")
            time.sleep(1)  # Wait for the options menu to expand

            # Wait for the Upscales button to be visible and click it
            page.wait_for_selector('button:has-text("Small")', state='visible', timeout=60000)
            page.click('button:has-text("Small")')
            print("Clicked Upscales button.")
            time.sleep(1)  # Wait for the page to update

        except Exception as e:
            print(f"Error clicking small buttons: {e}")
            return []
        
    def launch_archive_page(self):
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    permissions=['clipboard-read', 'clipboard-write'],
                    ignore_https_errors=True
                )

                cookie_manager = CookieManager()
                cookies_file_path = os.path.join(os.path.dirname(__file__), 'cookies.json')

                # Always filter and add only the desired cookies
                cookie_manager.load_cookies(context)
                
                page = context.new_page()
                page.goto('https://www.midjourney.com/archive')
                page.wait_for_timeout(4000)

                if not os.path.exists(cookies_file_path):
                    input("Complete the login process and press Enter...")
                    # Save cookies after initial login
                    cookie_manager.save_cookies(context)
                    # Reload the filtered cookies to ensure only desired cookies are used
                    context.clear_cookies()
                    cookie_manager.load_cookies(context)
                
                page = context.new_page()
                page.goto('https://www.midjourney.com/archive')
                page.wait_for_timeout(4000)

                print("Reached MidJourney archive page. Extracting images and information...")
                self.filter_upscale_only(page)
                self.make_images_small(page)

                job_urls = self.get_all_new_jobs(page)
                image_scraper = ImageScraper(self.limit)
                image_scraper.compile_image_data(page, job_urls, context)
                browser.close()
    
    def get_all_new_jobs(self, page):  
        new_jobs_urls = []

        page.wait_for_selector('#pageScroll')

        # Click on the first child of the third element inside the scrollable container
        page.click('#pageScroll > :nth-child(3) > :first-child')
        print('clicked')

        # Perform scrolling to load more jobs
        while True:
            images = page.query_selector_all('a')
            for img in images:
                href = img.get_attribute('href')
                if href and href.startswith('/jobs/'):
                    parts = href.split('/')
                    id = parts[2].split('?')[0]
                    if(id in self.seen_ids):
                        return new_jobs_urls
                    new_jobs_urls.append(href)


            # Get the scrollable container's current scroll height, client height, and scroll top values
            scroll_height = page.evaluate('document.querySelector("#pageScroll").scrollHeight')
            client_height = page.evaluate('document.querySelector("#pageScroll").clientHeight')
            scroll_top = page.evaluate('document.querySelector("#pageScroll").scrollTop')
            
            # Check if the bottom of the container has been reached
            if scroll_top + client_height >= scroll_height:
                break

            # Scroll down
            page.keyboard.press('ArrowDown')
            time.sleep(.005)
        seen = set()
        unique_urls = [x for x in new_jobs_urls if not (x in seen or seen.add(x))]
        return unique_urls