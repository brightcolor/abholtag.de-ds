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
