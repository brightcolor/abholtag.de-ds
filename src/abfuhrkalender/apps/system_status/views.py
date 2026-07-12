"""Health checks and system monitoring."""
from django.http import JsonResponse
from django.views.generic import TemplateView, View
from django.db import connection
from django.conf import settings
from .models import SystemCheck


class HealthView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok", "service": "abfuhrkalender"})


class LivenessView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "alive"})


class ReadinessView(View):
    def get(self, request, *args, **kwargs):
        try:
            connection.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False
        return JsonResponse({
            "status": "ready" if db_ok else "not_ready",
            "database": "ok" if db_ok else "error",
        })


class SystemStatusDashboardView(TemplateView):
    template_name = "system_status/dashboard.html"
