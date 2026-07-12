"""Core views - home page, static pages, theme toggle."""
from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.http import JsonResponse


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_hero"] = True
        return context


class AboutView(TemplateView):
    template_name = "core/about.html"


class PrivacyView(TemplateView):
    template_name = "core/privacy.html"


class AccessibilityView(TemplateView):
    template_name = "core/accessibility.html"


class ImprintView(TemplateView):
    template_name = "core/imprint.html"


class ThemeToggleView(View):
    """Toggle between light, dark, and system theme."""

    def post(self, request, *args, **kwargs):
        theme = request.POST.get("theme", "system")
        if theme not in ("light", "dark", "system"):
            theme = "system"
        
        response = JsonResponse({"theme": theme})
        response.set_cookie(
            "akl_theme",
            theme,
            max_age=31536000,
            samesite="Lax",
        )
        return response