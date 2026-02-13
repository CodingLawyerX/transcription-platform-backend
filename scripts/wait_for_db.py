import os
import time

import psycopg


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.")
        return 1

    timeout_seconds = int(os.environ.get("DB_WAIT_TIMEOUT_SECONDS", "60"))
    interval_seconds = int(os.environ.get("DB_WAIT_INTERVAL_SECONDS", "2"))
    deadline = time.time() + timeout_seconds
    attempt = 0

    while True:
        attempt += 1
        try:
            with psycopg.connect(database_url, connect_timeout=5):
                print("Database is available.")
                return 0
        except Exception as exc:
            if time.time() >= deadline:
                print(f"Database not available after {timeout_seconds}s: {exc}")
                return 1
            print(f"Database not ready (attempt {attempt}): {exc}")
            time.sleep(interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
