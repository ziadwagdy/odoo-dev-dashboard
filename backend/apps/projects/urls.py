from django.urls import path
from . import views

urlpatterns = [
    path('config', views.api_config),
    path('status', views.api_status),
    path('restart/<str:container_name>', views.api_restart),
    path('stop/<str:container_name>', views.api_stop),
    path('logs/<str:container_name>/download', views.logs_download),
    path('db/<str:project>/list', views.db_list),
    path('db/<str:project>/backup/<str:dbname>', views.db_backup),
    path('db/<str:project>/download/<str:filename>', views.db_download),
    path('db/<str:project>/duplicate/<str:dbname>', views.db_duplicate),
    path('db/<str:project>/drop/<str:dbname>', views.db_drop),
    path('db/<str:project>/backups', views.db_backups_list),
    path('db/<str:project>/restore/<str:dbname>', views.db_restore),
    path('modules/<str:project>/<str:dbname>', views.modules_list),
    path('modules/<str:project>/<str:dbname>/update/<str:module_name>', views.module_update),
    path('project/<str:name>/deploy', views.deploy_project),
    path('project/<str:name>/history', views.deploy_history),
    path('project/<str:name>', views.project_detail),
]
