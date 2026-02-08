#!/usr/bin/env python3
import requests
import json
import sys

BASE = "http://localhost:8112/rest/api/v1"

def test_registration():
    # Generate a unique username
    import random
    username = f"testuser{random.randint(1000,9999)}"
    email = f"{username}@example.com"
    password = "Testpass123!"
    
    data = {
        "username": username,
        "email": email,
        "password1": password,
        "password2": password,
    }
    
    print(f"Attempting registration for {username}...")
    resp = requests.post(f"{BASE}/auth/registration/", json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    if resp.status_code in (200, 201, 204):
        print("Registration successful")
        # Try to login
        login_resp = requests.post(f"{BASE}/auth/login/", json={"username": username, "password": password})
        print(f"Login status: {login_resp.status_code}")
        if login_resp.status_code == 200:
            token = login_resp.json().get("key")
            print(f"Token obtained: {token[:10]}...")
            return token
        else:
            print("Login failed")
    else:
        print("Registration failed")
    return None

if __name__ == "__main__":
    test_registration()