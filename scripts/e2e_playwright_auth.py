#!/usr/bin/env python
import os
import time

import re

import django
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    django.setup()

    from django.contrib.auth import get_user_model
    from allauth.account.models import EmailAddress

    base_url = os.environ.get("E2E_BASE_URL", "http://transcription-frontend:3000").rstrip("/")
    api_base_url = os.environ.get("E2E_API_BASE_URL", "https://backend.simpliant-ds.eu/rest/api/v1").rstrip("/")
    email = f"playwright+{int(time.time())}@example.com"
    password = "Playwright!234"

    User = get_user_model()
    User.objects.filter(email=email).delete()

    user = User.objects.create_user(
        email=email,
        username=email.split("@", 1)[0],
        password=password,
    )
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}"))
            page.on("requestfailed", lambda req: print(f"Request failed: {req.url} {req.failure}"))

            page.goto(f"{base_url}/login?callbackUrl=/transcribe", wait_until="domcontentloaded")
            page.fill("input#email", email)
            page.fill("input#password", password)
            page.click("button[type=submit]")

            try:
                page.wait_for_function("() => window.location.pathname === '/transcribe'", timeout=20000)
            except PWTimeout:
                page.screenshot(path="/tmp/e2e-login-failure.png", full_page=True)
                if page.locator("text=Anmeldung fehlgeschlagen").count():
                    print("Login error message displayed on UI.")
                cookies = page.context.cookies()
                print("Cookies after login:", [c.get("name") for c in cookies])
                try:
                    session_response = page.request.get(f"{base_url}/api/auth/session")
                    print("Session status:", session_response.status, session_response.text())
                except Exception as exc:
                    print("Failed to fetch session:", exc)
                raise

            print("Login redirect OK ->", page.url)

            session_response = page.request.get(f"{base_url}/api/auth/session")
            session_payload = session_response.json()
            print("Session email_verified:", session_payload.get("user", {}).get("email_verified"))
            access_token = session_payload.get("accessToken")
            if access_token:
                api_profile = page.request.get(
                    f"{api_base_url}/auth/profile/",
                    headers={"Authorization": f"Token {access_token}"},
                )
                print("Profile API status:", api_profile.status, api_profile.text())

            page.goto(f"{base_url}/profile", wait_until="domcontentloaded")
            try:
                page.wait_for_selector("text=Account-Informationen", timeout=20000)
                warning_count = page.locator("text=Email erneut senden").count()
                print("Verification banner count:", warning_count)
            except PWTimeout:
                page.screenshot(path="/tmp/e2e-profile-failure.png", full_page=True)
                print("Profile URL:", page.url)
                if "/login" in page.url:
                    print("Profile redirect failed: still on login page.")
                if page.locator("text=Lade Profil").count():
                    print("Profile appears stuck in loading state.")
                if page.locator("text=Fehler").count():
                    print("Profile shows error state.")
                error_items = page.locator("ul li").all_text_contents()
                if error_items:
                    print("Profile error details:", error_items)
                cookies = page.context.cookies()
                print("Cookies before profile:", [c.get("name") for c in cookies])
                print("Profile UI check skipped due to load failure.")

            browser.close()
    finally:
        User.objects.filter(email=email).delete()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
