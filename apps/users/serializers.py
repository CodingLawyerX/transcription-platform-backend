from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import (
    PasswordResetSerializer as DefaultPasswordResetSerializer,
)
from dj_rest_auth.serializers import PasswordResetConfirmSerializer as DefaultPasswordResetConfirmSerializer
from dj_rest_auth.serializers import (
    TokenSerializer as DefaultTokenSerializer,
)
from dj_rest_auth.serializers import (
    UserDetailsSerializer as DefaultUserDetailSerializer,
    LoginSerializer as DefaultLoginSerializer,
)
from rest_framework import serializers
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.tokens import default_token_generator as django_default_token_generator
from allauth.account.forms import default_token_generator as allauth_default_token_generator
from allauth.account.utils import url_str_to_user_pk
from smtplib import SMTPException, SMTPRecipientsRefused

User = get_user_model()


class FrontendPasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        template = getattr(settings, "ACCOUNT_PASSWORD_RESET_CONFIRM", "") or getattr(
            settings, "PASSWORD_RESET_CONFIRM_URL", ""
        )
        uid = context.get("uid")
        token = context.get("token")
        if template and uid and token:
            context["password_reset_url"] = template.format(uid=uid, token=token)
        subject = loader.render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")

        # Let SMTP/network failures bubble up so the API can return actionable errors.
        email_message.send()


class UserDetailSerializer(DefaultUserDetailSerializer):
    """Slimmed-down user detail serializer for REST auth.

    Fields should cover everything the Next.js frontend actually uses.
    """

    email_verified = serializers.SerializerMethodField()

    class Meta(DefaultUserDetailSerializer.Meta):
        model = User
        fields = (
            "username",
            "email",
            "email_verified",
            "name",
            "is_active",
            "is_staff",
        )

    def get_email_verified(self, obj):
        if not obj.email:
            return False
        return EmailAddress.objects.filter(user=obj, email=obj.email, verified=True).exists()


class TokenSerializer(DefaultTokenSerializer):
    user = UserDetailSerializer(read_only=True)

    class Meta(DefaultTokenSerializer.Meta):
        fields = ("key", "user")


class CustomLoginSerializer(DefaultLoginSerializer):
    """Login serializer that accepts either username or email."""

    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs):
        # If email is provided, map it to username field for authentication
        email = attrs.get('email', '').strip()
        username = attrs.get('username', '').strip()

        if email and not username:
            # Try to find user by email
            try:
                user = User.objects.get(email=email)
                attrs['username'] = user.username
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    "Unable to log in with provided credentials."
                )
        # Let the parent validation handle the rest
        return super().validate(attrs)


class CustomRegisterSerializer(RegisterSerializer):
    """Registration serializer compatible with dj-rest-auth/Next.js flow."""

    username = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        if not data.get("username"):
            email = data.get("email", "")
            if email:
                base = email.split("@", 1)[0]
                data["username"] = get_adapter().generate_unique_username([base, email])
        data.update({
            "name": self.validated_data.get("name", ""),
        })
        return data

    def save(self, request):
        user = super().save(request)
        user.name = self.cleaned_data.get("name", "")
        user.save(update_fields=["name"])
        return user


class CustomPasswordResetSerializer(DefaultPasswordResetSerializer):
    """Custom serializer to generate frontend password reset URL.

    Mirrors the behavior from the old backend by delegating to Django's
    PasswordResetForm but ensures the email template gets the frontend
    reset URL from settings.
    """

    def save(self):
        request = self.context.get("request")
        form: PasswordResetForm = self.reset_form

        opts = {
            "use_https": request.is_secure() if request is not None else False,
            "from_email": getattr(settings, "DEFAULT_FROM_EMAIL", None),
            "email_template_name": "account/email/password_reset_key_message.html",
            "subject_template_name": "account/email/password_reset_key_subject.txt",
            "request": request,
            "html_email_template_name": "account/email/password_reset_key_message.html",
        }
        try:
            form.save(**opts)
        except SMTPRecipientsRefused:
            raise serializers.ValidationError(
                {
                    "email": [
                        "Email delivery was refused by the mail server. Please use a different email address.",
                    ],
                }
            )
        except SMTPException:
            raise serializers.ValidationError(
                {
                    "email": [
                        "Unable to send password reset email right now. Please try again later.",
                    ],
                }
            )

    @property
    def password_reset_form_class(self):
        # Use a custom form to inject the frontend reset URL into the email context.
        return FrontendPasswordResetForm


class CustomPasswordResetConfirmSerializer(DefaultPasswordResetConfirmSerializer):
    """Accept both allauth base36 and Django uidb64 formats."""

    def validate(self, attrs):
        uid_value = attrs.get("uid", "")
        user = None

        # Try allauth base36 UID first.
        try:
            uid = force_str(url_str_to_user_pk(uid_value))
            user = User._default_manager.get(pk=uid)
            token_generator = allauth_default_token_generator
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, DjangoValidationError):
            # Fall back to Django's uidb64.
            try:
                uid = force_str(urlsafe_base64_decode(uid_value))
                user = User._default_manager.get(pk=uid)
                token_generator = django_default_token_generator
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                raise serializers.ValidationError({"uid": ["Invalid value"]})

        self.user = user
        if not token_generator.check_token(self.user, attrs["token"]):
            raise serializers.ValidationError({"token": ["Invalid value"]})

        self.custom_validation(attrs)
        self.set_password_form = self.set_password_form_class(user=self.user, data=attrs)
        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)

        return attrs
