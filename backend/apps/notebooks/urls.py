from django.urls import path
from . import views

urlpatterns = [
    path('<str:project>/status', views.kernel_status),
    path('<str:project>/start', views.kernel_start),
    path('<str:project>/stop', views.kernel_stop),
]
