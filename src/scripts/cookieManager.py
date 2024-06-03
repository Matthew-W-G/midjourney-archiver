import json
import os

class CookieManager:
    @staticmethod
    def validate_cookie(cookie):
        if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
            cookie['sameSite'] = 'None'
        return cookie
    
    def load_cookies(self, context):
        cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.json')
        with open(cookies_file, 'r') as file:
            cookies = json.load(file)
            validated_cookies = [self.validate_cookie(cookie) for cookie in cookies]
            context.add_cookies(validated_cookies)