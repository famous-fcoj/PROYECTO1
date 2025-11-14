from django.contrib import admin
from .models import OT2025MecanicasRaw, OrdenTrabajo, Tarea, Repuesto, Insumo


@admin.register(OT2025MecanicasRaw)
class OT2025MecanicasRawAdmin(admin.ModelAdmin):
	list_display = ('fila', 'fuente_archivo', 'created_at')
	readonly_fields = ('data', 'fuente_archivo', 'fila', 'created_at')
	search_fields = ('fuente_archivo', 'data')
	list_filter = ('fuente_archivo',)


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
	list_display = ('ot', 'maquina', 'encargado', 'fecha_inicio', 'incompleta')
	search_fields = ('ot', 'maquina', 'encargado')
	list_filter = ('incompleta', 'mantencion_lograda')


admin.site.register(Tarea)
admin.site.register(Repuesto)
admin.site.register(Insumo)
