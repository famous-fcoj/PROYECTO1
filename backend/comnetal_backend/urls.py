from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Esta línea es la única necesaria, redirige todo a tu app
    path('', include('ot_management.urls')), 
]