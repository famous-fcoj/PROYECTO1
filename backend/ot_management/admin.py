from django.contrib import admin
# OT2025MecanicasRaw ELIMINADO de la importación
from .models import OrdenTrabajo, Tarea, Repuesto, Insumo 


# @admin.register(OT2025MecanicasRaw) ELIMINADO
# class OT2025MecanicasRawAdmin(admin.ModelAdmin): ELIMINADO
#   ... ELIMINADO


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ('ot', 'maquina', 'encargado', 'fecha_inicio', 'incompleta')
    search_fields = ('ot', 'maquina', 'encargado')
    list_filter = ('incompleta', 'mantencion_lograda')


admin.site.register(Tarea)
admin.site.register(Repuesto)
admin.site.register(Insumo)