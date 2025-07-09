import os
import sys
import time
import requests
from typing import List, Tuple, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TOKENS_FILE

CLIENT_ID = "000000004C12AE6F"
REDIRECT_URI = "http://localhost:8080"
SCOPE = "Xboxlive.signin Xboxlive.offline_access"
AUTH_URL = "https://login.live.com/oauth20_authorize.srf"
TOKEN_URL = "https://login.live.com/oauth20_token.srf"
XBL_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_AUTH_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"

class TokenGenerator:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.auth_code = None

    def setup_driver(self):
        """Set up Chrome WebDriver with headless option"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def get_auth_code(self) -> Optional[str]:
        """Get authorization code using Selenium"""
        params = {
            'client_id': CLIENT_ID,
            'response_type': 'code',
            'approval_prompt': 'auto',
            'scope': SCOPE,
            'redirect_uri': REDIRECT_URI
        }
        auth_url = f"{AUTH_URL}?{requests.compat.urlencode(params)}"

        try:
            self.driver.get(auth_url)
            print("\nPlease sign in to your Microsoft account in the browser...")
            
            WebDriverWait(self.driver, 300).until(
                EC.url_contains("localhost:8080")
            )
            
            url = self.driver.current_url
            parsed = requests.compat.urlparse(url)
            params = requests.compat.parse_qs(parsed.query)
            
            if 'code' in params:
                return params['code'][0]
            
        except Exception as e:
            print(f"Error during authentication: {str(e)}")
            return None

    @staticmethod
    def get_access_token(auth_code: str) -> Tuple[str, str, int]:
        """Exchange authorization code for access token"""
        data = {
            'client_id': CLIENT_ID,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'scope': SCOPE
        }
        
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data['access_token'], token_data['refresh_token'], token_data['expires_in']

    @staticmethod
    def get_xbl_token(access_token: str) -> str:
        """Get XBL token"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        data = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={access_token}"
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT"
        }
        
        response = requests.post(XBL_AUTH_URL, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()['Token']

    @staticmethod
    def get_xsts_token(xbl_token: str) -> Tuple[str, str]:
        """Get XSTS token"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        data = {
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [xbl_token]
            },
            "RelyingParty": "http://xboxlive.com",
            "TokenType": "JWT"
        }
        
        response = requests.post(XSTS_AUTH_URL, headers=headers, json=data)
        response.raise_for_status()
        
        response_data = response.json()
        return response_data['Token'], response_data['DisplayClaims']['xui'][0]['uhs']

    @staticmethod
    def save_token(token: str):
        """Save token to file"""
        os.makedirs(os.path.dirname(TOKENS_FILE), exist_ok=True)
        with open(TOKENS_FILE, "a") as f:
            f.write(f"{token}\n")
        print(f"\nToken saved to {os.path.abspath(TOKENS_FILE)}")

    def generate_token(self) -> bool:
        """Generate a single token"""
        try:
            print("\nStarting token generation...")
            
            auth_code = self.get_auth_code()
            if not auth_code:
                print("Failed to get authorization code")
                return False
                
            access_token, _, _ = self.get_access_token(auth_code)
            xbl_token = self.get_xbl_token(access_token)
            xsts_token, user_hash = self.get_xsts_token(xbl_token)
            
            xbl3_token = f"x={user_hash};{xsts_token}"
            
            self.save_token(xbl3_token)
            return True
            
        except Exception as e:
            print(f"Error generating token: {str(e)}")
            return False
        finally:
            if self.driver:
                self.driver.quit()

def main():
    print("Xbox Live Token Generator\n")
    
    try:
        num_tokens = int(input("How many tokens do you want to generate? "))
        if num_tokens < 1:
            print("Please enter a number greater than 0")
            return
    except ValueError:
        print("Please enter a valid number")
        return
    
    headless = input("Run in headless mode? (y/n, default: y): ").lower() != 'n'
    
    success_count = 0
    for i in range(num_tokens):
        print(f"\nGenerating Token {i+1}/{num_tokens}")
        generator = TokenGenerator(headless)
        generator.setup_driver()
        if generator.generate_token():
            success_count += 1
        
        if i < num_tokens - 1:
            print("\nPreparing for next token...")
            time.sleep(2)
    
    print(f"\nToken Generation Complete")
    print(f"Successfully generated {success_count} out of {num_tokens} tokens")
    print("You can now use the generated tokens with the Xbox Follower Bot.")

if __name__ == "__main__":
    main()