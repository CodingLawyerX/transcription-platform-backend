from rest_framework import serializers
from .models import Transcription, TranscriptionSettings

class TranscriptionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    is_processing = serializers.BooleanField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Transcription
        fields = [
            'id',
            'user',
            'title',
            'audio_file',
            'file_size',
            'duration_seconds',
            'transcribed_text',
            'status',
            'error_message',
            'language',
            'model_name',
            'created_at',
            'updated_at',
            'completed_at',
            'is_processing',
            'is_complete',
        ]
        read_only_fields = [
            'user',
            'file_size',
            'transcribed_text',
            'status',
            'error_message',
            'created_at',
            'updated_at',
            'completed_at',
        ]

class TranscriptionCreateSerializer(serializers.Serializer):
    """Serializer für Transkriptions-Anfragen"""
    
    file = serializers.FileField(required=True)
    language = serializers.CharField(
        max_length=10,
        default='de',
        required=False
    )
    
    def validate_file(self, value):
        """Validiere Audio-Datei"""
        # Max 50MB
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError(
                "Datei ist zu groß. Maximum: 50MB"
            )
        
        # Erlaubte Formate
        allowed_types = [
            'audio/mpeg',
            'audio/mp4',
            'audio/wav',
            'audio/flac',
            'audio/ogg',
            'audio/webm'
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Nicht unterstütztes Format: {value.content_type}"
            )
        
        return value


class TranscriptionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptionSettings
        fields = [
            'id',
            'backend_url',
            'api_key',
            'default_language',
            'default_model',
            'notifications_enabled',
            'auto_delete_audio',
            'updated_at',
        ]
        extra_kwargs = {
            'api_key': {'write_only': True}  # Nie im Response zeigen!
        }


class HealthCheckSerializer(serializers.Serializer):
    """Serializer für Health-Check-Response"""
    
    status = serializers.CharField()
    model = serializers.CharField(required=False)
    have_key = serializers.BooleanField(required=False)


class TranscriptionStatsSerializer(serializers.Serializer):
    """Serializer für Transkriptions-Statistiken"""
    
    total_transcriptions = serializers.IntegerField()
    total_duration_seconds = serializers.IntegerField()
    total_file_size_bytes = serializers.IntegerField()
    status_counts = serializers.DictField(child=serializers.IntegerField())
    language_counts = serializers.DictField(child=serializers.IntegerField())
    model_counts = serializers.DictField(child=serializers.IntegerField())
    recent_transcriptions = serializers.ListField(child=serializers.DictField())


class TranscriptionTimelineSerializer(serializers.Serializer):
    """Serializer für Zeitreihendaten"""
    
    date = serializers.DateField()
    count = serializers.IntegerField()
    total_duration = serializers.IntegerField()