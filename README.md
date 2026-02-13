# Simpliant App Backend

Django-basiertes Backend für die Simpliant App mit Benutzerauthentifizierung, REST-API und Workflow- bzw. Eintragsverwaltung.

## Wichtige Pfade & Deploy-Kontext (Server)

- Backend-Repo: `/srv/transcription-platform-backend.git`
- Frontend-Repo: `/srv/transcription-platform-frontend`
- Backend Docker Compose (Prod): `/srv/transcription-platform-backend.git/docker-compose.prod.yml`
- Frontend Docker Compose (Prod): `/srv/transcription-platform-frontend/docker-compose.prod.yml`
- Domains: Frontend `https://app.simpliant-ds.eu`, Backend `https://backend.simpliant-ds.eu`
- API-Base (Prod): `https://backend.simpliant-ds.eu/rest/api/v1`
- Voxtral: `https://transcribe.simpliant-ds.eu`

## Projektstruktur (nach Refactoring)

```
transcription-platform-backend.git/
├── apps/                           # Django-Apps
│   ├── users/                      # Benutzerverwaltung (Custom User Model)
│   │   ├── migrations/
│   │   ├── tests/
│   │   ├── adapters.py
│   │   ├── admin.py
│   │   ├── api_views.py            # REST-API-Endpunkte für Benutzer (flache Struktur)
│   │   ├── api_urls.py             # API-URLs der Users-App
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py          # API-Serializer (CustomRegister, CustomLogin, etc.)
│   │   ├── urls.py                 # Web-URLs (falls vorhanden)
│   │   └── views.py                # Web-Views (falls vorhanden)
│   └── transcriptions/             # Eintrags- & Workflow-Verwaltung (Modul-Name bleibt technisch)
│       ├── api_urls.py             # API-URLs für Transkriptionen
│       ├── migrations/
│       ├── models.py               # Erweitertes Transcription-Model + TranscriptionSettings
│       ├── serializers.py          # Serializer für Transcription und TranscriptionSettings
│       ├── views.py                # API-Views für Transkriptionen
│       ├── admin.py                # Erweiterte Admin-Oberfläche
│       └── ...
├── api/                            # API-Routing
│   └── urls.py                     # Haupt-API-URLs (REST/API/v1/...)
├── config/                         # Django-Konfiguration
│   ├── settings/                   # Multi‑Environment Settings
│   │   ├── base.py                 # Basis‑Settings
│   │   ├── local.py                # Lokale Entwicklung
│   │   ├── production.py           # Produktion
│   │   └── test.py                 # Test‑Umgebung
│   ├── urls.py                     # Projekt‑URLs
│   └── wsgi.py / asgi.py
├── locale/                         # Internationalisierung
├── tests/                          # Projektweite Tests
├── utility/                        # Hilfsskripte (Installation, etc.)
├── docker-compose.yml              # Local Dev (Ports: 5439, 6383, 9000, 9001, 8120 -> 8112)
├── docker-compose.prod.yml         # Production (Traefik, Gunicorn, 8112 intern)
├── Dockerfile
├── pyproject.toml                  # Abhängigkeiten & Projektmetadaten
├── uv.lock                         # Lock‑Datei für uv
└── manage.py
```

**Wichtige Änderungen nach Refactoring:**
- `users/api/`-Unterordner entfernt, `api_views.py` und `api_urls.py` direkt im App-Root.
- `core/`-Ordner gelöscht (war leer).
- `Transcription`-Model um Felder erweitert: `title`, `file_size`, `duration_seconds`, `error_message`, `model_name`, `completed_at`.
- `TranscriptionSettings`-Model hinzugefügt für benutzerspezifische Einstellungen.
- Admin-Oberfläche für beide Models optimiert.
- Serializer aktualisiert, um alle neuen Felder zu unterstützen.
- Migration `0002_alter_transcription_options_and_more` erstellt und anwendbar.
- **MinIO Integration**: S3‑kompatibler Object Storage für Audio‑Dateien hinzugefügt (Bucket `transcription-audio`).

## Technologie‑Stack

