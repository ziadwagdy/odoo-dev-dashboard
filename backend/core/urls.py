from django.urls import path, include

urlpatterns = [
    path('api/auth/', include('apps.auth_api.urls')),
    path('api/', include('apps.projects.urls')),
    path('api/git/', include('apps.git_ops.urls')),
    path('api/settings/', include('apps.settings_app.urls')),
    path('api/notebooks/', include('apps.notebooks.urls')),
    path('api/onboard/', include('apps.onboard.urls')),
    path('api/security/', include('apps.security.urls')),
    path('api/push/', include('apps.security.push_urls')),
    path('stream/', include('apps.streams.urls')),
]
