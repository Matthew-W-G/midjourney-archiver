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

            # Wait for the Small button to be visible and click it
            page.wait_for_selector('button:has-text("Small")', state='visible', timeout=60000)
            page.click('button:has-text("Small")')
            print("Clicked Small button.")
            time.sleep(1)  # Wait for the page to update

        except Exception as e:
            print(f"Error clicking small buttons: {e}")
            return []
        
    def launch_archive_page(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
            context = browser.new_context(
                permissions=['clipboard-read', 'clipboard-write'],
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()

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
            self.make_relaxed(page)
            self.filter_upscale_only(page)
            self.make_images_small(page)

            job_urls = self.navigate_archive_page(page)
            if(job_urls):
                image_scraper = ImageScraper()
                image_scraper.compile_image_data(page, job_urls, context)
            browser.close()


    def go_to_starting_point(self, page):
        page.wait_for_selector('#pageScroll')

        # Click on the first child of the third element inside the scrollable container
        page.click('#pageScroll > :nth-child(3) > :first-child')
        print('clicked')
        # Perform scrolling to load more jobs
        while True:
            images = page.query_selector_all('a')
            images.reverse()
            for img in images:
                href = img.get_attribute('href')
                if href and href.startswith('/jobs/'):
                    parts = href.split('/')
                    id = parts[2].split('?')[0]
                    if(id in self.seen_ids):
                        return
                    else:
                        break

            # Get the scrollable container's current scroll height, client height, and scroll top values
            scroll_height = page.evaluate('document.querySelector("#pageScroll").scrollHeight')
            client_height = page.evaluate('document.querySelector("#pageScroll").clientHeight')
            scroll_top = page.evaluate('document.querySelector("#pageScroll").scrollTop')
            
            print('st', scroll_top)
            print('ch', client_height)
            print('sh', scroll_height)
            # Check if the bottom of the container has been reached
            if scroll_top + client_height >= scroll_height:
                return

            # Scroll down
            page.keyboard.press('ArrowDown')
            time.sleep(.0001)

    def make_relaxed(self, page):
        try:
            # Click the "Adjust your prompt's settings" button
            button_selector = 'button[title="Adjust your prompt\'s settings"]'
            button = page.query_selector(button_selector)
            if button:
                print("Found 'Adjust your prompt's settings' button. Clicking it.")
                button.click()
            else:
                raise RuntimeError("Adjust settings button not found.")

            # Wait for the container div to appear
            parent_div_selector = (
                'div.\\@\\[1440px\\]\\/settings\\:hidden.flex.group.flex-col.gap-3.flex-1.items-center.'
                'justify-center.rounded-md'
            )
            page.wait_for_selector(parent_div_selector, timeout=5000)
            parent_div = page.query_selector(parent_div_selector)
            if parent_div:
                print("Found parent div. Printing HTML:")
                print(parent_div.inner_html())
            else:
                raise RuntimeError("Parent div not found.")

            # Find and click the "Relax" button within the updated page context
            relax_selector = (
                'button.justify-center.min-w-12.select-none.items-center'
                '.font-semibold.text-splash.bg-splash\\/20'
            )
            relax_button = parent_div.query_selector(relax_selector)
            if relax_button:
                print("Found 'Relax' button. Clicking it.")
                relax_button.click()
                print("Relax button clicked successfully.")
            else:
                raise RuntimeError("Relax button not found inside parent div.")
            button.click()

        except Exception as e:
            print(f"Error clicking relaxed button: {e}")
            raise RuntimeError("Error occurred during clicking sequence.")

    def get_new_jobs(self, page):
        new_jobs = []
        new_ids = set()
        while True:
            images = page.query_selector_all('a')
            images.reverse()
            for img in images:
                href = img.get_attribute('href')
                if href and href.startswith('/jobs/'):
                    parts = href.split('/')
                    id = parts[2].split('?')[0]
                    if(id not in new_ids and id not in self.seen_ids):
                        new_ids.add(id)
                        new_jobs.append(href)
                    if(len(new_jobs) >= self.limit):
                        return new_jobs


            # Get the current scroll top value
            scroll_top = page.evaluate('document.querySelector("#pageScroll").scrollTop')

            # Check if the top of the container has been reached
            if scroll_top == 0:
                break

            # Scroll up
            page.keyboard.press('ArrowUp')
            time.sleep(0.1)
        return new_jobs
    
    def navigate_archive_page(self, page):  
        self.go_to_starting_point(page)
        new_jobs = self.get_new_jobs(page)
        if(len(new_jobs) > 0):
            new_jobs.reverse()
        return new_jobs