- **Django 5.2.9** – Web‑Framework
- **Django REST Framework 3.15.2** – REST‑API
- **PostgreSQL** – Hauptdatenbank (via `psycopg`)
- **Redis** – Caching, Session‑Storage & Celery Message Broker
- **MinIO** – S3‑kompatibler Object Storage für Audio‑Dateien
- **Celery** – Asynchrone Task‑Verarbeitung
- **Voxtral** – Externer Service für Audio-Workflows (voxtral-mini-latest)
- **Django‑Allauth** – Authentifizierung (Registrierung, Login, Social‑Auth)
- **dj‑rest‑auth** – REST‑API‑Auth (Token‑basierte Authentifizierung)
- **CORS headers** – Cross‑Origin‑Unterstützung für Frontend
- **Django‑Crispy‑Forms** – Formular‑Rendering
- **Django‑Debug‑Toolbar** – Entwicklungshilfe
- **drf‑spectacular** – OpenAPI‑Schema‑Generierung und Swagger‑UI
- **Gunicorn** – Produktions‑WSGI‑Server
- **Docker & Docker Compose** – Containerisierung

## Test Tooling

Das Projekt verwendet **pytest** als Test-Framework mit einer umfassenden Konfiguration für Django, Coverage und Markierungen.

### Konfiguration

- **pyproject.toml**: Enthält optional-dependencies `test` mit:
  - `pytest>=7.4`
  - `pytest-django>=4.5`
  - `pytest-cov>=4.1`
  - `factory-boy>=3.3`
- **pytest.ini**: Definiert Django-Settings, Python-Dateimuster, Optionen und Marker.

### Test-Abhängigkeiten installieren

```bash
uv sync --extra test
```

### Tests ausführen

```bash
# Alle Tests
uv run python -m pytest

# Mit Coverage-Bericht
uv run python -m pytest --cov=apps --cov-report=html

# Spezifische Test-Datei
uv run python -m pytest apps/users/tests/test_auth.py

# Marker verwenden (z.B. langsame Tests überspringen)
uv run python -m pytest -m "not slow"
```

### Verfügbare Marker

- `slow`: Markiert langsame Tests (z.B. Integration mit externen Diensten)
- `integration`: Markiert Integrationstests

### Test-Umgebung

Die Test-Umgebung (`config.settings.test`) verwendet:
- SQLite in‑memory Datenbank
- Console‑only Logging
- Deaktivierte Migrationen für problematische Apps (sites, socialaccount, account, users)
- In‑memory Celery Broker (`memory://`)
- Voxtral‑API‑Aufrufe werden nicht ausgeführt (Tasks bleiben pending)

### Test‑Dateien

- `apps/users/tests/test_auth.py` – Authentifizierungs‑Tests (Registrierung, Login)
- `apps/transcriptions/tests/test_api.py` – Transkriptions‑API‑Tests (create, list, isolation)
- `apps/transcriptions/tests/test_health.py` – Health‑Check‑Tests

## Schnellstart für Coding Agents

Wenn du in einer neuen Session an diesem Backend arbeitest, folge diesen Schritten, um den Kontext zu verstehen und das Projekt schnell zu starten.

### Wichtige Konzepte

- **API-Struktur**: Alle API-Endpunkte sind unter `/rest/api/v1/` erreichbar. Die Routing-Logik liegt in `api/urls.py`.
- **Apps**: Zwei Django-Apps: `users` (Authentifizierung) und `transcriptions` (Einträge/Workflows).
- **Models**:
  - `User` (Custom) mit `name`-Feld.
  - `Transcription` mit erweiterten Feldern (siehe Datenbank‑Models).
  - `TranscriptionSettings` (OneToOne zu User) für benutzerspezifische Einstellungen.
- **Serializer**: In `apps/*/serializers.py` definiert; enthalten alle Felder der Models.
- **Admin**: Django-Admin unter `/admin/`; beide Models sind registriert.

### Häufige Befehle

```bash
# Migrationen erstellen (nach Model-Änderungen)
uv run python manage.py makemigrations

# Migrationen anwenden
uv run python manage.py migrate

# Entwicklungsserver starten (Port 8120)
uv run python manage.py runserver 0.0.0.0:8112

# Tests ausführen
uv run python -m pytest

# Docker Compose starten (PostgreSQL, Redis, MinIO, Django)
docker compose -f docker-compose.yml up -d postgres redis minio
docker compose -f docker-compose.yml up -d django

# MinIO Bucket-Status prüfen
docker compose -f docker-compose.yml exec minio /usr/bin/mc ls myminio/transcription-audio
```

