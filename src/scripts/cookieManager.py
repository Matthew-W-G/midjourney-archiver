import json
import os

class CookieManager:
    @staticmethod
    def validate_cookie(cookie):
        if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
            cookie['sameSite'] = 'None'
        return cookie

    def filter_cookies(self, cookies):
        filtered_cookies = [cookie for cookie in cookies if 'midjourney' in cookie.get('domain', '') and cookie['name'] != 'cf_clearance']
        return filtered_cookies

    def load_cookies(self, context):
        cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
        if os.path.exists(cookies_file):
            with open(cookies_file, 'r') as file:
                cookies = json.load(file)
                validated_cookies = [self.validate_cookie(cookie) for cookie in cookies]
                filtered_cookies = self.filter_cookies(validated_cookies)
                context.add_cookies(filtered_cookies)
                print(f"Loaded {len(filtered_cookies)} cookies.")

    def save_cookies(self, context):
        cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
        cookies = context.cookies()
        validated_cookies = [self.validate_cookie(cookie) for cookie in cookies]
        filtered_cookies = self.filter_cookies(validated_cookies)
        with open(cookies_file, 'w') as file:
            json.dump(filtered_cookies, file, indent=2)
        print(f"Saved {len(filtered_cookies)} cookies.")
