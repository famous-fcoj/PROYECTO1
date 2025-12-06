import json
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from datetime import datetime, date
from decimal import Decimal
from django.db.models import Count, Sum, Q
from .models import OrdenTrabajo, Tarea, Repuesto, Insumo 
from django.db.models.functions import TruncMonth

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
    # 1. KPIs
    total_ots = OrdenTrabajo.objects.count()
    pendientes = OrdenTrabajo.objects.filter(estado='PENDIENTE').count()
    proceso = OrdenTrabajo.objects.filter(estado='EN_PROCESO').count()
    finalizadas = OrdenTrabajo.objects.filter(estado='FINALIZADA').count()
    
    # 2. Tipos de Falla (Pareto Top 5)
    all_types = OrdenTrabajo.objects.values('tipo_falla').annotate(total=Count('id')).order_by('-total')
    top_types = list(all_types[:5])
    
    # Sumamos el resto en "Otros"
    rest_count = sum(item['total'] for item in all_types[5:])
    if rest_count > 0:
        top_types.append({'tipo_falla': 'Otros', 'total': rest_count})

    # 3. CARGA LABORAL POR ENCARGADO (Gráfico Barras Apiladas)
    # Esta es la lógica nueva que reemplaza a la "Evolución Mensual"
    carga = OrdenTrabajo.objects.values('encargado').annotate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado='PENDIENTE')),
        proceso=Count('id', filter=Q(estado='EN_PROCESO')),
        finalizadas=Count('id', filter=Q(estado='FINALIZADA'))
    ).order_by('-total')[:7] # Top 7 encargados

    # 4. Top Máquinas
    maquina = OrdenTrabajo.objects.values('maquina').annotate(total=Count('id')).order_by('-total')[:5]
    
    # 5. Estado General
    estado = OrdenTrabajo.objects.values('estado').annotate(total=Count('id'))

    # UN SOLO RETURN AL FINAL
    return JsonResponse({
        'resumen_estado': list(estado),
        'resumen_maquina': list(maquina),
        'resumen_tipo': top_types,
        'carga_laboral': list(carga), # Enviamos los datos para el gráfico de barras apiladas
        'kpis': {
            'total': total_ots,
            'pendientes': pendientes,
            'proceso': proceso,
            'finalizadas': finalizadas
        }
    })

