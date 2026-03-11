from django.urls import path
from . import views

urlpatterns = [
    path('<str:project>/branches', views.git_branches),
    path('<str:project>/switch', views.git_switch),
    path('<str:project>/submodules', views.git_submodules),
    path('<str:project>/submodule-update', views.git_submodule_update),
    path('<str:project>/pull', views.git_pull_view),
]
