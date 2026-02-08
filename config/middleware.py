from django.conf import settings
from django.http import HttpResponseForbidden


class TraefikApiKeyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip API key check for health endpoint
        if request.path == "/health/":
            return self.get_response(request)

        # Skip API key check for public auth endpoints
        if request.path.startswith("/rest/api/v1/auth/"):
            return self.get_response(request)
        
        # Skip API key check for internal Docker network requests
        # (no X-Forwarded-* headers present means direct container-to-container communication)
        if not request.headers.get("X-Forwarded-Proto"):
            return self.get_response(request)
        
        expected = getattr(settings, "TRAEFIK_API_KEY", "")
        header_name = getattr(settings, "TRAEFIK_API_HEADER", "X-Api-Key")
        if expected:
            provided = request.headers.get(header_name)
            if provided != expected:
                return HttpResponseForbidden("Forbidden")
        return self.get_response(request)