# --- 6. EXCEL PROFESIONAL (DISEÑO MEJORADO) ---
def exportar_ot_excel(request, ot_num):
    ot = get_object_or_404(OrdenTrabajo, ot=ot_num)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"OT_{ot.ot}"
    
    # --- ESTILOS DEFINIDOS ---
    COLOR_PRIMARY = "1F3B4B"  # Azul Oscuro Corporativo
    COLOR_HEADER_BG = "E2E8F0" # Gris Azulado Claro
    COLOR_TEXT_WHITE = "FFFFFF"
    
    # Fuentes
    font_title = Font(name='Arial', size=16, bold=True, color=COLOR_TEXT_WHITE)
    font_section = Font(name='Arial', size=11, bold=True, color=COLOR_PRIMARY)
    font_header_table = Font(name='Arial', size=10, bold=True, color=COLOR_TEXT_WHITE)
    font_label = Font(name='Arial', size=10, bold=True, color="333333")
    font_data = Font(name='Arial', size=10, color="000000")
    
    # Bordes
    border_thick = Side(style='medium', color=COLOR_PRIMARY)
    border_thin = Side(style='thin', color="94A3B8")
    
    border_box = Border(left=border_thick, right=border_thick, top=border_thick, bottom=border_thick)
    border_cell = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
    
    # Rellenos
    fill_title = PatternFill(start_color=COLOR_PRIMARY, end_color=COLOR_PRIMARY, fill_type="solid")
    fill_header_table = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    fill_label_bg = PatternFill(start_color=COLOR_HEADER_BG, end_color=COLOR_HEADER_BG, fill_type="solid")

    # Alineación
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    # Configuración de Columnas
    ws.column_dimensions['A'].width = 6   # Index
    ws.column_dimensions['B'].width = 25  # Label 1
    ws.column_dimensions['C'].width = 35  # Value 1
    ws.column_dimensions['D'].width = 25  # Label 2
    ws.column_dimensions['E'].width = 35  # Value 2

    # --- 1. TÍTULO PRINCIPAL ---
    ws.merge_cells('A1:E2')
    title_cell = ws['A1']
    title_cell.value = f"ORDEN DE TRABAJO N° {ot.ot}"
    title_cell.font = font_title
    title_cell.fill = fill_title
    title_cell.alignment = center
    title_cell.border = border_box

    current_row = 4

    # Función Helper para filas de datos
    def draw_form_row(r, l1, v1, l2, v2):
        # Col 1
        c1 = ws.cell(row=r, column=2, value=l1)
        c1.font = font_label
        c1.fill = fill_label_bg
        c1.border = border_cell
        
        c2 = ws.cell(row=r, column=3, value=v1)
        c2.font = font_data
        c2.alignment = left
        c2.border = border_cell
        
        # Col 2
        c3 = ws.cell(row=r, column=4, value=l2)
        c3.font = font_label
        c3.fill = fill_label_bg
        c3.border = border_cell
        
        c4 = ws.cell(row=r, column=5, value=v2)
        c4.font = font_data
        c4.alignment = left
        c4.border = border_cell

    # --- DATOS GENERALES ---
    f_creacion = ot.fecha_inicio.strftime('%d/%m/%Y') if ot.fecha_inicio else '-'
    f_plan = ot.fecha_planificada.strftime('%d/%m/%Y') if ot.fecha_planificada else '-'
    
    draw_form_row(current_row, "Fecha Emisión", f_creacion, "Equipo / Máquina", ot.maquina)
    current_row += 1
    
    # Descripción (Merge)
    ws.cell(row=current_row, column=2, value="Descripción").font = font_label
    ws.cell(row=current_row, column=2).fill = fill_label_bg
    ws.cell(row=current_row, column=2).border = border_cell
    
    ws.merge_cells(f'C{current_row}:E{current_row}')
    desc_cell = ws.cell(row=current_row, column=3, value=ot.descripcion)
    desc_cell.font = font_data
    desc_cell.alignment = left
    desc_cell.border = border_cell
    ws.cell(row=current_row, column=4).border = border_cell
    ws.cell(row=current_row, column=5).border = border_cell
    current_row += 1

    draw_form_row(current_row, "Marca", ot.marca, "Modelo", ot.modelo)
    current_row += 1
    draw_form_row(current_row, "Ubicación", ot.ubicacion, "Tipo Acción", ot.tipo_accion)
    current_row += 1
    draw_form_row(current_row, "Odómetro", ot.odometro, "Responsable", ot.encargado)
    current_row += 1
    draw_form_row(current_row, "Supervisor", ot.supervisor, "Fecha Planificada", f_plan)
    current_row += 1
    draw_form_row(current_row, "Estado", ot.get_estado_display(), "Folio Interno", ot.ot)

    current_row += 2 

    # --- TABLAS DETALLE ---
    
    def draw_section_header(row, title):
        ws.merge_cells(f'A{row}:E{row}')
        cell = ws.cell(row=row, column=1, value=title)
        cell.font = font_section
        cell.alignment = Alignment(horizontal='left', vertical='bottom')
        cell.border = Border(bottom=border_thick)

    def draw_table_header(row, headers):
        for idx, h in enumerate(headers, 1):
            c = ws.cell(row=row, column=idx, value=h)
            c.font = font_header_table
            c.fill = fill_header_table
            c.alignment = center
            c.border = border_cell

    # 1. TAREAS
    draw_section_header(current_row, "1. TAREAS A EJECUTAR")
    current_row += 1
    draw_table_header(current_row, ["#", "Detalle de la Tarea", "T. Est (Hrs)", "T. Real (Hrs)", "Verificación"])
    current_row += 1
    
    tareas = ot.tareas.all()
    if not tareas:
        ws.merge_cells(f'A{current_row}:E{current_row}')
        ws.cell(row=current_row, column=1, value="No hay tareas registradas").alignment = center
        ws.cell(row=current_row, column=1).border = border_cell
        for i in range(2,6): ws.cell(row=current_row, column=i).border = border_cell
        current_row += 1
    else:
        for i, t in enumerate(tareas, 1):
            ws.cell(row=current_row, column=1, value=i).alignment = center
            ws.cell(row=current_row, column=2, value=t.detalle).alignment = left
            ws.cell(row=current_row, column=3, value=t.tiempo_estimado).alignment = center
            ws.cell(row=current_row, column=4, value=t.tiempo_real).alignment = center
            ws.cell(row=current_row, column=5, value="[   ] OK").alignment = center
            
            for col in range(1, 6): ws.cell(row=current_row, column=col).border = border_cell
            current_row += 1

    current_row += 1

    # 2. REPUESTOS E INSUMOS
    draw_section_header(current_row, "2. REPUESTOS E INSUMOS REQUERIDOS")
    current_row += 1
    draw_table_header(current_row, ["#", "Código", "Descripción del Material", "Cantidad", "Estado"])
    current_row += 1

    materiales = list(ot.repuestos.all()) + list(ot.insumos.all())
    
    if not materiales:
        ws.merge_cells(f'A{current_row}:E{current_row}')
        ws.cell(row=current_row, column=1, value="No se requieren materiales").alignment = center
        ws.cell(row=current_row, column=1).border = border_cell
        for i in range(2,6): ws.cell(row=current_row, column=i).border = border_cell
        current_row += 1
    else:
        for i, m in enumerate(materiales, 1):
            ws.cell(row=current_row, column=1, value=i).alignment = center
            ws.cell(row=current_row, column=2, value=m.codigo).alignment = center
            ws.cell(row=current_row, column=3, value=m.descripcion).alignment = left
            ws.cell(row=current_row, column=4, value=m.cantidad).alignment = center
            ws.cell(row=current_row, column=5, value="").border = border_cell 
            
            for col in range(1, 6): ws.cell(row=current_row, column=col).border = border_cell
            current_row += 1

    current_row += 2

    # --- CIERRE ---
    ws.merge_cells(f'A{current_row}:E{current_row}')
    ws.cell(row=current_row, column=1, value="OBSERVACIONES Y CIERRE").font = font_section
    ws.cell(row=current_row, column=1).border = Border(bottom=border_thick)
    current_row += 1

    ws.merge_cells(f'A{current_row}:E{current_row+3}')
    obs_cell = ws.cell(row=current_row, column=1, value=ot.observacion or "(Sin observaciones)")
    obs_cell.alignment = Alignment(horizontal='left', vertical='top')
    obs_cell.border = border_box
    current_row += 5

    # Firmas
    ws.cell(row=current_row, column=2, value="__________________________").alignment = center
    ws.cell(row=current_row, column=4, value="__________________________").alignment = center
    current_row += 1
    
    ws.cell(row=current_row, column=2, value=f"Revisado Por: {ot.revisado_por or ''}").font = font_label
    ws.cell(row=current_row, column=2).alignment = center
    
    ws.cell(row=current_row, column=4, value=f"Recibido Por: {ot.recibido_por or ''}").font = font_label
    ws.cell(row=current_row, column=4).alignment = center

    # --- NOMBRE DEL ARCHIVO CORREGIDO ---
    # Reemplaza '-' por '_' para obtener OT_1.xlsx
    clean_filename = ot.ot.replace('-', '_')
    filename = f"{clean_filename}.xlsx"

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

# --- 7. SIGUIENTE FOLIO ---
def siguiente_folio_api(request):
    numero = 1
    while True:
        folio_candidato = f'OT-{numero}'
        if not OrdenTrabajo.objects.filter(ot=folio_candidato).exists():
            break
        numero += 1
    return JsonResponse({'nuevo_folio': folio_candidato})   