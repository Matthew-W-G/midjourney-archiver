from playwright.sync_api import sync_playwright
import json
import pandas as pd
import os
import requests
import json

def load_ids():
    mj_folder = os.path.join(os.path.expanduser('~'), 'Desktop', 'midjourney_archive')
    ids_file = os.path.join(mj_folder, 'ids.json')
    if(os.path.exists(ids_file)):
        with open(ids_file, 'r') as file:
            if(file.read(1)):
                return set(json.load(file))
            else:
                return set()
    else:
        with open(ids_file, 'a'):
            return set()

seen_ids = load_ids()

def validate_cookie(cookie):
    if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
        cookie['sameSite'] = 'None'
    return cookie

def load_cookies(context, cookies_file):
    with open(cookies_file, 'r') as file:
        cookies = json.load(file)
        validated_cookies = [validate_cookie(cookie) for cookie in cookies]
        context.add_cookies(validated_cookies)

def fetch_archive_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        # Load cookies to bypass login
        load_cookies(context, 'cookies.json')
        
        page = context.new_page()
        page.goto('https://www.midjourney.com/archive')
        
        # Wait for Cloudflare challenge to complete (if any)
        page.wait_for_timeout(1000)  # Wait 1 second for the challenge to complete
        
        print("Reached MidJourney archive page. Extracting images and information...")
        
        # Extract images and associated information
        images = page.query_selector_all('a')

        job_urls = []
        for img in images:
            href = img.get_attribute('href')
            if href and href.startswith('/jobs/'):
                job_urls.append(href)

        df = compile_image_data(page, job_urls, context)
        browser.close()
    return df

def get_downloads_folder():
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    folder_path = os.path.join(desktop_path, 'midjourney_archive', 'images')
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path
        
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

def compile_image_data(page, job_urls, context):
    image_df = pd.DataFrame(columns=['id','prompt','url','download_path'])

    storage_folder = get_downloads_folder()
    print(f"Storage folder: {storage_folder}")
    
    # Get the cookies from the context
    cookies = context.cookies()
    cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
    
    # Get the headers from the context
    headers = page.evaluate("() => { return { 'User-Agent': navigator.userAgent } }")

    i = 0
    for job_url in job_urls:
        if(i > 10):
            break
        i += 1
        parts = job_url.split('/')
        id = parts[2].split('?')[0]
        print(id)
        global seen_ids
        if(id in seen_ids):
            continue
        else:
            seen_ids.add(id)

        image_url = 'https://www.midjourney.com' + job_url
        page.goto(image_url)
        page.wait_for_load_state('networkidle')
        elements = page.query_selector_all('p.block, span.block')
        upscaled = False
        for element in elements:
            text = element.inner_text().strip()
            if text == 'Upscale':
                upscaled = True
        if not upscaled:
            continue

        lightbox_prompt_div = page.query_selector('div#lightboxPrompt')
        prompt_text_element = lightbox_prompt_div.query_selector('p')
        prompt_text = prompt_text_element.inner_text()

        jpeg_element = page.query_selector('img[src$=".jpeg"]')
        jpeg_src = None
        if jpeg_element:
            jpeg_src = jpeg_element.get_attribute('src')

        if jpeg_src:
            img_path = os.path.join(storage_folder, f'{id}.jpeg')
            print(f"Saving image to: {img_path}")
            download_path = download_image(jpeg_src, img_path, headers, cookies_dict)

        new_row = {'id': id, 'prompt': prompt_text, 'url': image_url, 'download_path': download_path}
        image_df = pd.concat([image_df, pd.DataFrame([new_row])], ignore_index=True)
    
    return image_df

def save_ids():
    mj_folder = os.path.join(os.path.expanduser('~'), 'Desktop', 'midjourney_archive')
    ids_file = os.path.join(mj_folder, 'ids.json')
    with open(ids_file, 'w') as file:
        json.dump(list(seen_ids), file)

if __name__ == '__main__':
    mj_folder = os.path.join(os.path.expanduser('~'), 'Desktop', 'midjourney_archive')
    excel_path = os.path.join(mj_folder, 'mj_archive.xlsx')
    if(os.path.exists(excel_path)):
        archive_df = pd.read_excel(excel_path)
        ids = set()
        for id in archive_df['id']:
            ids.add(id)
    else:
        archive_df = pd.DataFrame(columns=['id','prompt','url','download_path'])
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    new_rows = fetch_archive_page()
    archive_df = pd.concat([archive_df, new_rows], ignore_index=False)
    print(archive_df)
    archive_df.to_excel(excel_path)
    save_ids()