### Port-Konflikte

Wenn die Standard-Ports (5439, 6383, 9000, 9001, 8120) belegt sind, passe sie in `docker-compose.yml` an und aktualisiere die entsprechenden Umgebungsvariablen.

**Aktuelle Port-Zuordnung:**
- PostgreSQL: 5439
- Redis: 6383
- MinIO API: 9000
- MinIO Console: 9001
- Django Backend: 8120 (Host) → 8112 (Container)
- Frontend: 3005 (optional)

## Entwicklungsumgebung einrichten

### Voraussetzungen

- Python 3.13+ (empfohlen)
- uv (schneller Python‑Paketmanager)
- Docker & Docker Compose (für vollständige Umgebung)

### Lokale Installation (ohne Docker)

1. Repository klonen:
   ```bash
   git clone <repository-url>
   cd /srv/transcription-platform-backend.git
   ```

2. Virtuelle Umgebung erstellen und Abhängigkeiten installieren:
   ```bash
   uv sync
   ```

3. Environment‑Variablen setzen:
   - Für Docker/Production: `.env` im Repo-Root verwenden.
   - Für lokale Entwicklung ohne Docker: Werte in `.env` setzen und `DJANGO_READ_DOT_ENV_FILE=True` nutzen.

4. Datenbank migrieren:
   ```bash
   .venv/bin/python manage.py migrate
   ```

5. Entwicklungsserver starten:
   ```bash
   .venv/bin/python manage.py runserver
   ```

### Mit Docker Compose (empfohlen)

1. Im Projekt‑Root ausführen:
   ```bash
   cd /srv/transcription-platform-backend.git
   docker compose -f docker-compose.yml up -d --build
   ```

   Dies startet:
    - PostgreSQL auf Port 5439
    - Redis auf Port 6383
    - MinIO Object Storage auf Port 9000 (API) und 9001 (Console UI)
    - Django‑Backend auf Port 8120 (intern 8112)

2. Migrationen werden automatisch ausgeführt.

3. Das Backend ist unter `http://localhost:8120` erreichbar.
   - MinIO Console: `http://localhost:9001` (Login siehe `.env`)
   - MinIO API: `http://localhost:9000`

### Production (Traefik / backend.simpliant-ds.eu)

```bash
cd /srv/transcription-platform-backend.git
docker compose -f docker-compose.prod.yml up -d --build
```

Hinweise:
- `.env` im Repo-Root enthält die Produktionswerte (DB, Redis, MinIO, SMTP, Secrets).
- Das Backend läuft intern auf Port 8112; Traefik routet `https://backend.simpliant-ds.eu`.

## API‑Endpunkte

Die REST‑API ist unter `/rest/api/v1/` erreichbar. Die browsable API ist aktiviert.

### Authentifizierung

- `POST /rest/api/v1/auth/login/` – Token‑Login
- `POST /rest/api/v1/auth/registration/` – Benutzerregistrierung
- `POST /rest/api/v1/auth/logout/` – Logout
- `GET /rest/api/v1/auth/user/` – Aktueller Benutzer

### Benutzer

- `GET /rest/api/v1/users/` – Benutzerliste (nur Admin)
- `GET /rest/api/v1/users/{id}/` – Benutzerdetails

### Transkriptionen

- `GET /rest/api/v1/transcribe/transcriptions/` – Liste aller Transkriptionen (authentifiziert)
- `POST /rest/api/v1/transcribe/transcriptions/` – Neue Transkription erstellen
- `GET /rest/api/v1/transcribe/transcriptions/{id}/` – Transkription abrufen
- `PUT /rest/api/v1/transcribe/transcriptions/{id}/` – Transkription aktualisieren
- `DELETE /rest/api/v1/transcribe/transcriptions/{id}/` – Transkription löschen
- `POST /rest/api/v1/transcribe/transcriptions/transcribe/` – Audio-Datei direkt transkribieren (multipart/form-data)
- `GET /rest/api/v1/transcribe/transcriptions/health/` – Health-Check des Transkriptions-Backends (Voxtral)
- `GET /rest/api/v1/transcribe/transcriptions/stats/` – Statistik-Daten für den aktuellen Benutzer
- `GET /rest/api/v1/transcribe/transcriptions/timeline/` – Zeitreihendaten für Transkriptionen (letzte 30 Tage, optional `?days=...`)

