from django.urls import path

from . import views

urlpatterns = [
    path('validate', views.validate_project, name='onboard_validate'),
    path('start', views.start_onboard, name='onboard_start'),
    path('stream/<str:project_name>', views.stream_onboard, name='onboard_stream'),
]
