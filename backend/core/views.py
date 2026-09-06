from django.conf import settings
from django.shortcuts import render


def index(request):
    """Public landing page: what this API is and where to go next."""
    spectacular = getattr(settings, "SPECTACULAR_SETTINGS", {})
    context = {
        "api_title": spectacular.get("TITLE", "Jango Mobile API"),
        "api_description": spectacular.get(
            "DESCRIPTION", "E-commerce API for the Jango Mobile app."
        ),
        "api_version": spectacular.get("VERSION", ""),
    }
    return render(request, "core/index.html", context)
