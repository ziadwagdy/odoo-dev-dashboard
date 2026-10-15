from django.urls import path
from . import views

urlpatterns = [
    path('<str:project>/runtime', views.runtime_settings),
    path('<str:project>/changes/validate', views.change_validate),
    path('<str:project>/changes', views.change_create),
    path('<str:project>/changes/<int:request_id>/approve', views.change_approve),
    path('<str:project>/changes/<int:request_id>/reject', views.change_reject),
    path('<str:project>/changes/<int:request_id>/cancel', views.change_cancel),
    path('<str:project>/cron', views.cron_get),
    path('<str:project>/cron/save', views.cron_save),
]
