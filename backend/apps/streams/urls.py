from django.urls import path
from . import views

urlpatterns = [
    path('status', views.stream_status),
    path('deploy/<str:name>', views.stream_deploy),
    path('logs/<str:name>', views.stream_logs),
    path('stats/<str:container_name>', views.stream_stats),
    path('module-update/<str:project>/<str:dbname>/<str:module_name>', views.stream_module_update),
    path('branch-switch/<str:project>', views.stream_branch_switch),
    path('submodule-update/<str:project>', views.stream_submodule_update),
    path('git-pull/<str:project>', views.stream_git_pull),
    path('health/host', views.stream_health_host),
    path('health/containers', views.stream_health_containers),
]
