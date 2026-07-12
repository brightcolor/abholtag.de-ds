from django.urls import path
from . import views

app_name = "calendars"
urlpatterns = [
    path("address/<uuid:address_key_id>/<slug:waste_type_slug>.ics", views.CalendarFeedView.as_view(), name="feed"),
    path("address/<uuid:address_key_id>/", views.CalendarSubscribeView.as_view(), name="subscribe"),
    path("address/<uuid:address_key_id>/all.ics", views.CalendarFeedAllView.as_view(), name="feed_all"),
]