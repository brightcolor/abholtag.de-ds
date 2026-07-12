from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Basis"

    def ready(self):
        # Enforce TOTP two-factor auth for the admin when configured (§34).
        if settings.ADMIN_OTP_REQUIRED:
            from django.contrib import admin
            from django_otp.admin import OTPAdminSite

            admin.site.__class__ = OTPAdminSite
