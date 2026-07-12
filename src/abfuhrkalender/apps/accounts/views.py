"""Accounts views - login, registration, profile."""
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_obj"] = self.request.user
        return context


class RegisterView(CreateView):
    model = User
    template_name = "accounts/register.html"
    fields = ["email", "display_name", "password"]
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        form.instance.set_password(form.cleaned_data["password"])
        return super().form_valid(form)
