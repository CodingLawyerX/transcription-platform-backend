# transcriptions/api_urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import TranscriptionViewSet, TranscriptionSettingsViewSet, health_check

router = DefaultRouter()
router.register(r"transcriptions", TranscriptionViewSet, basename="transcription")
router.register(r"settings", TranscriptionSettingsViewSet, basename="transcription-settings")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", health_check, name="health-check"),
]