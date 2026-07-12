"""Accounts views - login, registration, profile."""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"


class RegisterView(TemplateView):
    template_name = "accounts/register.html"
