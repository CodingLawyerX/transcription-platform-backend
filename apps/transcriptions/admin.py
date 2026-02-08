from django.contrib import admin
from .models import Transcription, TranscriptionSettings

@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'user', 
        'title', 
        'status', 
        'language',
        'created_at',
        'completed_at'
    ]
    list_filter = ['status', 'language', 'created_at']
    search_fields = ['title', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'file_size']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'title', 'status')
        }),
        ('Audio File', {
            'fields': ('audio_file', 'file_size', 'duration_seconds')
        }),
        ('Transcription', {
            'fields': ('transcribed_text', 'language', 'model_name')
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TranscriptionSettings)
class TranscriptionSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'default_language', 'default_model', 'notifications_enabled']
    search_fields = ['user__email']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('API Configuration', {
            'fields': ('backend_url', 'api_key')
        }),
        ('Defaults', {
            'fields': ('default_language', 'default_model')
        }),
        ('Preferences', {
            'fields': ('notifications_enabled', 'auto_delete_audio')
        }),
    )
