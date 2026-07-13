from django.http import HttpResponse
from django.shortcuts import render

from apps.analytics.services import record_event
from apps.core.ratelimit import is_rate_limited

from .services import search_streets


def street_suggestions(request):
    """HTMX endpoint: renders the autocomplete suggestion list."""
    if is_rate_limited(request, "search"):
        return HttpResponse(status=429)
    query = request.GET.get("q", "").strip()
    streets = search_streets(query) if query else []
    if query and len(query) >= 2:
        if streets:
            record_event(request, "street_search", query=query, status="ok")
        else:
            record_event(request, "street_search_no_result", query=query, status="no_result")
    return render(
        request,
        "partials/street_suggestions.html",
        {"streets": streets, "query": query},
    )


def house_number_list(request):
    """JSON list of official house numbers of a street (BMS) for the datalist."""
    from django.http import JsonResponse

    from .models import Street

    if is_rate_limited(request, "search"):
        return HttpResponse(status=429)
    street = Street.objects.filter(pk=request.GET.get("street_id"), is_active=True).first()
    if street is None:
        return JsonResponse({"results": []})
    texts = list(street.house_numbers.values_list("text", flat=True)[:400])
    return JsonResponse({"results": texts})
