from django.conf import settings
from django.urls import include, path
from dj_rest_auth.registration.views import VerifyEmailView

from apps.users.api_views import (
    ConfirmEmailRedirectView,
    CustomRegisterView,
    FrontendPasswordResetConfirmView,
    altcha_challenge,
    change_password,
    check_token,
    resend_verification_email,
    user_profile,
)


api_routes = [
    path("altcha/challenge", altcha_challenge, name="altcha_challenge"),
    path("auth/", include("dj_rest_auth.urls")),
    path(
        "auth/registration/account-confirm-email/<str:key>/",
        ConfirmEmailRedirectView.as_view(),
        name="account_confirm_email",
    ),
    path("auth/registration/", CustomRegisterView.as_view(), name="rest_register"),
    path("auth/registration/verify-email/", VerifyEmailView.as_view(), name="rest_verify_email"),
    path("auth/registration/resend-email/", resend_verification_email, name="rest_resend_email"),
    path("auth/check-token/", check_token),
    path("auth/profile/", user_profile, name="user_profile"),
    path("auth/resend-verification/", resend_verification_email, name="resend_verification"),
    path("auth/change-password/", change_password, name="change_password"),
    path("transcribe/", include("apps.transcriptions.api_urls")),
]


urlpatterns = [
    path(f"{settings.HTTP_ROUTE}api/v1/", include(api_routes)),
    path(f"{settings.HTTP_ROUTE}auth/", include("rest_framework.urls")),
    path(
        f"{settings.HTTP_ROUTE}api/v1/auth/",
        include(
            [
                path(
                    "password/reset/<uidb64>/<token>/",
                    FrontendPasswordResetConfirmView.as_view(),
                    name="password_reset_confirm",
                ),
            ],
        ),
    ),
]
