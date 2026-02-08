import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.transcriptions.models import Transcription

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    """Return an APIClient authenticated with a test user."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password123",
        name="Test User",
    )
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def other_user():
    """Create a second user for isolation tests."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="password123",
        name="Other User",
    )


@pytest.mark.django_db
class TestCreateTranscription:
    """Tests for creating a transcription via POST."""

    def test_create_transcription(self, authenticated_client):
        """POST /rest/api/v1/transcribe/transcriptions/ with audio file."""
        client, user = authenticated_client
        url = "/rest/api/v1/transcribe/transcriptions/"
        # Create a dummy audio file
        audio_file = SimpleUploadedFile(
            "test_audio.mp3",
            b"fake audio content",
            content_type="audio/mpeg"
        )
        data = {
            "title": "Test Transcription",
            "audio_file": audio_file,
            "language": "de",
            "model_name": "whisper-large-v3",
        }
        response = client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        # Check response data
        assert response.data["status"] == "pending"
        # The serializer may return username as user representation
        assert response.data["user"] == user.username
        # Verify object in DB
        transcription = Transcription.objects.get(id=response.data["id"])
        assert transcription.status == "pending"
        assert transcription.user == user
        assert transcription.title == "Test Transcription"
        # Ensure only one transcription for this user
        assert Transcription.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestListTranscriptions:
    """Tests for listing transcriptions."""

    def test_list_transcriptions(self, authenticated_client):
        """GET /rest/api/v1/transcribe/transcriptions/ returns user's transcriptions."""
        client, user = authenticated_client
        # Create a transcription for the user
        Transcription.objects.create(
            user=user,
            title="Test Transcription",
            status="pending",
            language="de",
            model_name="whisper-large-v3",
        )
        url = "/rest/api/v1/transcribe/transcriptions/"
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Expect paginated results (DRF default)
        # The response may be a dict with 'results' key if pagination is enabled
        # Let's inspect the structure
        if isinstance(response.data, dict) and "results" in response.data:
            results = response.data["results"]
        else:
            results = response.data
        assert len(results) == 1
        assert results[0]["title"] == "Test Transcription"
        assert results[0]["status"] == "pending"

    def test_list_empty(self, authenticated_client):
        """GET returns empty list when user has no transcriptions."""
        client, _ = authenticated_client
        url = "/rest/api/v1/transcribe/transcriptions/"
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        if isinstance(response.data, dict) and "results" in response.data:
            results = response.data["results"]
        else:
            results = response.data
        assert len(results) == 0


@pytest.mark.django_db
class TestTranscriptionIsolation:
    """Tests that users cannot access each other's transcriptions."""

    def test_cannot_access_other_users_transcription(
        self, authenticated_client, other_user
    ):
        """GET detail of other user's transcription returns 404."""
        client, user = authenticated_client
        # Create a transcription belonging to other_user
        transcription = Transcription.objects.create(
            user=other_user,
            title="Other's Transcription",
            status="pending",
        )
        url = f"/rest/api/v1/transcribe/transcriptions/{transcription.id}/"
        response = client.get(url)
        # Expect 404 because the transcription is not owned by the authenticated user
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_list_other_users_transcriptions(
        self, authenticated_client, other_user
    ):
        """GET list only shows own transcriptions."""
        client, user = authenticated_client
        # Create transcription for other user
        Transcription.objects.create(
            user=other_user,
            title="Other's Transcription",
            status="pending",
        )
        # Create transcription for authenticated user
        Transcription.objects.create(
            user=user,
            title="My Transcription",
            status="pending",
        )
        url = "/rest/api/v1/transcribe/transcriptions/"
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        if isinstance(response.data, dict) and "results" in response.data:
            results = response.data["results"]
        else:
            results = response.data
        # Should only see own transcription
        assert len(results) == 1
        assert results[0]["title"] == "My Transcription"