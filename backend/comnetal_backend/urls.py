from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ot_management.urls')),  # Esto incluye las URLs de tu app
]