from django.urls import path

from . import views

urlpatterns = [
    path("moderation/", views.queue, name="moderation_queue"),
]
