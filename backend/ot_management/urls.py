from django.urls import path
from . import views

urlpatterns = [
    path('recibir-orden/', views.recibir_orden_trabajo, name='recibir_orden'),
    path('cargar-excel/', views.cargar_excel_ot, name='cargar_excel'),
    path('datos-powerbi/', views.generar_datos_powerbi, name='datos_powerbi'),
]