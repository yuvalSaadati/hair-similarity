#!/usr/bin/env python3
"""Test the new Instagram access token"""

import requests
import os

# Your new token from the notebook
NEW_TOKEN = "EAAZAZBUfDPaikBPiBWgE7I8nZCdeTuQnT1ZC6ZBiKsL0x2ZC9xbX6RMDAdEgTSF43ZBz0bSGUgVBsXZB0MyPdxSfOKtxTZCdik82L2ctcVldVJTUtZBBhAVEvvujOPVDq8XuAtW9XsLJPqydM6UBDFNtsYjzqYe9O0ZAgeaYgYGYOZB5pWSZCJxUVEYncwdtIZBGZCR0kBQsYyVyRrtnGGJuoF3IAwqttEj1vvfcixC6QZDZD"
IG_USER_ID = "17841476730204065"

def test_instagram_api():
    """Test Instagram API with new token"""
    print("Testing Instagram API with new token...")
    
    # Test 1: Basic user info
    print("\n1. Testing basic user info...")
    try:
        url = f"https://graph.instagram.com/v18.0/{IG_USER_ID}"
        params = {
            "fields": "id,username",
            "access_token": NEW_TOKEN
        }
        
        response = requests.get(url, params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ User info: {data}")
        else:
            print(f"   ❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False
    
    # Test 2: Business discovery (what we use for creator profiles)
    print("\n2. Testing business discovery...")
    try:
        username = "dror_natan_hairartist"
        url = f"https://graph.instagram.com/v18.0/{IG_USER_ID}"
        params = {
            "fields": f"business_discovery.username({username}){{profile_picture_url,biography}}",
            "access_token": NEW_TOKEN
        }
        
        response = requests.get(url, params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Business discovery: {data}")
        else:
            print(f"   ❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False
    
    # Test 3: Media discovery
    print("\n3. Testing media discovery...")
    try:
        username = "dror_natan_hairartist"
        url = f"https://graph.instagram.com/v18.0/{IG_USER_ID}"
        params = {
            "fields": f"business_discovery.username({username}){{media{{id,media_type,media_url,permalink,caption}}}}",
            "access_token": NEW_TOKEN
        }
        
        response = requests.get(url, params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Media discovery: Found {len(data['business_discovery']['media']['data'])} posts")
        else:
            print(f"   ❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False
    
    print("\n✅ All Instagram API tests passed!")
    return True

if __name__ == "__main__":
    success = test_instagram_api()
    
    if success:
        print("\n" + "="*50)
        print("NEXT STEPS:")
        print("="*50)
        print("1. Create a .env file with your new token:")
        print("   IG_ACCESS_TOKEN=EAAZAZBUfDPaikBPiBWgE7I8nZCdeTuQnT1ZC6ZBiKsL0x2ZC9xbX6RMDAdEgTSF43ZBz0bSGUgVBsXZB0MyPdxSfOKtxTZCdik82L2ctcVldVJTUtZBBhAVEvvujOPVDq8XuAtW9XsLJPqydM6UBDFNtsYjzqYe9O0ZAgeaYgYGYOZB5pWSZCJxUVEYncwdtIZBGZCR0kBQsYyVyRrtnGGJuoF3IAwqttEj1vvfcixC6QZDZD")
        print("   IG_APP_ID=1827740257839657")
        print("   IG_APP_SECRET=169b680e4ec2c3813a62415414c5a2f4")
        print("   IG_USER_ID=17841476730204065")
        print("2. Restart your FastAPI server")
        print("3. Test creator registration with Instagram integration")
    else:
        print("\n❌ Instagram API tests failed. Check your token.")
