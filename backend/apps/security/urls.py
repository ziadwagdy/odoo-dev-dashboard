from django.urls import path
from . import views

urlpatterns = [
    path('alerts', views.alerts),
    path('summary', views.summary),
    path('alerts/<int:alert_id>/ack', views.acknowledge),
]
