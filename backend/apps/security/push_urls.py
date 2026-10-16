from django.urls import path
from . import push_views

urlpatterns = [
    path('public-key', push_views.public_key),
    path('subscribe', push_views.subscribe),
    path('unsubscribe', push_views.unsubscribe),
    path('test', push_views.test_notification),
]
