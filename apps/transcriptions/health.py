"""
Health check functions for infrastructure components.
"""
import logging
from django.db import connection
from django.core.cache import cache
from django.core.files.storage import default_storage
from celery import current_app

logger = logging.getLogger(__name__)


def check_database() -> bool:
    """Check database connectivity."""
    try:
        connection.ensure_connection()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def check_redis() -> bool:
    """Check Redis cache connectivity."""
    try:
        # Simple set/get to verify Redis works
        test_key = "health_check_test"
        test_value = "ok"
        cache.set(test_key, test_value, timeout=1)
        retrieved = cache.get(test_key)
        return retrieved == test_value
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


def check_storage() -> bool:
    """Check storage backend (MinIO/S3 or local)."""
    try:
        # Try to list root directory (should not raise)
        default_storage.listdir("")
        return True
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return False


def check_celery() -> bool:
    """Check Celery worker availability."""
    try:
        # Inspect active workers
        inspector = current_app.control.inspect()
        stats = inspector.stats()
        # If stats is None, no workers are connected
        if stats is None:
            logger.warning("Celery health check: no workers connected")
            return False
        # At least one worker should be present
        return len(stats) > 0
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return False