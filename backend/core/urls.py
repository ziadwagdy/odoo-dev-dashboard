from django.urls import path, include

urlpatterns = [
    path('api/', include('apps.projects.urls')),
    path('api/git/', include('apps.git_ops.urls')),
    path('api/settings/', include('apps.settings_app.urls')),
    path('api/notebooks/', include('apps.notebooks.urls')),
    path('stream/', include('apps.streams.urls')),
]
