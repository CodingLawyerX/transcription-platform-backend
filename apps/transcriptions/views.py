import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from .models import Transcription, TranscriptionSettings
from .serializers import (
    TranscriptionSerializer,
    TranscriptionCreateSerializer,
    TranscriptionSettingsSerializer,
    HealthCheckSerializer,
    TranscriptionStatsSerializer,
    TranscriptionTimelineSerializer
)
from .tasks import process_transcription
from .health import check_database, check_redis, check_storage, check_celery

logger = logging.getLogger(__name__)


class TranscriptionRateThrottle(UserRateThrottle):
    scope = "transcription"


class TranscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet für Transkriptions-Verwaltung"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = TranscriptionSerializer
    
    def get_queryset(self):
        """Nur eigene Transkriptionen anzeigen"""
        return Transcription.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create transcription and start async Voxtral processing."""
        transcription = serializer.save(
            user=self.request.user,
            status='pending'
        )
        
        # Start async Voxtral task
        task = process_transcription.delay(transcription.id)
        logger.info(
            f"Submitted transcription {transcription.id} to Voxtral. "
            f"Task ID: {task.id}"
        )
    
    def get_throttles(self):
        """Apply custom throttle for create action."""
        if self.action == "create":
            return [TranscriptionRateThrottle()]
        return super().get_throttles()
    
    @action(detail=False, methods=['post'])
    def transcribe(self, request):
        """
        Audio-Datei transkribieren
        
        POST /rest/api/v1/transcribe/transcriptions/transcribe/
        Body: multipart/form-data
          - file: Audio-Datei
          - language: Sprache (optional, default: 'auto')
        """
        serializer = TranscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        audio_file = serializer.validated_data['file']
        language = serializer.validated_data.get('language', 'auto')
        
        # User-Einstellungen abrufen
        settings_obj, _ = TranscriptionSettings.objects.get_or_create(
            user=request.user,
            defaults={"backend_url": settings.VOXTRAL_BACKEND_URL},
        )
        
        # Transkriptions-Objekt erstellen
        transcription = Transcription.objects.create(
            user=request.user,
            audio_file=audio_file,
            language=language,
            status='processing'
        )
        
        try:
            # An externes Backend senden
            backend_url = settings_obj.backend_url.rstrip('/')
            if "api.openai.com" in backend_url or "/v1/audio/transcriptions" in backend_url:
                backend_url = settings.VOXTRAL_BACKEND_URL.rstrip('/')
                settings_obj.backend_url = backend_url
                settings_obj.save(update_fields=["backend_url"])
            api_key = settings_obj.api_key
            
            headers = {}
            if api_key:
                headers['X-API-KEY'] = api_key
            
            try:
                audio_file.seek(0)
            except Exception:
                try:
                    audio_file.file.seek(0)
                except Exception:
                    pass

            files = {'file': (audio_file.name, audio_file.file, audio_file.content_type)}
            data = {}
            if language and language != 'auto':
                data['language'] = language
            
            transcribe_url = backend_url
            if not transcribe_url.endswith('/transcribe'):
                transcribe_url = f'{transcribe_url}/transcribe'
            response = requests.post(
                transcribe_url,
                headers=headers,
                files=files,
                data=data,
                timeout=300  # 5 Minuten Timeout
            )
            if not response.ok:
                error_body = response.text[:1000]
                raise requests.exceptions.HTTPError(
                    f"{response.status_code} {response.reason}: {error_body}",
                    response=response,
                )

            try:
                result = response.json()
            except ValueError:
                raise requests.exceptions.RequestException(
                    f"Invalid JSON response from transcription backend (status {response.status_code})"
                )
            
            # Ergebnis speichern
            transcription.transcribed_text = result.get('text', '')
            transcription.model_name = result.get('model', '')
            transcription.language = result.get('language', language)
            transcription.status = 'completed'
            transcription.completed_at = timezone.now()
            transcription.save()
            
            return Response({
                'id': transcription.id,
                'text': transcription.transcribed_text,
                'language': transcription.language,
                'model': transcription.model_name,
                'status': 'ok'
            }, status=status.HTTP_200_OK)
            
        except requests.exceptions.RequestException as e:
            transcription.status = 'failed'
            error_detail = str(e)
            if getattr(e, "response", None) is not None:
                error_detail = f"{error_detail} | {e.response.text[:1000]}"
            transcription.error_message = error_detail
            transcription.save()
            
            return Response({
                'error': error_detail,
                'detail': 'Transkription fehlgeschlagen'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def health(self, request):
        """
        Health-Check des Transkriptions-Backends
        
        GET /rest/api/v1/transcribe/transcriptions/health/
        """
        settings_obj, _ = TranscriptionSettings.objects.get_or_create(
            user=request.user,
            defaults={"backend_url": settings.VOXTRAL_BACKEND_URL},
        )
        
        try:
            backend_url = settings_obj.backend_url.rstrip('/')
            if "api.openai.com" in backend_url or "/v1/audio/transcriptions" in backend_url:
                backend_url = settings.VOXTRAL_BACKEND_URL.rstrip('/')
                settings_obj.backend_url = backend_url
                settings_obj.save(update_fields=["backend_url"])
            api_key = settings_obj.api_key
            
            headers = {}
            if api_key:
                headers['X-API-KEY'] = api_key
            
            health_url = backend_url
            if not health_url.endswith('/health'):
                health_url = f'{health_url}/health'
            response = requests.get(
                health_url,
                headers=headers,
                timeout=10
            )
            
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                raise requests.exceptions.RequestException(
                    f"Invalid JSON response from health endpoint (status {response.status_code})"
                )
            
            return Response({
                'status': data.get('status', 'ok'),
                'model': data.get('model'),
                'have_key': bool(api_key)
            }, status=status.HTTP_200_OK)
            
        except requests.exceptions.RequestException as e:
            return Response({
                'status': 'error',
                'error': str(e),
                'have_key': bool(api_key)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistik-Daten für den aktuellen Benutzer
        
        GET /rest/api/v1/transcribe/transcriptions/stats/
        """
        user = request.user
        queryset = Transcription.objects.filter(user=user)
        
        # Gesamtstatistiken
        total_transcriptions = queryset.count()
        total_duration = queryset.aggregate(
            total=Sum('duration_seconds')
        )['total'] or 0
        total_file_size = queryset.aggregate(
            total=Sum('file_size')
        )['total'] or 0
        
        # Status-Zählungen
        status_counts = dict(
            queryset.values_list('status').annotate(count=Count('status'))
        )
        
        # Sprache-Zählungen
        language_counts = dict(
            queryset.values_list('language').annotate(count=Count('language'))
        )
        
        # Modell-Zählungen
        model_counts = dict(
            queryset.values_list('model_name').annotate(count=Count('model_name'))
        )
        
        # Letzte Transkriptionen (max 5)
        recent = queryset.order_by('-created_at')[:5]
        recent_transcriptions = [
            {
                'id': t.id,
                'title': t.title,
                'status': t.status,
                'language': t.language,
                'created_at': t.created_at,
                'duration_seconds': t.duration_seconds,
            }
            for t in recent
        ]
        
        data = {
            'total_transcriptions': total_transcriptions,
            'total_duration_seconds': total_duration,
            'total_file_size_bytes': total_file_size,
            'status_counts': status_counts,
            'language_counts': language_counts,
            'model_counts': model_counts,
            'recent_transcriptions': recent_transcriptions,
        }
        
        serializer = TranscriptionStatsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """
        Zeitreihendaten für Transkriptionen (letzte 30 Tage)
        
        GET /rest/api/v1/transcribe/transcriptions/timeline/
        Optional: ?days=30 (Anzahl Tage)
        """
        days = int(request.query_params.get('days', 30))
        if days > 365:
            days = 365
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        user = request.user
        queryset = Transcription.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Gruppierung nach Tag
        from django.db.models.functions import TruncDate
        timeline_data = (
            queryset
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                count=Count('id'),
                total_duration=Sum('duration_seconds')
            )
            .order_by('date')
        )
        
        # Lücken füllen
        result = []
        current_date = start_date
        while current_date <= end_date:
            entry = next(
                (item for item in timeline_data if item['date'] == current_date),
                {'date': current_date, 'count': 0, 'total_duration': 0}
            )
            result.append({
                'date': entry['date'],
                'count': entry['count'],
                'total_duration': entry['total_duration'] or 0,
            })
            current_date += timedelta(days=1)
        
        serializer = TranscriptionTimelineSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Get current processing status.
        
        GET /transcriptions/{id}/status/
        """
        transcription = self.get_object()
        return Response({
            'id': transcription.id,
            'status': transcription.status,
            'created_at': transcription.created_at,
            'updated_at': transcription.updated_at,
            'completed_at': transcription.completed_at,
            'error_message': transcription.error_message or '',
            'is_processing': transcription.is_processing,
            'is_complete': transcription.is_complete,
        })


class TranscriptionSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet für User-Einstellungen"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = TranscriptionSettingsSerializer
    http_method_names = ['get', 'put', 'patch']
    
    def get_queryset(self):
        return TranscriptionSettings.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Einstellungen für aktuellen User abrufen oder erstellen"""
        obj, _ = TranscriptionSettings.objects.get_or_create(
            user=self.request.user,
            defaults={"backend_url": settings.VOXTRAL_BACKEND_URL},
        )
        return obj


# Infrastructure health check endpoint
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for infrastructure components.
    Returns 200 if all checks pass, 503 otherwise.
    """
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "storage": check_storage(),
        "celery": check_celery(),
    }
    all_healthy = all(checks.values())
    status = "healthy" if all_healthy else "unhealthy"
    status_code = 200 if all_healthy else 503
    return Response(
        {"status": status, "checks": checks},
        status=status_code
    )
