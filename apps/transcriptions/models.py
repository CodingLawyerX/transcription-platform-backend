from django.db import models
from django.conf import settings


class Transcription(models.Model):
    """Audio Transkription mit Status-Tracking"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transcriptions'
    )
    
    # Audio Info
    audio_file = models.FileField(
        upload_to='audio/%Y/%m/',
        null=True,
        blank=True
    )
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Audio duration in seconds"
    )
    
    # Transkription
    title = models.CharField(max_length=255, blank=True)
    transcribed_text = models.TextField(blank=True)
    
    # Processing Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error details if status is 'failed'"
    )
    
    # Settings used for this transcription
    language = models.CharField(
        max_length=10,
        default='de',
        help_text="Language code (e.g., 'de', 'en')"
    )
    model_name = models.CharField(
        max_length=50,
        default='whisper-large-v3',
        help_text="AI model used for transcription"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When transcription was completed"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        verbose_name = 'Transcription'
        verbose_name_plural = 'Transcriptions'
    
    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.status})"
    
    @property
    def is_processing(self):
        return self.status in ['pending', 'processing']
    
    @property
    def is_complete(self):
        return self.status == 'completed'


class TranscriptionSettings(models.Model):
    """User-specific settings for transcription service"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transcription_settings'
    )
    
    # External Service Configuration
    backend_url = models.URLField(
        default=settings.VOXTRAL_BACKEND_URL,
        help_text="Base URL of the transcription service"
    )
    api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="API key for transcription service (encrypted)"
    )
    
    # Default Settings
    default_language = models.CharField(
        max_length=10,
        default='de',
        help_text="Default language for transcriptions"
    )
    default_model = models.CharField(
        max_length=50,
        default='whisper-large-v3',
        help_text="Default AI model to use"
    )
    
    # Preferences
    notifications_enabled = models.BooleanField(
        default=True,
        help_text="Send email when transcription is complete"
    )
    auto_delete_audio = models.BooleanField(
        default=False,
        help_text="Automatically delete audio file after transcription"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Transcription Settings'
        verbose_name_plural = 'Transcription Settings'
    
    def __str__(self):
        return f"Settings for {self.user.email}"
