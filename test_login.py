#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8112/rest/api/v1/auth/login/"
payload = {"username": "steffen_test", "password": "TestPassword123!"}
headers = {"Content-Type": "application/json"}

resp = requests.post(url, json=payload, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Headers: {resp.headers}")
print(f"Body: {resp.text}")

if resp.status_code == 200:
    data = resp.json()
    print("Token:", data.get('key'))
else:
    print("Error details:", resp.json())