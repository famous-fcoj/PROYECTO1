import json
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from datetime import datetime, date
from decimal import Decimal
from django.db.models import Count
from .models import OrdenTrabajo, Tarea, Repuesto, Insumo 

# --- HELPER ---
def safe_cast(data, field_name, cast_type):
    value = data.get(field_name)
    if value in (None, '', 'null'): return None
    if cast_type == date:
        try: return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError: return None 
    if cast_type == datetime:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return datetime(dt.year, dt.month, dt.day, 0, 0, 0)
        except ValueError: return None
    if cast_type == int:
        try: return int(value)
        except: return 0 
    if cast_type == Decimal:
        try: return Decimal(str(value)) 
        except: return Decimal(0)
    return str(value).strip()

# --- 1. GUARDAR ---
@csrf_exempt 
def recibir_orden_trabajo(request): 
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tareas = data.pop('tareas', [])
            repuestos = data.pop('repuestos', [])
            insumos = data.pop('insumos', [])
            
            ot_data = {
                'ot': data.get('numero_ot'),
                'encargado': data.get('responsable_ejecucion'),
                'maquina': data.get('equipo_maquina'),
                'descripcion': data.get('descripcion'),
                'marca': data.get('marca'),
                'ubicacion': data.get('ubicacion'),
                'modelo': data.get('modelo'),
                'tipo_accion': data.get('tipo_accion'),
                'tipo_falla': data.get('tipo_accion'),
                'odometro': safe_cast(data, 'odometro', int),
                'supervisor': data.get('supervisor'),
                'fecha_planificada': safe_cast(data, 'fechaPlanificada', date),
                'fecha_inicio': safe_cast(data, 'fechaCreacion', datetime),
                'revisado_por': data.get('revisadoPor'),
                'fecha_revision': safe_cast(data, 'fechaRevision', date),
                'recibido_por': data.get('recibidoPor'),
                'observacion': data.get('observaciones'),
                # CORRECCIÓN: Usamos 'estado' en lugar de 'mantencion_lograda'
                'estado': data.get('estado', 'PENDIENTE')
            }
            ot_data = {k: v for k, v in ot_data.items() if v is not None}
            ot_num = ot_data.pop('ot')
            
            ot_obj, created = OrdenTrabajo.objects.get_or_create(ot=ot_num, defaults=ot_data)
            if not created:
                for k, v in ot_data.items(): setattr(ot_obj, k, v)
                ot_obj.save()
            
            ot_obj.tareas.all().delete()
            ot_obj.repuestos.all().delete()
            ot_obj.insumos.all().delete()
            
            for i, t in enumerate(tareas, 1): Tarea.objects.create(orden=ot_obj, numero_item=i, **t)
            for i, r in enumerate(repuestos, 1): Repuesto.objects.create(orden=ot_obj, numero_item=i, **r)
            for i, ins in enumerate(insumos, 1): Insumo.objects.create(orden=ot_obj, numero_item=i, **ins)

            return JsonResponse({'status': 'success', 'message': 'Guardado OK', 'numero_ot': ot_obj.ot})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# --- 2. LISTAR ---
def lista_ots_api(request):
    ordenes = OrdenTrabajo.objects.all().order_by('-created_at')
    data = []
    for o in ordenes:
        data.append({
            'ot': o.ot,
            'fecha': o.fecha_inicio.strftime('%Y-%m-%d') if o.fecha_inicio else '-',
            'maquina': o.maquina,
            'encargado': o.encargado,
            # CORRECCIÓN: Leemos 'estado', ya no existe 'mantencion_lograda'
            'estado': o.estado
        })
    return JsonResponse({'ordenes': data})

# --- 3. DETALLE ---
def detalle_ot_api(request, ot_num):
    ot = get_object_or_404(OrdenTrabajo, ot=ot_num)
    data = {
        'numero_ot': ot.ot,
        'fechaCreacion': ot.fecha_inicio.strftime('%Y-%m-%d') if ot.fecha_inicio else '',
        'equipo_maquina': ot.maquina,
        'descripcion': ot.descripcion,
        'marca': ot.marca,
        'ubicacion': ot.ubicacion,
        'modelo': ot.modelo,
        'tipo_accion': ot.tipo_accion,
        'odometro': ot.odometro,
        'responsable_ejecucion': ot.encargado,
        'fechaPlanificada': ot.fecha_planificada.strftime('%Y-%m-%d') if ot.fecha_planificada else '',
        'supervisor': ot.supervisor,
        'revisadoPor': ot.revisado_por,
        'fechaRevision': ot.fecha_revision.strftime('%Y-%m-%d') if ot.fecha_revision else '',
        'recibidoPor': ot.recibido_por,
        'observaciones': ot.observacion,
        # CORRECCIÓN: Agregamos el estado
        'estado': ot.estado,
        'tareas': list(ot.tareas.values('detalle', 'tiempo_estimado', 'tiempo_real')),
        'repuestos': list(ot.repuestos.values('codigo', 'descripcion', 'cantidad')),
        'insumos': list(ot.insumos.values('codigo', 'descripcion', 'cantidad'))
    }
    return JsonResponse(data)

# --- 4. ELIMINAR ---
@csrf_exempt
def eliminar_ot_api(request, ot_num):
    if request.method == 'POST':
        try:
            ot = OrdenTrabajo.objects.get(ot=ot_num)
            ot.delete()
            return JsonResponse({'status': 'success'})
        except:
            return JsonResponse({'status': 'error'}, status=404)
    return JsonResponse({'status': 'error'}, status=400)

# --- 5. RESUMEN ---
def ot_resumen_api(request):
    # CORRECCIÓN: Agrupamos por 'estado', ya no por 'mantencion_lograda'
    estado = OrdenTrabajo.objects.values('estado').annotate(total=Count('id'))
    encargado = OrdenTrabajo.objects.values('encargado').annotate(total=Count('id')).order_by('-total')[:10]
    ubicacion = OrdenTrabajo.objects.values('ubicacion').annotate(total=Count('id')).order_by('-total')
    tipo = OrdenTrabajo.objects.values('tipo_accion').annotate(total=Count('id')).order_by('-total')
    maquina = OrdenTrabajo.objects.values('maquina').annotate(total=Count('id')).order_by('-total')[:10]
    return JsonResponse({
        'resumen_estado': list(estado), 'resumen_encargado': list(encargado),
        'resumen_ubicacion': list(ubicacion), 'resumen_tipo': list(tipo), 'resumen_maquina': list(maquina)
    })

# --- 6. EXCEL ---
def exportar_ot_excel(request, ot_num):
    ot = get_object_or_404(OrdenTrabajo, ot=ot_num)
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = f"OT_{ot.ot}"
    ws['A1'] = f"OT: {ot.ot}"
    ws['A2'] = f"Máquina: {ot.maquina}"
    ws['A3'] = f"Encargado: {ot.encargado}"
    # CORRECCIÓN: Usamos el método para obtener el nombre legible del estado
    ws['A4'] = f"Estado: {ot.get_estado_display()}" 
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="OT_{ot.ot}.xlsx"'
    wb.save(response)
    return response

# --- 7. SIGUIENTE FOLIO ---
def siguiente_folio_api(request):
    """
    Busca el primer número de OT disponible empezando desde el 1.
    Si existe OT-1, prueba OT-2. Si existe OT-2, prueba OT-3.
    """
    numero = 1
    while True:
        folio_candidato = f'OT-{numero}'
        if not OrdenTrabajo.objects.filter(ot=folio_candidato).exists():
            break
        numero += 1

    return JsonResponse({'nuevo_folio': folio_candidato})