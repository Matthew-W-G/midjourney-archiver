import time
import requests
import random
import os
from dotenv import load_dotenv
from flask_app import db
from flask_app.models import Image
from datetime import datetime

load_dotenv()

class ImageScraper:
    def __init__(self):
        self.download_folder = os.getenv('DOWNLOAD_FOLDER')


    @staticmethod
    def get_image_prompt( page):
        # Click the options button to open the submenu
        page.click('button[title="Options"]')

        try:
            page.wait_for_selector('span:has-text("Copy")', timeout=10000)
            page.click('span:has-text("Copy")')
            page.wait_for_selector('span:has-text("Prompt")', timeout=10000)
            page.click('span:has-text("Prompt")')

        except Exception as e:
            print("Failed to find or click 'Copy' button:", e)

        return page.evaluate('navigator.clipboard.readText()')
    
    @staticmethod
    def get_image_date(page):
        page.wait_for_selector('.absolute.flex.flex-col.gap-2')
        # Extract the date from the container
        date_element = page.query_selector('.absolute.flex.flex-col.gap-2 .select-none.min-w-0.gap-3.flex.items-baseline span[title]')
        if date_element:
            date_str = date_element.get_attribute('title')
            # Manually add the current year to the date string
            current_year = datetime.now().year
            date_str_with_year = f"{date_str} {current_year}"
            
            # Convert the string to a datetime object
            date_obj = datetime.strptime(date_str_with_year, os.getenv('DATE_FORMAT'))
            print(f"Converted date object: {date_obj}")
            return date_obj
        else:
            print("Date element not found")
            return None
        
    def create_subtle_upscale(self, page, first_try):
        # Find all instances of the specified class
        elements = page.query_selector_all("div.flex-wrap.grid.grid-cols-2.w-full.shrink.flex.items-center.justify-start.gap-1\\.5.max-w-full")

        # Check if at least two elements are found
        if len(elements) > 1:
            # Select the second element
            element = elements[1]

            # Attempt to click the first button inside the second element
            first_button = element.query_selector("button")
            
            if first_button:
                try:
                    first_button.click()
                    print("First button inside the second element was clicked.")
                    
                    # Wait for 1 second to see if the indicator remains
                    page.wait_for_timeout(1000)  # Wait 1 second

                    # Check if the span with the number 1 is still present
                    indicator = first_button.query_selector("span.absolute")
                    if indicator and len(indicator.inner_text().strip()) >= 1:
                        print("Image generation was successful. Indicator is still present.")
                        return True  # Indicate success
                    elif(first_try):
                        first_try = False
                        page.wait_for_timeout(10000)  # Wait 10 seconds
                        self.create_subtle_upscale(page, False)
                    else:
                        print("Limit reached.")
                        raise RuntimeError("Limit reached.")

                except Exception as e:
                    print(f"Failed to click the first button: {e}")
                    raise
            else:
                print("No button found inside the second element.")
                raise RuntimeError("No button found inside the second element.")
        else:
            print("Less than two elements found.")
            raise RuntimeError("Less than two elements found.")

    @staticmethod
    def get_enhancement_level(page):
        element = page.query_selector_all("span.block.relative.truncate")
        if element:
            text_content = element[0].inner_text()
            return text_content
        return "No matching element found"
        
    @staticmethod
    def download_image(image_url, save_path, headers, cookies):
        try:
            print(f"Downloading image from: {image_url}")
            response = requests.get(image_url, headers=headers, cookies=cookies, stream=True)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"Image downloaded and saved to: {save_path}")
                return save_path
            else:
                print(f"Failed to download image from {image_url}, Status Code: {response.status_code}")
        except Exception as e:
            print(f"Error downloading image from {image_url}: {e}")
        
    def compile_image_data(self, page, job_urls, context):
        #this is important - images are added from top to bottom, but some may not be saved on that go
        #and id colleciton stops when seen_id is found. So images need to saved from the bottom up
        job_urls.reverse()

        storage_folder = self.get_downloads_folder()
        
        # Get the cookies from the context
        cookies = context.cookies()
        cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        
        # Get the headers from the context
        headers = page.evaluate("() => { return { 'User-Agent': navigator.userAgent } }")

        for job_url in job_urls:
            image_url = 'https://www.midjourney.com' + job_url
            page.goto(image_url)

            page.wait_for_load_state('networkidle')

            quality = self.get_enhancement_level(page)
            if(quality=='Upscale'):
                self.create_subtle_upscale(page, True)
            prompt_text = self.get_image_prompt(page)
            prompt_date = self.get_image_date(page)

            jpeg_element = page.query_selector('img[src$=".jpeg"]')
            jpeg_src = None
            if jpeg_element:
                jpeg_src = jpeg_element.get_attribute('src')

            parts = job_url.split('/')
            id = parts[2].split('?')[0]
            if jpeg_src:
                img_path = os.path.join(storage_folder, f'{id}.jpeg')
                print(f"Saving image to: {img_path}")
                download_path = self.download_image(jpeg_src, img_path, headers, cookies_dict)
            self.add_image_to_db(id, prompt_date, prompt_text, jpeg_src, download_path, quality)
            time.sleep(random.uniform(2, 3))

    def get_downloads_folder(self):
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
        return self.download_folder
            


    def add_image_to_db(self, image_id, prompt_date, prompt_text, url, download_path, quality):
        new_image = Image(image_id=image_id, prompt_date=prompt_date, prompt_text=prompt_text, url=url, download_path=download_path, enhancement_level=quality)
        db.session.add(new_image)
        db.session.commit()()