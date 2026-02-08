"""Celery tasks for Voxtral transcription processing."""
import logging
import os
import requests
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Transcription

logger = logging.getLogger(__name__)


def get_content_type(filename):
    """Get content type based on file extension."""
    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.mp4': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.webm': 'audio/webm',
    }
    return content_types.get(ext, 'audio/mpeg')


@shared_task(bind=True, max_retries=3)
def process_transcription(self, transcription_id):
    """
    Process audio transcription using Voxtral API.
    
    Args:
        transcription_id (int): ID of Transcription object
        
    Returns:
        dict: Result with transcription_id, status, text_length
    """
    try:
        transcription = Transcription.objects.select_related('user').get(id=transcription_id)
        
        logger.info(
            f"Starting Voxtral transcription {transcription_id} "
            f"for user {transcription.user.email}"
        )
        
        # Update status to processing
        transcription.status = 'processing'
        transcription.save(update_fields=['status', 'updated_at'])
        
        # Get language (use user settings or model default)
        try:
            user_settings = transcription.user.transcription_settings
            language = user_settings.default_language or transcription.language or 'de'
        except Exception:
            language = transcription.language or 'de'
        
        # Prepare Voxtral API request
        voxtral_url = f"{settings.VOXTRAL_BACKEND_URL}/transcribe"
        headers = {
            'X-API-KEY': settings.VOXTRAL_API_KEY
        }
        
        # Open audio file from MinIO/S3
        with transcription.audio_file.open('rb') as audio_file:
            # Get just the filename without path - Voxtral doesn't need full path
            filename = os.path.basename(transcription.audio_file.name)
            content_type = get_content_type(filename)
            
            files = {
                'file': (
                    filename,
                    audio_file,
                    content_type
                )
            }
            data = {
                'language': language
            }
            
            logger.info(f"Calling Voxtral API for transcription {transcription_id}")
            
            # Call Voxtral API (may take minutes for long audio)
            response = requests.post(
                voxtral_url,
                files=files,
                data=data,
                headers=headers,
                timeout=1800  # 30 minutes timeout
            )
            
            response.raise_for_status()
            result = response.json()
        
        # Extract transcription text
        if result.get('status') != 'ok':
            raise Exception(f"Voxtral API error: {result}")
        
        transcribed_text = result.get('text', '')
        segments = result.get('segments', [])
        detected_language = result.get('language')
        
        # Update transcription with result
        transcription.transcribed_text = transcribed_text
        transcription.status = 'completed'
        transcription.completed_at = timezone.now()
        
        # Update language if detected
        if detected_language and not transcription.language:
            transcription.language = detected_language
        
        transcription.save(update_fields=[
            'transcribed_text',
            'status',
            'completed_at',
            'language',
            'updated_at'
        ])
        
        logger.info(
            f"Completed Voxtral transcription {transcription_id} "
            f"({len(transcribed_text)} chars, {len(segments)} segments)"
        )
        
        # Send notification if enabled
        try:
            user_settings = transcription.user.transcription_settings
            if user_settings and user_settings.notifications_enabled:
                send_completion_email(transcription)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
        
        return {
            'transcription_id': transcription_id,
            'status': 'completed',
            'text_length': len(transcribed_text),
            'segments_count': len(segments),
            'language': detected_language,
            'user': transcription.user.email
        }
        
    except Transcription.DoesNotExist:
        logger.error(f"Transcription {transcription_id} not found")
        raise
    
    except requests.exceptions.Timeout:
        error_msg = "Voxtral API timeout (audio too long?)"
        logger.error(f"Transcription {transcription_id}: {error_msg}")
        
        try:
            transcription = Transcription.objects.get(id=transcription_id)
            transcription.status = 'failed'
            transcription.error_message = error_msg
            transcription.save(update_fields=['status', 'error_message', 'updated_at'])
        except Exception:
            pass
        
        raise Exception(error_msg)
    
    except requests.exceptions.HTTPError as exc:
        error_msg = f"Voxtral API HTTP error: {exc.response.status_code}"
        
        # Handle specific errors
        if exc.response.status_code == 413:
            error_msg = "Audio file too large (max 50MB)"
        elif exc.response.status_code == 429:
            error_msg = "Voxtral API rate limit exceeded"
        elif exc.response.status_code == 401:
            error_msg = "Invalid Voxtral API key"
        
        try:
            error_detail = exc.response.json().get('detail', '')
            if error_detail:
                error_msg += f": {error_detail}"
        except:
            pass
        
        logger.error(f"Transcription {transcription_id}: {error_msg}")
        
        try:
            transcription = Transcription.objects.get(id=transcription_id)
            transcription.status = 'failed'
            transcription.error_message = error_msg[:500]
            transcription.save(update_fields=['status', 'error_message', 'updated_at'])
        except Exception:
            pass
        
        # Don't retry on 4xx errors (client errors)
        if 400 <= exc.response.status_code < 500:
            raise Exception(error_msg)
        
        # Retry on 5xx errors (server errors)
        raise self.retry(exc=exc, countdown=120)  # Retry after 2 minutes
        
    except Exception as exc:
        error_msg = str(exc)[:500]
        logger.error(
            f"Error processing transcription {transcription_id}: {exc}",
            exc_info=True
        )
        
        try:
            transcription = Transcription.objects.get(id=transcription_id)
            transcription.status = 'failed'
            transcription.error_message = error_msg
            transcription.save(update_fields=['status', 'error_message', 'updated_at'])
        except Exception as save_error:
            logger.error(f"Failed to save error state: {save_error}")
        
        # Retry for network errors
        if isinstance(exc, requests.exceptions.RequestException):
            raise self.retry(exc=exc, countdown=60)
        
        raise


def send_completion_email(transcription):
    """Send email notification when transcription is complete."""
    subject = f'Transcription Complete: {transcription.title or "Untitled"}'
    
    message = f"""
Hello {transcription.user.email},

Your transcription is now complete!

Title: {transcription.title or "Untitled"}
Language: {transcription.language or "auto-detected"}
Created: {transcription.created_at.strftime('%Y-%m-%d %H:%M')}
Completed: {transcription.completed_at.strftime('%Y-%m-%d %H:%M')}

Text length: {len(transcription.transcribed_text)} characters

View at: [YOUR_FRONTEND_URL]/transcriptions/{transcription.id}

Best regards,
Transcription Platform
    """.strip()
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[transcription.user.email],
            fail_silently=False,
        )
        logger.info(f"Sent completion email to {transcription.user.email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")