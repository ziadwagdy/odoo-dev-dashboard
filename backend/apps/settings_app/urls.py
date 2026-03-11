from django.urls import path
from . import views

urlpatterns = [
    path('<str:project>/odoo-conf', views.odoo_conf_read),
    path('<str:project>/odoo-conf/write', views.odoo_conf_write),
    path('<str:project>/env', views.env_read),
    path('<str:project>/env/write', views.env_write),
    path('<str:project>/cron', views.cron_get),
    path('<str:project>/cron/save', views.cron_save),
]
