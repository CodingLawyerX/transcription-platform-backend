import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestAuthRegistration:
    """Tests for user registration endpoint."""

    def test_register_user_success(self, api_client):
        """POST /rest/api/v1/auth/registration/ -> 201 + 'key'."""
        url = "/rest/api/v1/auth/registration/"
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
            "name": "Test User",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "key" in response.data
        # Verify user was created
        user = User.objects.get(email="test@example.com")
        assert user.username == "testuser"
        assert user.name == "Test User"

    def test_register_duplicate_email(self, api_client):
        """POST with duplicate email -> 400."""
        # Create a user first
        user = User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="password123",
            name="Existing User",
        )
        # Ensure EmailAddress entry exists (allauth uses this for uniqueness)
        from allauth.account.models import EmailAddress
        EmailAddress.objects.create(
            user=user,
            email="existing@example.com",
            verified=True,
            primary=True,
        )
        url = "/rest/api/v1/auth/registration/"
        data = {
            "username": "newuser",
            "email": "existing@example.com",  # duplicate email
            "password1": "securepassword123",
            "password2": "securepassword123",
            "name": "New User",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Ensure error about email exists
        assert "email" in response.data or any(
            "email" in err for err in response.data.get("non_field_errors", [])
        )


@pytest.mark.django_db
class TestAuthLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, api_client):
        """POST /rest/api/v1/auth/login/ -> 200 + 'key'."""
        # Create a user
        user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password="password123",
            name="Login User",
        )
        url = "/rest/api/v1/auth/login/"
        data = {
            "username": "loginuser",
            "password": "password123",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "key" in response.data
        # Verify token belongs to the user
        from rest_framework.authtoken.models import Token
        token = Token.objects.get(user=user)
        assert response.data["key"] == token.key

    def test_login_wrong_password(self, api_client):
        """POST with wrong password -> 400."""
        User.objects.create_user(
            username="wrongpass",
            email="wrong@example.com",
            password="correctpassword",
            name="Wrong Pass",
        )
        url = "/rest/api/v1/auth/login/"
        data = {
            "username": "wrongpass",
            "password": "wrongpassword",
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Ensure error about invalid credentials
        assert "non_field_errors" in response.data