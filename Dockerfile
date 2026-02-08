# Use Python 3.13 slim as base
FROM python:3.13-slim

# Set work directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
    postgresql-server-dev-all \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv (without frozen to allow resolution)
RUN uv sync --no-dev

# Copy the rest of the application
COPY . .

# Collect static files (optional)
ARG SKIP_COLLECTSTATIC=1
RUN if [ "$SKIP_COLLECTSTATIC" != "1" ]; then uv run python manage.py collectstatic --noinput; fi

# Expose port
EXPOSE 8112

# Run the Django development server (for development)
# For production, use gunicorn or uwsgi
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8112"]