### Infrastruktur

- `GET /rest/api/v1/transcribe/health/` – Health-Check der Infrastruktur (Datenbank, Redis, Storage, Celery)

### OpenAPI / Swagger

Das Projekt verwendet **drf‑spectacular** zur automatischen Generierung von OpenAPI‑Schemas und bietet eine interaktive Swagger‑UI.

#### Endpunkte

- `GET /api/schema/` – OpenAPI‑Schema (YAML oder JSON)
- `GET /api/docs/` – Swagger‑UI (interaktive Dokumentation)
- `GET /api/redoc/` – ReDoc‑UI (alternative Dokumentation)

#### Zugriff

Die Swagger‑UI ist unter `http://localhost:8120/api/docs/` (lokal) oder
`https://backend.simpliant-ds.eu/api/docs/` (prod) erreichbar. Sie listet alle API‑Endpunkte mit Beschreibungen, Parametern und Beispielen auf.

#### Konfiguration

- **INSTALLED_APPS**: `drf_spectacular` in `THIRD_PARTY_APPS`
- **REST_FRAMEWORK**: `DEFAULT_SCHEMA_CLASS = 'drf_spectacular.openapi.AutoSchema'`
- **SPECTACULAR_SETTINGS**: Definiert in `config/settings/base.py` (Titel, Version, Beschreibung, etc.)

#### Verwendung

1. Starte den Entwicklungsserver (`uv run python manage.py runserver 8120`)
2. Öffne `http://localhost:8120/api/docs/`
3. Authentifiziere dich mit einem gültigen Token (über den "Authorize"‑Button) um geschützte Endpunkte zu testen.

### Admin‑Interface

- Django‑Admin unter `/admin/` (nur für Superuser)

## Datenbank‑Models

### User (Custom)

Erweitert `AbstractUser` mit zusätzlichem Feld `name`.

### Transcription

- `user` – ForeignKey zu User
- `title` – Titel der Transkription
- `audio_file` – Upload‑Feld (Audio‑Datei)
- `file_size` – Dateigröße in Bytes
- `duration_seconds` – Audiodauer in Sekunden
- `transcribed_text` – Textfeld für Transkription
- `status` – Status (pending, processing, completed, failed)
- `error_message` – Fehlermeldung bei Status „failed“
- `language` – Sprachcode (z.B. „de“, „en“)
- `model_name` – Verwendetes KI‑Modell (z.B. „whisper‑large‑v3“)
- `created_at`, `updated_at`, `completed_at` – Zeitstempel

### TranscriptionSettings

- `user` – OneToOne‑Beziehung zu User
- `backend_url` – API‑Endpoint des Transkriptionsdienstes
- `api_key` – API‑Schlüssel (verschlüsselt)
- `default_language` – Standard‑Sprache für Transkriptionen
- `default_model` – Standard‑KI‑Modell
- `notifications_enabled` – E‑Mail‑Benachrichtigungen bei Abschluss
- `auto_delete_audio` – Audio‑Datei nach Transkription automatisch löschen
- `created_at`, `updated_at` – Zeitstempel

## Konfiguration

### Environment‑Variablen

Wichtige Variablen (siehe `.env` im Repo-Root):

- `DATABASE_URL` – PostgreSQL‑Connection‑String
- `REDIS_URL` – Redis‑Connection‑String
- `DJANGO_SECRET_KEY` – Geheimer Schlüssel
- `DJANGO_DEBUG` – Debug‑Modus (True/False)
- `CORS_ALLOWED_HOSTS` – Komma‑getrennte Liste erlaubter Origins
- `EMAIL_*` – SMTP‑E‑Mail‑Konfiguration
- `USE_S3` – S3‑Storage aktivieren (True/False)
- `AWS_ACCESS_KEY_ID` – MinIO‑Access‑Key
- `AWS_SECRET_ACCESS_KEY` – MinIO‑Secret‑Key
- `AWS_STORAGE_BUCKET_NAME` – Bucket‑Name (default: `transcription-audio`)
- `AWS_S3_ENDPOINT_URL` – MinIO‑API‑Endpoint (z.B. `http://minio:9000`)
- `AWS_S3_USE_SSL` – SSL‑Nutzung (default: `False`)

