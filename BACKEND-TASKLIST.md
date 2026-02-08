Unten sind Copy/Paste-fertige Agent-Tickets.
Jeder Block ist ein einzelner Prompt für deinen Coding Agent (inkl. Dateien, konkreten Änderungen, Acceptance, Commands).
(Ohne Backups.)

**Hinweis:** Ticket 05 (Logging) und Ticket 06 (Health Check Endpoint) wurden implementiert.

⸻

Ticket 01 — Secrets Hygiene (README + .gitignore + Serializer write_only)

PROMPT FÜR CODING AGENT

Du arbeitest im Django Backend "transcription-platform/backend".

Ziel: Secrets Hygiene. Keine echten API Keys im Repo. API Keys dürfen nie in Responses auftauchen.

Änderungen:

1) README.md
- Entferne/ersetze jede echte API-Key-Zeile (z.B. VOXTRAL_API_KEY=...).
- Ersetze mit Placeholder:
  VOXTRAL_API_KEY=your_voxtral_api_key_here

2) apps/transcriptions/serializers.py
- Stelle sicher, dass im Serializer für TranscriptionSettings (TranscriptionSettingsSerializer) das Feld api_key NICHT im Response zurückkommt.
- Lösung: api_key als write_only=True via extra_kwargs in Meta.
- api_key soll weiterhin geschrieben werden können (POST/PUT/PATCH).
- setze zusätzlich required=False, allow_blank=True.

Beispiel:
extra_kwargs = {
  "api_key": {"write_only": True, "required": False, "allow_blank": True}
}

3) .gitignore
- Stelle sicher, dass env/secrets/logs nicht committet werden:
  .envs/*
  !.envs/*.example
  *.env
  .env.local
  **/credentials.json
  **/secrets.yaml
  logs/
  *.log
  /var/log/django/

Acceptance Criteria:
- Keine echten Keys mehr im README.
- Serializer liefert bei GET/Response kein api_key Feld.
- Tests/Server laufen weiterhin.

Commands:
- uv run python manage.py check
- uv run python -m pytest (falls schon vorhanden)


⸻

Ticket 02 — Rate Limiting (DRF + stricter for Transcription create)

PROMPT FÜR CODING AGENT

Ziel: Rate Limiting im DRF aktivieren + strenger Throttle für POST /rest/api/v1/transcriptions/ (create).

Änderungen:

1) config/settings/base.py
- Ergänze/patch REST_FRAMEWORK:
  DEFAULT_THROTTLE_CLASSES:
    - rest_framework.throttling.AnonRateThrottle
    - rest_framework.throttling.UserRateThrottle
  DEFAULT_THROTTLE_RATES:
    anon: "100/day"
    user: "1000/day"
    transcription: "10/hour"

Wichtig: Bestehende REST_FRAMEWORK Settings dürfen nicht überschrieben werden -> nur ergänzen/merge.

2) apps/transcriptions/views.py
- Implementiere Custom Throttle:
  from rest_framework.throttling import UserRateThrottle
  class TranscriptionRateThrottle(UserRateThrottle):
      scope = "transcription"

- Im TranscriptionViewSet:
  def get_throttles(self):
      if self.action == "create":
          return [TranscriptionRateThrottle()]
      return super().get_throttles()

Acceptance Criteria:
- Nach >10 POST Requests pro Stunde auf create: 429.
- Andere Endpoints weiter normal throttled.

Smoke Test:
for i in {1..15}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8120/rest/api/v1/transcriptions/ \
    -H "Authorization: Token YOUR_TOKEN" \
    -F "audio_file=@test.mp3"
done


⸻

Ticket 03 — Production Security Settings (HTTPS, cookies, headers, HSTS)

PROMPT FÜR CODING AGENT

Ziel: Harden production settings.

Datei: config/settings/production.py

Änderungen (nur in production.py, nicht local/base):

- Stelle sicher: DEBUG = False (falls nicht bereits).
- HTTPS:
  SECURE_SSL_REDIRECT = True
  SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

- Cookies:
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  SESSION_COOKIE_HTTPONLY = True
  CSRF_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SAMESITE = "Lax"
  CSRF_COOKIE_SAMESITE = "Lax"

- Headers:
  SECURE_CONTENT_TYPE_NOSNIFF = True
  X_FRAME_OPTIONS = "DENY"

- HSTS:
  SECURE_HSTS_SECONDS = 31536000
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_HSTS_PRELOAD = True

Acceptance Criteria:
- production settings booten ohne Error.
- curl -I https://domain liefert die erwarteten Header (mind. HSTS + X-Frame-Options + nosniff).


⸻

Ticket 04 — Production ALLOWED_HOSTS via Env

PROMPT FÜR CODING AGENT

Ziel: ALLOWED_HOSTS in production aus Env konfigurierbar.

Dateien:
- config/settings/production.py
- .envs/.production/.django.example (oder passende example Datei)

Änderungen:
1) production.py:
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["transcription.yourhost.com", "api.transcription.yourhost.com"]
)

2) production env example:
DJANGO_ALLOWED_HOSTS=transcription.yourdomain.com,api.yourdomain.com

Acceptance Criteria:
- production startet mit korrekten Hosts.
- Ohne Env greift default.


⸻

Ticket 05 — Logging (Rotating files + dev override)

PROMPT FÜR CODING AGENT

Ziel: Basic production logging + lokale override auf ./logs.

Dateien:
- config/settings/base.py
- config/settings/local.py
- .gitignore

Änderungen:

1) base.py:
- LOGGING dict hinzufügen:
  - formatter verbose
  - handlers:
    console (INFO)
    file RotatingFileHandler -> /var/log/django/app.log
    error_file RotatingFileHandler -> /var/log/django/error.log (level ERROR)
    celery_file RotatingFileHandler -> /var/log/django/celery.log
  - loggers:
    django -> console,file,error_file
    django.request -> error_file
    apps -> console,file
    celery -> console,celery_file
  - root -> console

Rotation:
- maxBytes = 15MB
- backupCount = 10

2) local.py:
- Überschreibe die file paths auf BASE_DIR/logs/*.log (app/error/celery)
- Stelle sicher, dass logs/ directory existiert (os.makedirs).

3) .gitignore ergänzen:
logs/
*.log
/var/log/django/

Acceptance Criteria:
- Local schreibt logs nach backend/logs/.
- Kein Crash wegen fehlendem logs folder.


⸻

Ticket 06 — Health Check Endpoint (DB/Redis/Storage/Celery)

PROMPT FÜR CODING AGENT

Ziel: Health endpoint für Infrastruktur.

Dateien:
- apps/transcriptions/health.py (NEU)
- apps/transcriptions/views.py
- apps/transcriptions/api_urls.py

Implementierung:

1) apps/transcriptions/health.py neu:
- check_database(): connection.ensure_connection()
- check_redis(): cache set/get
- check_storage(): default_storage.listdir("") minimal prüfen
- check_celery(): celery inspect.stats()

Alle Funktionen:
- return True/False
- log errors via logger.error(...)

2) apps/transcriptions/views.py:
- function-based view health_check:
  - @api_view(["GET"])
  - @permission_classes([AllowAny])
  - checks dict aus obigen Funktionen
  - all_healthy = all(checks.values())
  - Response JSON: {"status": "healthy"/"unhealthy", "checks": checks}
  - HTTP 200 wenn healthy sonst 503

3) apps/transcriptions/api_urls.py:
- path("health/", health_check, name="health-check")

Acceptance Criteria:
- GET /rest/api/v1/transcriptions/health/ gibt JSON mit keys: status, checks, database, redis, storage, celery
- Statuscode 200 oder 503 abhängig von all_healthy.

Smoke Test:
curl http://localhost:8120/rest/api/v1/transcriptions/health/


⸻

Ticket 07 — Test Tooling (deps + pytest.ini)

PROMPT FÜR CODING AGENT

Ziel: Pytest Setup.

Dateien:
- pyproject.toml
- pytest.ini

Änderungen:
1) pyproject.toml: optional-dependencies "test":
- pytest>=7.4
- pytest-django>=4.5
- pytest-cov>=4.1
- factory-boy>=3.3

2) pytest.ini neu:
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py *_tests.py
addopts =
  --verbose
  --strict-markers
  --tb=short
  --cov=apps
  --cov-report=term-missing
  --cov-report=html
markers =
  slow: marks tests as slow
  integration: marks tests as integration tests

Commands:
- uv sync --extra test
- uv run python -m pytest

Acceptance Criteria:
- pytest startet ohne config errors.


⸻

Ticket 08 — Auth Tests (registration/login)

PROMPT FÜR CODING AGENT

Ziel: Minimal Auth Regression Tests.

Datei:
- apps/users/tests/test_auth.py (NEU)

Implementiere Tests (pytest-django + DRF APIClient):
- test_register_user_success -> POST /rest/api/v1/auth/registration/ -> 201 + "key"
- test_register_duplicate_email -> 400
- test_login_success -> POST /rest/api/v1/auth/login/ -> 200 + "key"
- test_login_wrong_password -> 400

Hinweise:
- Verwende get_user_model() und User.objects.create_user(...)
- @pytest.mark.django_db
- Fixture api_client = APIClient()

Acceptance Criteria:
- uv run python -m pytest apps/users/tests/test_auth.py ist grün.


⸻

Ticket 09 — Transcription API Tests (create/list/isolation)

PROMPT FÜR CODING AGENT

Ziel: Kern API Tests für Transcriptions.

Datei:
- apps/transcriptions/tests/test_api.py (NEU)

Tests:
1) test_create_transcription:
- authenticated client fixture (client.force_authenticate)
- POST /rest/api/v1/transcriptions/ mit SimpleUploadedFile audio
- Erwartung: 201, status == "pending" (oder euer initialer Status), 1 Objekt in DB.

2) test_list_transcriptions:
- Erzeuge Transcription für user
- GET /rest/api/v1/transcriptions/
- Erwartung: 200, results length == 1 (oder entsprechend pagination).

3) test_cannot_access_other_users_transcription:
- other user + transcription
- GET detail als first user
- Erwartung: 404

Acceptance Criteria:
- uv run python -m pytest apps/transcriptions/tests/test_api.py grün.


⸻

Ticket 10 — Health Check Tests

PROMPT FÜR CODING AGENT

Ziel: Health Endpoint Test.

Datei:
- apps/transcriptions/tests/test_health.py (NEU)

Test:
- GET /rest/api/v1/transcriptions/health/
- Erwartung: Statuscode in [200, 503]
- Response enthält: "status", "checks", und keys in checks: "database", "redis"

Acceptance Criteria:
- uv run python -m pytest apps/transcriptions/tests/test_health.py grün.


⸻

Optional Ticket 11 — OpenAPI/Swagger (drf-spectacular)

PROMPT FÜR CODING AGENT

Ziel: Swagger UI / OpenAPI Schema.

Dateien:
- pyproject.toml (dependency drf-spectacular>=0.27)
- config/settings/base.py (INSTALLED_APPS + DEFAULT_SCHEMA_CLASS + SPECTACULAR_SETTINGS)
- config/urls.py (schema + swagger + redoc routes)

Acceptance Criteria:
- http://localhost:8120/api/docs/ lädt Swagger UI.
- /api/schema/ liefert schema.

