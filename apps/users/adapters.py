from __future__ import annotations

import typing

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_username
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.http import HttpRequest

    from apps.users.models import User


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def save_user(self, request: HttpRequest, user: "User", form, commit=True) -> "User":
        user = super().save_user(request, user, form, commit=False)
        if not user_username(user):
            email = user_email(user) or (form.cleaned_data.get("email") if form else "")
            if email:
                base = email.split("@", 1)[0]
                user.username = self.generate_unique_username([base, email])
        if commit:
            user.save()
            if form and hasattr(form, "save_m2m"):
                form.save_m2m()
        return user

    def get_reset_password_from_key_url(self, key: str) -> str:
        # allauth passes key as "<uid>-<token>", where token can include "-"
        if "-" in key:
            uid, token = key.split("-", 1)
        else:
            uid, token = "", key
        template = getattr(settings, "PASSWORD_RESET_CONFIRM_URL", None) or getattr(
            settings, "ACCOUNT_PASSWORD_RESET_CONFIRM", ""
        )
        if template:
            return template.format(uid=uid, token=token)
        return super().get_reset_password_from_key_url(key)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def populate_user(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
        data: dict[str, typing.Any],
    ) -> User:
        """
        Populates user information from social provider info.

        See: https://docs.allauth.org/en/latest/socialaccount/advanced.html#creating-and-populating-user-instances
        """
        user = super().populate_user(request, sociallogin, data)
        if not user.name:
            if name := data.get("name"):
                user.name = name
            elif first_name := data.get("first_name"):
                user.name = first_name
                if last_name := data.get("last_name"):
                    user.name += f" {last_name}"
        return user
