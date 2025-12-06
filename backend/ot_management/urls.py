from django.urls import path
from . import views

urlpatterns = [
    path('recibir-orden/', views.recibir_orden_trabajo, name='recibir_orden'),
    path('api/lista-ots/', views.lista_ots_api, name='api_lista'),
    path('api/detalle-ot/<str:ot_num>/', views.detalle_ot_api, name='api_detalle'),
    path('api/eliminar-ot/<str:ot_num>/', views.eliminar_ot_api, name='api_eliminar'),
    path('api/ot-resumen/', views.ot_resumen_api, name='ot_resumen_api'),
    path('api/exportar-excel/<str:ot_num>/', views.exportar_ot_excel, name='exportar_excel'),
    path('api/siguiente-folio/', views.siguiente_folio_api, name='siguiente_folio'),
    path('api/exportar-pdf/<str:ot_num>/', views.exportar_ot_pdf, name='exportar_pdf'),
]