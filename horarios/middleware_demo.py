"""Middleware solo para demo con túnel temporal. No usar en producción."""
from django.middleware.csrf import CsrfViewMiddleware


class DemoRelaxedCsrfMiddleware(CsrfViewMiddleware):
    """Permite login vía túnel (localtunnel/ngrok) cuando DJANGO_ALLOW_ALL_HOSTS=True."""

    def _origin_verified(self, request):
        return True

    def _check_referer(self, request):
        return
