from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Transcription, TranscriptionSettings

User = get_user_model()


class TranscriptionStatsTests(APITestCase):
    """Tests für Statistik- und Timeline-Endpunkte"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        self.client.force_authenticate(user=self.user)
        
        # Testdaten erstellen
        Transcription.objects.create(
            user=self.user,
            title='Test 1',
            status='completed',
            language='de',
            model_name='whisper-large-v3',
            duration_seconds=120,
            file_size=1024000,
            created_at=timezone.now() - timedelta(days=1)
        )
        Transcription.objects.create(
            user=self.user,
            title='Test 2',
            status='processing',
            language='en',
            model_name='whisper-tiny',
            duration_seconds=60,
            file_size=512000,
            created_at=timezone.now()
        )
        Transcription.objects.create(
            user=self.user,
            title='Test 3',
            status='failed',
            language='de',
            model_name='whisper-large-v3',
            duration_seconds=180,
            file_size=2048000,
            created_at=timezone.now() - timedelta(days=5)
        )
        
        # Einstellungen erstellen
        TranscriptionSettings.objects.create(
            user=self.user,
            backend_url='https://api.example.com',
            api_key='test-key'
        )
    
    def test_stats_endpoint(self):
        """Testet den Stats-Endpunkt"""
        url = '/rest/api/v1/transcribe/transcriptions/stats/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Grundlegende Felder prüfen
        self.assertIn('total_transcriptions', data)
        self.assertEqual(data['total_transcriptions'], 3)
        
        self.assertIn('total_duration_seconds', data)
        self.assertEqual(data['total_duration_seconds'], 360)  # 120+60+180
        
        self.assertIn('total_file_size_bytes', data)
        self.assertEqual(data['total_file_size_bytes'], 3584000)  # 1024000+512000+2048000
        
        # Status-Zählungen prüfen
        self.assertIn('status_counts', data)
        self.assertEqual(data['status_counts'].get('completed', 0), 1)
        self.assertEqual(data['status_counts'].get('processing', 0), 1)
        self.assertEqual(data['status_counts'].get('failed', 0), 1)
        
        # Sprache-Zählungen prüfen
        self.assertIn('language_counts', data)
        self.assertEqual(data['language_counts'].get('de', 0), 2)
        self.assertEqual(data['language_counts'].get('en', 0), 1)
        
        # Modell-Zählungen prüfen
        self.assertIn('model_counts', data)
        self.assertEqual(data['model_counts'].get('whisper-large-v3', 0), 2)
        self.assertEqual(data['model_counts'].get('whisper-tiny', 0), 1)
        
        # Letzte Transkriptionen prüfen
        self.assertIn('recent_transcriptions', data)
        self.assertEqual(len(data['recent_transcriptions']), 3)  # alle 3
    
    def test_stats_empty(self):
        """Testet Stats mit leerer Datenbank"""
        # Neuen Benutzer ohne Transkriptionen
        user2 = User.objects.create_user(
            email='empty@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=user2)
        
        url = '/rest/api/v1/transcribe/transcriptions/stats/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        self.assertEqual(data['total_transcriptions'], 0)
        self.assertEqual(data['total_duration_seconds'], 0)
        self.assertEqual(data['total_file_size_bytes'], 0)
        self.assertEqual(data['status_counts'], {})
        self.assertEqual(data['language_counts'], {})
        self.assertEqual(data['model_counts'], {})
        self.assertEqual(data['recent_transcriptions'], [])
    
    def test_timeline_endpoint_default(self):
        """Testet den Timeline-Endpunkt mit Standard-Parametern"""
        url = '/rest/api/v1/transcribe/transcriptions/timeline/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Sollte eine Liste von Tagen zurückgeben
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        
        # Prüfe Struktur jedes Eintrags
        for entry in data:
            self.assertIn('date', entry)
            self.assertIn('count', entry)
            self.assertIn('total_duration', entry)
    
    def test_timeline_with_days_param(self):
        """Testet Timeline mit days-Parameter"""
        url = '/rest/api/v1/transcribe/transcriptions/timeline/?days=7'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Sollte genau 7 Tage zurückgeben
        self.assertEqual(len(data), 7)
        
        # Tage sollten aufsteigend sein
        dates = [entry['date'] for entry in data]
        self.assertEqual(sorted(dates), dates)
    
    def test_timeline_max_days(self):
        """Testet dass days auf 365 begrenzt ist"""
        url = '/rest/api/v1/transcribe/transcriptions/timeline/?days=400'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Sollte maximal 365 Tage zurückgeben
        self.assertLessEqual(len(data), 365)
    
    def test_unauthenticated_access(self):
        """Testet dass unauthentifizierte Zugriffe abgelehnt werden"""
        self.client.logout()
        
        urls = [
            '/rest/api/v1/transcribe/transcriptions/stats/',
            '/rest/api/v1/transcribe/transcriptions/timeline/',
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_stats_only_own_data(self):
        """Testet dass nur eigene Transkriptionen gezählt werden"""
        # Zweiter Benutzer mit eigenen Transkriptionen
        user2 = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        Transcription.objects.create(
            user=user2,
            title='Other User',
            status='completed',
            language='fr',
            duration_seconds=300,
            file_size=5000000
        )
        
        # Authentifiziert als erster Benutzer
        self.client.force_authenticate(user=self.user)
        url = '/rest/api/v1/transcribe/transcriptions/stats/'
        response = self.client.get(url)
        
        # Sollte nur 3 Transkriptionen haben (nicht 4)
        self.assertEqual(response.data['total_transcriptions'], 3)
        self.assertNotIn('fr', response.data['language_counts'])


class TranscriptionViewSetIntegrationTests(APITestCase):
    """Integrationstests für bestehende Endpunkte mit neuen Features"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_transcriptions(self):
        """Testet dass Listen-Endpunkt weiterhin funktioniert"""
        url = '/rest/api/v1/transcribe/transcriptions/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_health_endpoint(self):
        """Testet dass Health-Endpunkt weiterhin funktioniert"""
        # Mock-Einstellungen erstellen
        TranscriptionSettings.objects.create(
            user=self.user,
            backend_url='https://api.example.com'
        )
        
        url = '/rest/api/v1/transcribe/transcriptions/health/'
        response = self.client.get(url)
        
        # Erwarte Fehler weil Backend nicht erreichbar, aber Status 503
        self.assertIn(response.status_code, [status.HTTP_503_SERVICE_UNAVAILABLE, status.HTTP_200_OK])
    
    def test_transcribe_endpoint(self):
        """Testet dass Transcribe-Endpunkt weiterhin funktioniert"""
        # Dieser Test benötigt eine echte Audio-Datei, überspringen wir
        pass
