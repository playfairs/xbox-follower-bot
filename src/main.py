import os
import sys
import time
import requests
from typing import List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TOKENS_FILE

def load_tokens() -> List[str]:
    try:
        with open(TOKENS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[!] Error: {TOKENS_FILE} not found. Please run the token generator first.")
        return []
    except Exception as e:
        print(f"[!] Error reading {TOKENS_FILE}: {str(e)}")
        return []

def get_xuid(gamertag: str, token: str) -> Optional[str]:
    if not gamertag or not token:
        print("[!] Invalid gamertag or token provided.")
        return None
        
    headers = {
        "Authorization": f"XBL3.0 x={token}",
        "x-xbl-contract-version": "2",
        "Accept-Language": "en-US"
    }
    
    try:
        response = requests.get(
            f"https://profile.xboxlive.com/users/gt({gamertag})/profile/settings",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()["profileUsers"][0]["id"]
    except requests.exceptions.RequestException as e:
        print(f"[!] API request failed for {gamertag}: {str(e)}")
        return None
    except (KeyError, IndexError, ValueError) as e:
        print(f"[!] Failed to parse XUID response for {gamertag}: {str(e)}")
        return None

def follow_user(xuid: str, token: str) -> bool:
    if not xuid or not token:
        print("[!] Invalid XUID or token provided.")
        return False
        
    headers = {
        "Authorization": f"XBL3.0 x={token}",
        "x-xbl-contract-version": "2",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.post(
            f"https://social.xboxlive.com/people/xuids({xuid})/friends",
            headers=headers,
            json={},
            timeout=10
        )
        
        if response.status_code == 204:
            return True
        else:
            print(f"[!] Follow request failed with status {response.status_code}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[!] Follow request failed: {str(e)}")
        return False

def main():
    print("Xbox Follower Bot\n")
    
    tokens = load_tokens()
    if not tokens:
        print(f"No valid tokens found in {TOKENS_FILE}")
        print("Please run the token generator first to create tokens.")
        return

    gamertag = input("Enter the Gamertag to follow: ").strip()
    if not gamertag:
        print("[!] Invalid gamertag provided.")
        return

    print(f"Found {len(tokens)} token(s). Starting follow process...\n")
    
    for idx, token in enumerate(tokens, 1):
        print(f"[{idx}/{len(tokens)}] Processing token...")
        
        if idx > 1:
            time.sleep(2)
            
        xuid = get_xuid(gamertag, token)
        if xuid:
            if follow_user(xuid, token):
                print(f"✓ Successfully followed {gamertag} with token {idx}")
            else:
                print(f"✗ Failed to follow {gamertag} with token {idx}")
        else:
            print(f"[!] Could not resolve XUID for {gamertag} with token {idx}")
        
        print()

if __name__ == "__main__":
    main()
