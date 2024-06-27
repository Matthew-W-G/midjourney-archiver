import time
import requests
import random
import os
from dotenv import load_dotenv
from flask_app import db
from flask_app.models import Image
from datetime import datetime
import boto3
from pathlib import Path

load_dotenv()

class ImageScraper:
    def __init__(self):
        self.download_folder = os.getenv('DOWNLOAD_FOLDER')
        self.username = ""

    @staticmethod
    def get_image_prompt(page):
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
        
    def create_subtle_upscale(self, page):
        try:
            # Find all instances of the specified class
            elements = page.query_selector_all("div.flex-wrap.grid.grid-cols-2.w-full.shrink.flex.items-center.justify-start.gap-1\\.5.max-w-full")

            # Check if at least two elements are found
            if len(elements) > 1:
                element = elements[1]
                subtle_button = element.query_selector("button")

                if subtle_button:
                    subtle_button.click()
                    page.wait_for_timeout(1500)  # Wait 1.5 seconds

                    # Check if there is a p tag element with the text "maximum number of jobs" or "fast hours"
                    limit_reached = page.query_selector("p:text('maximum number of jobs')") or page.query_selector("p:text('fast hours')") or page.query_selector("p:text('failed to submit')") 
                    if limit_reached:
                        print("Limit reached. No more attempts.")
                        raise RuntimeError("Limit reached.")

                    updated_subtle_button = element.query_selector("button")
                    span = updated_subtle_button.query_selector("span") if updated_subtle_button else None
                    if span:
                        print('Subtle upscale successful')
                    else:
                        print("Subtle upscale failed. No span found.")
                        raise RuntimeError("Subtle upscale failed.")
                else:
                    print("No button found inside the second element.")
                    raise RuntimeError("No button found inside the second element.")
            else:
                print("Less than two elements found.")
                raise RuntimeError("Less than two elements found.")

        except Exception as e:
            print(f"An error occurred: {e}")
            raise

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

    @staticmethod
    def upload_image_s3(local_filename):
        # Get AWS credentials from environment variables
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_default_region = os.getenv('AWS_DEFAULT_REGION')

        # Create an S3 client using the credentials from environment variables
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_default_region
        )

        # S3 bucket details
        BUCKET_NAME = 'conformist-midjourney-bucket'
        BUCKET_REGION = 'us-east-2'
        try:
            s3_filename = Path(local_filename).name  # Use filename instead of stem to keep the extension
            s3_client.upload_file(local_filename, BUCKET_NAME, s3_filename)
            s3_url = f'https://{BUCKET_NAME}.s3.{BUCKET_REGION}.amazonaws.com/{s3_filename}'
            db.session.commit()
            print(f'The URL of the image will be: {s3_url}')
            return s3_url
        except Exception:
            print('Error uploading to s3 bucket')
        
    def compile_image_data(self, page, job_urls, context):
        self.username = page.query_selector('.line-clamp-1.break-all.text-sm.font-semibold').inner_text()

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
            print('quality', quality)
            print('job_url', job_url)
            if(quality.strip()=='Upscale'):
                self.create_subtle_upscale(page)
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
                s3_url = self.upload_image_s3(download_path)
            self.add_image_to_db(id, prompt_date, prompt_text, jpeg_src, download_path, quality, s3_url)
            time.sleep(random.uniform(10, 12.5))

    def get_downloads_folder(self):
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
        return self.download_folder

    def add_image_to_db(self, image_id, prompt_date, prompt_text, url, download_path, quality, s3_url):
        new_image = Image(image_id=image_id, prompt_date=prompt_date, prompt_text=prompt_text, url=url, download_path=download_path, 
                          enhancement_level=quality, s3_url=s3_url, author=self.username)
        db.session.add(new_image)
        db.session.commit()