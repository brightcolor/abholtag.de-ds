from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("privacy/", views.PrivacyView.as_view(), name="privacy"),
    path("accessibility/", views.AccessibilityView.as_view(), name="accessibility"),
    path("imprint/", views.ImprintView.as_view(), name="imprint"),
    path("theme-toggle/", views.ThemeToggleView.as_view(), name="theme-toggle"),
]