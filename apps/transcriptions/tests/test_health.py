import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_health_check(api_client):
    """GET /rest/api/v1/transcribe/health/ returns status 200 or 503 with expected structure."""
    url = "/rest/api/v1/transcribe/health/"
    response = api_client.get(url)
    # The endpoint returns either 200 (healthy) or 503 (unhealthy)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE)
    # Response must contain "status" and "checks"
    assert "status" in response.data
    assert "checks" in response.data
    # Checks must contain database, redis, storage, celery
    checks = response.data["checks"]
    assert "database" in checks
    assert "redis" in checks
    assert "storage" in checks
    assert "celery" in checks
    # Each check value is boolean
    for key, value in checks.items():
        assert isinstance(value, bool)
    # Status is either "healthy" or "unhealthy"
    assert response.data["status"] in ("healthy", "unhealthy")
    # Consistency: if all checks are True, status must be "healthy" and status_code 200
    # if any check is False, status must be "unhealthy" and status_code 503
    all_healthy = all(checks.values())
    if all_healthy:
        assert response.data["status"] == "healthy"
        assert response.status_code == status.HTTP_200_OK
    else:
        assert response.data["status"] == "unhealthy"
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE