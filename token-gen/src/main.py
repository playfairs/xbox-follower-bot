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
import random
import string
import urllib.parse

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
        """Set up Chrome WebDriver with headless mode"""
        chrome_options = Options()
        
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/local/bin/chromium",
            "/Applications/Chromium.app/Contents/MacOS/Chromium"
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_options.binary_location = path
                print(f"Found Chrome/Chromium at: {path}")
                break
        else:
            print("Warning: Chrome/Chromium not found in standard locations. Trying default...")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
            
            return True
            
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            print("\nTroubleshooting tips:")
            print("1. Make sure Chrome or Chromium is installed on your system")
            print("2. If using Chrome, install it from: https://www.google.com/chrome/")
            print("3. If using Chromium, install it via Homebrew: 'brew install --cask chromium'")
            print("4. Make sure the Chrome/Chromium binary is in your PATH or specify the full path in the script")
            return False

    def generate_random_password(self, length=12):
        """Generate a random strong password"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choice(chars) for _ in range(length))

    def create_microsoft_account(self):
        """Create a new Microsoft account and return credentials"""
        try:
            first_name = ''.join(random.choices(string.ascii_letters, k=6)).capitalize()
            last_name = ''.join(random.choices(string.ascii_letters, k=8)).capitalize()
            username = f"{first_name.lower()}{last_name.lower()}{random.randint(100, 999)}"
            email = f"{username}@outlook.com"
            password = self.generate_random_password()
            
            print(f"Creating new Microsoft account: {email}")
            
            self.driver.get("https://signup.live.com/")
            
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.ID, "liveSwitch"))
            ).click()
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "MemberName"))
            ).send_keys(username)
            self.driver.find_element(By.ID, "iSignupAction").click()
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "Password"))
            ).send_keys(password)
            self.driver.find_element(By.ID, "iSignupAction").click()
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "FirstName"))
            ).send_keys(first_name)
            self.driver.find_element(By.NAME, "LastName").send_keys(last_name)
            self.driver.find_element(By.ID, "iSignupAction").click()
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "BirthDay"))
            ).send_keys("1")
            self.driver.find_element(By.NAME, "BirthMonth").send_keys("1")
            self.driver.find_element(By.NAME, "BirthYear").send_keys("2000")
            self.driver.find_element(By.ID, "iSignupAction").click()
            
            print(f"Account created: {email}")
            return {
                'email': email,
                'password': password,
                'username': username
            }
            
        except Exception as e:
            print(f"Error creating account: {e}")
            return None

    def generate_token(self) -> bool:
        """Generate and save Xbox Live token"""
        try:
            account = self.create_microsoft_account()
            if not account:
                print("Failed to create Microsoft account")
                return False
                
            print(f"Logging in to account: {account['email']}")
            
            auth_code = self.get_auth_code(account['email'], account['password'])
            if not auth_code:
                print("Failed to get authorization code")
                return False
                
            token_data = self.get_access_token(auth_code)
            if not token_data:
                print("Failed to get access token")
                return False
                
            xbl_token = self.get_xbl_token(token_data['access_token'])
            if not xbl_token:
                print("Failed to get XBL token")
                return False
                
            xsts_token = self.get_xsts_token(xbl_token)
            if not xsts_token:
                print("Failed to get XSTS token")
                return False
                
            self.save_token(xsts_token)
            print(f"Token generated and saved successfully for {account['email']}")
            return True
            
        except Exception as e:
            print(f"Error in token generation: {e}")
            return False

    def get_auth_code(self, email: str, password: str) -> Optional[str]:
        """Get authorization code using Selenium with auto-login"""
        try:
            params = {
                'client_id': CLIENT_ID,
                'response_type': 'code',
                'approval_prompt': 'auto',
                'scope': SCOPE,
                'redirect_uri': REDIRECT_URI
            }
            auth_url = f"{AUTH_URL}?{requests.compat.urlencode(params)}"
            
            print("Getting authorization code...")
            self.driver.get(auth_url)
            
            if "login.live.com" in self.driver.current_url:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "loginfmt"))
                ).send_keys(email)
                self.driver.find_element(By.ID, "idSIButton9").click()
                
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "passwd"))
                ).send_keys(password)
                self.driver.find_element(By.ID, "idSIButton9").click()
                
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "idBtn_Back"))
                    ).click()
                except:
                    pass
            
            WebDriverWait(self.driver, 30).until(
                lambda d: "localhost:8080" in d.current_url
            )
            
            parsed_url = urllib.parse.urlparse(self.driver.current_url)
            auth_code = urllib.parse.parse_qs(parsed_url.query).get('code', [None])[0]
            
            if auth_code:
                return auth_code
                
        except Exception as e:
            print(f"Error in get_auth_code: {e}")
            
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
        """Save token to tokens.txt"""
        with open(TOKENS_FILE, 'a') as f:
            f.write(f"{token}\n")

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