### File Storage (MinIO)

Das Projekt verwendet **MinIO** als S3‑kompatiblen Object Storage für Audio‑Dateien:

- **Bucket**: `transcription-audio` (wird automatisch erstellt)
- **Storage Backend**: `storages.backends.s3boto3.S3Boto3Storage`
- **URL‑Format**: `http://minio:9000/transcription-audio/audio/YYYY/MM/filename.mp3`
- **Lokale Entwicklung**: MinIO läuft im Docker‑Container; die Console ist unter `http://localhost:9001` erreichbar.
- **Fallback**: Wenn `USE_S3=False`, werden Dateien im lokalen `media/`‑Ordner gespeichert.

Die Konfiguration befindet sich in `config/settings/base.py` und `local.py`.

### Asynchrone Transkription (Voxtral)

#### Celery Worker

Transkriptionen werden asynchron mit Voxtral API verarbeitet:

```bash
# Celery läuft automatisch
docker compose -f docker-compose.yml ps celery

# Logs anschauen
docker compose -f docker-compose.yml logs -f celery
```

#### Voxtral Integration

- **Service**: https://transcribe.simpliant-ds.eu
- **Model**: voxtral-mini-latest
- **Max File Size**: 50 MB
- **Max Duration**: 60 minutes
- **Supported Formats**: MP3, M4A, WAV, FLAC, OGG, WebM

#### Flow

1. POST /rest/api/v1/transcribe/transcriptions/ → Status: `pending`
2. Celery Task startet
3. Status: `processing`
4. Voxtral API transkribiert (kann Minuten dauern)
5. Status: `completed` (oder `failed`)
6. Transcribed text + segments gespeichert
7. Optional: Email notification

#### Configuration

Environment Variables:
- `VOXTRAL_BACKEND_URL`: API endpoint (default: https://transcribe.simpliant-ds.eu)
- `VOXTRAL_API_KEY`: Authentication key

### Multi‑Environment Settings

- `config.settings.local` – Lokale Entwicklung
- `config.settings.production` – Produktion
- `config.settings.test` – Test‑Umgebung

Die Umgebung wird über `DJANGO_SETTINGS_MODULE` gesteuert.

## Tests ausführen

Siehe auch den Abschnitt **Test Tooling** für detaillierte Informationen.

```bash
# Alle Tests (mit pytest.ini Konfiguration)
uv run python -m pytest

# Nur Users‑Tests
uv run python -m pytest apps/users/tests/

# Mit Coverage und HTML‑Bericht
uv run python -m pytest --cov=apps --cov-report=html

# Spezifische Test‑Datei (z.B. Auth‑Tests)
uv run python -m pytest apps/users/tests/test_auth.py

# Tests mit Marker filtern (z.B. keine langsamen Tests)
uv run python -m pytest -m "not slow"
```

## Deployment

### Produktions‑Build mit Docker

1. `docker compose -f docker-compose.prod.yml up -d --build`

2. Environment‑Variablen für Produktion setzen (`.env` im Repo-Root).

### Ohne Docker

- Gunicorn als WSGI‑Server
- Nginx als Reverse‑Proxy
- Statische Dateien mit `collectstatic`
- Datenbank‑Migrationen vor dem Start

## Wichtige Hinweise

- **Email‑Verifizierung** ist auf `mandatory` gesetzt (ACCOUNT_EMAIL_VERIFICATION). In der Entwicklung kann sie über `console`‑Backend getestet werden.
- **CORS** ist für `https://app.simpliant-ds.eu` sowie lokale Frontends konfiguriert (siehe `CORS_ALLOWED_HOSTS`).
- **Redis** – Caching, Session‑Storage & Celery Message Broker
- **Celery** – Asynchrone Task‑Verarbeitung
- **Voxtral** – Externes Transkriptions-Backend (voxtral-mini-latest)
- **Django‑Admin** kann über `allauth`‑Login erzwungen werden (`DJANGO_ADMIN_FORCE_ALLAUTH`).

## Lizenz

Proprietär – Nur für interne Nutzung.
