from django.urls import path
from . import views

urlpatterns = [
    path('login',              views.login,            name='auth-login'),
    path('logout',             views.logout,           name='auth-logout'),
    path('me',                 views.me,               name='auth-me'),
    path('users',              views.list_users,       name='auth-users'),
    path('users/create',       views.create_user,      name='auth-create-user'),
    path('users/<int:user_id>/delete',   views.delete_user,      name='auth-delete-user'),
    path('users/<int:user_id>/role',     views.update_user_role, name='auth-update-role'),
    path('users/<int:user_id>/password',  views.change_password,         name='auth-change-password'),
    path('users/<int:user_id>/projects',  views.user_project_assignments, name='auth-user-projects'),
    path('audit',                         views.system_audit,             name='auth-system-audit'),
]
