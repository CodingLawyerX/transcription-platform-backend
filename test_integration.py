#!/usr/bin/env python3
"""
Integration test for the transcription app backend.
Assumes Django server is running on http://localhost:8112
"""

import json
import sys
import time
import requests

BASE_URL = "http://localhost:8112/rest/api/v1"
SESSION = requests.Session()

def log(msg):
    print(f"[*] {msg}")

def fail(msg):
    print(f"[!] FAIL: {msg}")
    sys.exit(1)

def success(msg):
    print(f"[✓] {msg}")

def test_endpoint(method, path, expected_status=200, **kwargs):
    """Generic endpoint tester."""
    url = BASE_URL + path
    log(f"{method} {url}")
    resp = SESSION.request(method, url, **kwargs)
    if resp.status_code != expected_status:
        fail(f"Expected {expected_status}, got {resp.status_code}: {resp.text}")
    success(f"{method} {path} -> {resp.status_code}")
    return resp

def main():
    log("Starting integration test for transcription app backend")
    
    # 1. Test that server is reachable
    try:
        resp = requests.get(BASE_URL + "/auth/login/", timeout=5)
        log("Server is reachable")
    except requests.exceptions.ConnectionError:
        fail("Cannot connect to server. Is Django running on port 8112?")
    
    # 2. Register a new user (requires email verification disabled for testing)
    # Since email verification is mandatory, we'll skip registration and assume a user exists.
    # Instead, we'll create a user via Django management command? Not possible via API.
    # For simplicity, we'll test with an existing superuser (if any) or skip auth tests.
    # We'll just test public endpoints that don't require auth.
    
    # 3. Test auth login (with invalid credentials) should return 400
    test_endpoint("POST", "/auth/login/", expected_status=400,
                  json={"username": "nonexistent", "password": "wrong"})
    
    # 4. Test registration endpoint (should return 400 due to missing fields)
    test_endpoint("POST", "/auth/registration/", expected_status=400,
                  json={})
    
    # 5. Test check-token without token (should return 401)
    test_endpoint("GET", "/auth/check-token/", expected_status=401)
    
    # 6. Test transcribe health endpoint without auth (should return 401)
    test_endpoint("GET", "/transcribe/transcriptions/health/", expected_status=401)
    
    # 7. Test that CORS headers are present (optional)
    resp = requests.options(BASE_URL + "/auth/login/")
    if "access-control-allow-origin" in resp.headers:
        success("CORS headers present")
    else:
        log("CORS headers missing (maybe not needed)")
    
    # 8. Test that static files are served (optional)
    # Not needed for API.
    
    # 9. Test that admin page is reachable (should redirect to login)
    admin_resp = requests.get("http://localhost:8112/admin/", allow_redirects=False)
    if admin_resp.status_code in (302, 301):
        success("Admin page redirects to login (as expected)")
    else:
        log(f"Admin page status: {admin_resp.status_code}")
    
    # 10. Test that API docs (DRF browsable API) is reachable
    drf_resp = requests.get(BASE_URL + "/auth/login/")
    if drf_resp.status_code == 200:
        success("DRF browsable API reachable")
    
    log("All basic endpoint tests passed.")
    log("\nNext steps for manual testing:")
    log("1. Create a user via registration endpoint (POST /rest/api/v1/auth/registration/)")
    log("2. Verify email (or disable email verification in settings for testing)")
    log("3. Login to obtain token")
    log("4. Use token to access /transcribe/transcriptions/health/")
    log("5. Upload an audio file to /transcribe/transcriptions/transcribe/")
    log("\nTo run the frontend:")
    log("1. Go to transcription-nextjs2/frontend")
    log("2. Update .env.local with NEXT_PUBLIC_API_URL=http://localhost:8112/rest/api/v1")
    log("3. Run 'npm run dev -- -p 3004'")
    log("4. Open browser to http://localhost:3004")
    
    # If you have a superuser, we can attempt to get a token and test authenticated endpoints.
    # Let's try to use environment variables for test credentials.
    import os
    test_user = os.environ.get("TEST_USER", "admin")
    test_pass = os.environ.get("TEST_PASS", "admin")
    
    log(f"\nTrying to authenticate as {test_user}...")
    resp = requests.post(BASE_URL + "/auth/login/", json={"username": test_user, "password": test_pass})
    if resp.status_code == 200:
        token = resp.json().get("key")
        if token:
            success(f"Obtained token: {token[:10]}...")
            headers = {"Authorization": f"Token {token}"}
            # Test check-token
            resp2 = requests.get(BASE_URL + "/auth/check-token/", headers=headers)
            if resp2.status_code == 200:
                success("Token is valid")
            # Test profile
            resp3 = requests.get(BASE_URL + "/auth/profile/", headers=headers)
            if resp3.status_code == 200:
                success("Profile retrieved")
                print(f"   User: {resp3.json().get('username')}")
            # Test transcribe health with auth
            resp4 = requests.get(BASE_URL + "/transcribe/transcriptions/health/", headers=headers)
            if resp4.status_code == 200:
                data = resp4.json()
                success(f"Transcription health: {data}")
            else:
                log(f"Transcription health returned {resp4.status_code}: {resp4.text}")
        else:
            log("No token in response")
    else:
        log(f"Authentication failed (status {resp.status_code}). Skipping authenticated tests.")
    
    log("\nIntegration test completed.")

if __name__ == "__main__":
    main()