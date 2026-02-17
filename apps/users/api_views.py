import altcha
from django.conf import settings
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.views import PasswordResetConfirmView
from allauth.account.models import EmailAddress
from dj_rest_auth.registration.views import RegisterView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import redirect
from django.views import View
from smtplib import SMTPException, SMTPRecipientsRefused
from allauth.account.models import EmailConfirmation, EmailConfirmationHMAC

from .serializers import CustomRegisterSerializer, UserDetailSerializer

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_token(request):
    """Simple endpoint for Next.js to validate auth token."""

    return Response({"message": "Token is valid"}, status=status.HTTP_200_OK)


class CustomRegisterView(RegisterView):
    serializer_class = CustomRegisterSerializer

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        try:
            return super().create(request, *args, **kwargs)
        except SMTPRecipientsRefused:
            return Response(
                {
                    "email": [
                        "Email delivery was refused by the mail server. Please use a different email address.",
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPException:
            return Response(
                {
                    "email": [
                        "Unable to send verification email right now. Please try again later.",
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get or update user profile.

    Avatar upload and audit logging from the old project are omitted for now
    to keep the implementation minimal; this can be extended later if needed.
    """

    if request.method == "GET":
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    data = request.data.copy()
    serializer = UserDetailSerializer(request.user, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """Resend email verification using django-allauth EmailAddress model."""

    email = request.data.get("email")
    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        email_address = EmailAddress.objects.get_for_user(user, email)

        if email_address.verified:
            return Response({"message": "Email is already verified"}, status=status.HTTP_200_OK)

        try:
            email_address.send_confirmation(request)
            return Response({"message": "Verification email sent successfully"}, status=status.HTTP_200_OK)
        except SMTPRecipientsRefused:
            return Response(
                {
                    "email": [
                        "Email delivery was refused by the mail server. Please use a different email address.",
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPException:
            return Response(
                {
                    "email": [
                        "Unable to send verification email right now. Please try again later.",
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except User.DoesNotExist:
        return Response({"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND)
    except EmailAddress.DoesNotExist:
        return Response({"error": "Email address not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change password for authenticated user.

    Mirrors the behavior from the old backend so the frontend messages match
    expectations (messages are in German there).
    """

    old_password = request.data.get("old_password")
    new_password1 = request.data.get("new_password1")
    new_password2 = request.data.get("new_password2")

    if not old_password or not new_password1 or not new_password2:
        return Response(
            {"error": "Alle Passwortfelder sind erforderlich"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_password1 != new_password2:
        return Response(
            {"error": "Die neuen Passwörter stimmen nicht überein"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user
    if not user.check_password(old_password):
        return Response(
            {"error": "Das alte Passwort ist falsch"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password1)
    user.save()

    # Keep user logged in after password change
    update_session_auth_hash(request, user)

    return Response({"message": "Passwort erfolgreich geändert"}, status=status.HTTP_200_OK)


class FrontendPasswordResetConfirmView(PasswordResetConfirmView):
    """Override Django's PasswordResetConfirmView to redirect to frontend."""

    def dispatch(self, *args, **kwargs):  # type: ignore[override]
        # Let the base view validate the token, then redirect regardless
        response = super().dispatch(*args, **kwargs)
        uidb64 = kwargs.get("uidb64")
        token = kwargs.get("token")
        frontend_url = settings.ACCOUNT_PASSWORD_RESET_CONFIRM.format(uid=uidb64, token=token)
        return redirect(frontend_url)


class ConfirmEmailRedirectView(View):
    """Confirm email address and redirect to the frontend."""

    def get(self, request, key, *args, **kwargs):  # type: ignore[override]
        confirmation = EmailConfirmationHMAC.from_key(key)
        if confirmation is None:
            try:
                confirmation = EmailConfirmation.objects.get(key=key)
            except EmailConfirmation.DoesNotExist:
                redirect_url = getattr(
                    settings,
                    "ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL",
                    "https://app.simpliant-ds.eu/login",
                )
                return redirect(redirect_url)
        
        
        confirmation.confirm(request)

        if request.user.is_authenticated:
            redirect_url = getattr(
                settings,
                "ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL",
                "https://app.simpliant-ds.eu/profile",
            )
        else:
            redirect_url = getattr(
                settings,
                "ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL",
                "https://app.simpliant-ds.eu/login",
            )
        return redirect(redirect_url)


@api_view(["GET"])
@permission_classes([AllowAny])
def altcha_challenge(request):
    """Generate ALTCHA challenge for Proof-of-Work CAPTCHA.
    
    Returns a challenge that the client must solve to prove they are not a bot.
    The challenge uses SHA-256 and requires computational work to solve.
    """
    hmac_key = getattr(settings, "ALTCHA_HMAC_KEY", "")
    if not hmac_key:
        return Response(
            {"error": "CAPTCHA not configured"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
    try:
        challenge = altcha.create_challenge(
            altcha.ChallengeOptions(
                hmac_key=hmac_key,
                max_number=50000,
            )
        )
        return Response({
            "algorithm": challenge.algorithm,
            "challenge": challenge.challenge,
            "maxnumber": challenge.max_number,
            "salt": challenge.salt,
            "signature": challenge.signature,
        })
    except Exception as e:
        return Response(
            {"error": "Failed to generate challenge"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
