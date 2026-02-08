#!/usr/bin/env python3
"""
Test SMTP email delivery by attempting to register a new user.
"""
import sys
import os
import requests
import json

BASE_URL = "http://localhost:8112/rest/api/v1"

def test_registration():
    """Register a new user and see if we get a 201 response."""
    url = f"{BASE_URL}/auth/registration/"
    # Use a random username to avoid conflicts
    import random
    import string
    random_str = ''.join(random.choices(string.ascii_lowercase, k=8))
    username = f"testuser_{random_str}"
    email = f"{username}@example.com"
    password = "TestPassword123!"
    
    data = {
        "username": username,
        "email": email,
        "password1": password,
        "password2": password,
    }
    
    print(f"Registering user: {username} ({email})")
    try:
        resp = requests.post(url, json=data, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 201:
            print("Registration succeeded (user created).")
            # Check if email verification is required
            if resp.json().get('detail') == 'Verification e-mail sent.':
                print("Email verification sent (SMTP likely working).")
            else:
                print("No verification email detail in response.")
        elif resp.status_code == 400:
            errors = resp.json()
            print(f"Errors: {errors}")
            if 'email' in errors:
                print("Email error:", errors['email'])
        else:
            print("Unexpected response.")
    except Exception as e:
        print(f"Request failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_registration()