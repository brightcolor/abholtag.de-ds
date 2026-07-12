import time

from django import forms
from django.conf import settings

from .models import CommunityContribution, ErrorReport


class HoneypotMixin(forms.Form):
    """Bot protection: hidden honeypot field + minimum fill time (§34)."""

    website = forms.CharField(required=False, widget=forms.HiddenInput)  # honeypot
    form_started = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Die Eingabe konnte nicht verarbeitet werden.")
        started = cleaned.get("form_started")
        try:
            elapsed = time.time() - float(started)
        except (TypeError, ValueError):
            elapsed = None
        if elapsed is not None and elapsed < settings.FORM_MIN_SECONDS:
            raise forms.ValidationError(
                "Das Formular wurde zu schnell abgesendet. Bitte versuchen Sie es erneut."
            )
        return cleaned


class ErrorReportForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = ErrorReport
        fields = ["category", "description", "source_hint", "contact_email"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Was ist falsch? Bitte beschreiben Sie das Problem so konkret wie möglich.",
                }
            ),
            "source_hint": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "z. B. Aushang, Anruf bei der Hotline …"}
            ),
            "contact_email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "optional – nur für Rückfragen"}
            ),
        }


class CommunityContributionForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = CommunityContribution
        fields = [
            "waste_type", "year", "date", "zone_code", "street_text",
            "district_text", "house_range", "note", "source_hint", "evidence", "contact_email",
        ]
        widgets = {
            "waste_type": forms.Select(attrs={"class": "form-control"}),
            "year": forms.NumberInput(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "zone_code": forms.TextInput(attrs={"class": "form-control", "maxlength": 10}),
            "street_text": forms.TextInput(attrs={"class": "form-control"}),
            "district_text": forms.TextInput(attrs={"class": "form-control"}),
            "house_range": forms.TextInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "source_hint": forms.TextInput(attrs={"class": "form-control"}),
            "evidence": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean_evidence(self):
        upload = self.cleaned_data.get("evidence")
        if upload:
            if upload.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Die Datei darf höchstens 10 MB groß sein.")
            allowed = ("image/jpeg", "image/png", "image/webp", "application/pdf")
            if getattr(upload, "content_type", "") not in allowed:
                raise forms.ValidationError("Erlaubt sind JPG, PNG, WebP oder PDF.")
        return upload
