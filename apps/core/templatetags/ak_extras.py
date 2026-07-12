from datetime import date as date_cls

from django import template

register = template.Library()

WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS_DE_SHORT = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


@register.filter
def weekday_de(value):
    return WEEKDAYS_DE[value.weekday()] if value else ""


@register.filter
def month_short_de(value):
    return MONTHS_DE_SHORT[value.month - 1] if value else ""


@register.filter
def month_de(value):
    return MONTHS_DE[value.month - 1] if value else ""


@register.filter
def relative_days(value):
    """Human friendly relative label: heute, morgen, in X Tagen."""
    if not value:
        return ""
    delta = (value - date_cls.today()).days
    if delta < 0:
        return "vergangen"
    if delta == 0:
        return "heute"
    if delta == 1:
        return "morgen"
    if delta < 14:
        return f"in {delta} Tagen"
    weeks = delta // 7
    return f"in {weeks} Wochen" if weeks > 1 else "in 1 Woche"


@register.filter
def is_past(value):
    return bool(value) and value < date_cls.today()
