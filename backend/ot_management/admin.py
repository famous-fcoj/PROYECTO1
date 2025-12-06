from django.contrib import admin
from .models import OrdenTrabajo, Tarea, Repuesto, Insumo 

@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    # Agregamos 'estado' para que se vea en la lista
    list_display = ('ot', 'maquina', 'encargado', 'fecha_inicio', 'estado', 'incompleta')
    search_fields = ('ot', 'maquina', 'encargado')
    list_filter = ('incompleta', 'estado') 

admin.site.register(Tarea)
admin.site.register(Repuesto)
admin.site.register(Insumo)