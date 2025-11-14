from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import OrdenTrabajo, Tarea, Repuesto, Insumo, OT2025MecanicasRaw
import pandas as pd
import json
from datetime import datetime
import unicodedata
import re
from pathlib import Path
from django.core.management import call_command
from .management.commands.map_ot2025 import Command as MapOT2025Command
import traceback

@csrf_exempt
def recibir_orden_trabajo(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("📥 Datos recibidos:", data)
            
            # Crear nueva orden de trabajo
            ot = OrdenTrabajo.objects.create(
                ot=data.get('numero_ot'),
                encargado=data.get('responsable_ejecucion', 'No especificado'),
                maquina=data.get('equipo_maquina', 'No especificado'),
                tipo_falla=data.get('tipo_falla', 'No especificado'),
                observacion=data.get('observaciones', ''),
                fecha_inicio=datetime.now(),
                personas=data.get('personas', 1),
                mantencion_lograda='NO'
            )
            # Crear tareas, repuestos e insumos si vienen en la carga
            tareas = data.get('tareas', [])
            for t in tareas:
                try:
                    Tarea.objects.create(
                        orden=ot,
                        numero_item=t.get('numero_item', 0),
                        detalle=t.get('detalle', ''),
                        tiempo_estimado=int(t.get('tiempo_estimado', 0) or 0),
                        tiempo_real=int(t.get('tiempo_real', 0) or 0)
                    )
                except Exception:
                    pass

            repuestos = data.get('repuestos', [])
            for r in repuestos:
                try:
                    Repuesto.objects.create(
                        orden=ot,
                        numero_item=r.get('numero_item', 0),
                        codigo=r.get('codigo', ''),
                        descripcion=r.get('descripcion', ''),
                        cantidad=int(r.get('cantidad', 1) or 1)
                    )
                except Exception:
                    pass

            insumos = data.get('insumos', [])
            for i in insumos:
                try:
                    Insumo.objects.create(
                        orden=ot,
                        numero_item=i.get('numero_item', 0),
                        codigo=i.get('codigo', ''),
                        descripcion=i.get('descripcion', ''),
                        cantidad=int(i.get('cantidad', 1) or 1)
                    )
                except Exception:
                    pass
            
            return JsonResponse({
                'status': 'success', 
                'message': f'✅ Orden {ot.ot} guardada correctamente. ID: {ot.id}'
            })
            
        except Exception as e:
            print("💥 Error completo:", str(e))
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
@require_http_methods(["POST"])
def cargar_excel_ot(request):
    # Check if this is a sheet-per-OT upload
    is_sheet_per_ot = request.POST.get('sheet_per_ot') == 'true'

    try:
        if 'archivo' not in request.FILES:
            return JsonResponse({
                'success': False, 
                'message': 'No se encontró archivo',
                'error_type': 'NO_FILE'
            }, status=400)
        
        archivo = request.FILES['archivo']

        # Validar extensión del archivo (aceptamos xlsx, xls y csv)
        if not archivo.name.endswith(('.xlsx', '.xls')):
            return JsonResponse({
                'success': False,
                'message': 'El archivo debe ser .xlsx o .xls',
                'error_type': 'INVALID_FORMAT'
            }, status=400)

        # If sheet-per-OT, use the map_ot2025 command to process the file
        if is_sheet_per_ot:
            temp_path = Path('temp_upload.xlsx')
            with open(temp_path, 'wb+') as f:
                for chunk in archivo.chunks():
                    f.write(chunk)
            
            try:
                # Use call_command which will populate default options defined in the command
                call_command('map_ot2025', path=str(temp_path), dry_run=False, limit=0, overwrite=True)

                # Get count of OTs created from this file (the command stores fuente_archivo=path.name)
                count = OrdenTrabajo.objects.filter(fuente_archivo=archivo.name).count()

                return JsonResponse({
                    'success': True,
                    'message': f'Carga completada: {count} OT procesadas desde hojas individuales',
                    'registros_procesados': count,
                    'errores': []
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al procesar OTs por hoja: {str(e)}',
                    'error_type': 'SHEET_PROCESS_ERROR'
                }, status=500)
            finally:
                if temp_path.exists():
                    temp_path.unlink()
        
        registros_procesados = 0
        errores = []
        
        # Leer archivo (soporta .xlsx, .xls, .csv)
        try:
            if archivo.name.endswith(('.xlsx', '.xls')):
                # intentar leer la primera hoja
                try:
                    df = pd.read_excel(archivo)
                except Exception:
                    # intentar leer todas las hojas y concatenar
                    all_sheets = pd.read_excel(archivo, sheet_name=None)
                    df = pd.concat(all_sheets.values(), ignore_index=True)
            elif archivo.name.endswith('.csv'):
                # asumir encoding utf-8 y coma como separador
                df = pd.read_csv(archivo)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Formato de archivo no soportado',
                    'error_type': 'INVALID_FORMAT'
                }, status=400)
        except Exception as e:
            # intentar leer con header=None y detectar fila de encabezado
            try:
                if archivo.name.endswith(('.xlsx', '.xls')):
                    raw = pd.read_excel(archivo, header=None)
                else:
                    raw = pd.read_csv(archivo, header=None)

                # buscar fila con palabras clave (encargado, maquina, tipo)
                def row_contains_header(r):
                    keys = ['encargado', 'maquina', 'tipo', 'fecha']
                    for v in r:
                        if v is None:
                            continue
                        s = str(v).strip().lower()
                        for k in keys:
                            if k in s:
                                return True
                    return False

                header_row = None
                for idx in range(min(10, len(raw))):
                    if row_contains_header(raw.iloc[idx].tolist()):
                        header_row = idx
                        break

                if header_row is not None:
                    if archivo.name.endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(archivo, header=header_row)
                    else:
                        df = pd.read_csv(archivo, header=header_row)
                else:
                    raise e
            except Exception as e2:
                return JsonResponse({
                    'success': False,
                    'message': 'Error al leer el archivo',
                    'error_detail': f'{str(e)} | {str(e2)}',
                    'error_type': 'READ_ERROR'
                }, status=400)

        # si df está vacío, intentamos leer todas las hojas (si aplica)
        if df is None or (hasattr(df, 'shape') and df.shape[0] == 0):
            try:
                if archivo.name.endswith(('.xlsx', '.xls')):
                    all_sheets = pd.read_excel(archivo, sheet_name=None)
                    df = pd.concat(all_sheets.values(), ignore_index=True)
            except Exception:
                pass

        # Diagnóstico inicial
        detected_columns = list(df.columns) if hasattr(df, 'columns') else []
        row_count = int(df.shape[0]) if hasattr(df, 'shape') else 0
        
        # Normalizar nombres de columnas para aceptar variaciones (sin tildes, minúsculas, guiones, etc.)
        def normalize(s):
            if s is None:
                return ''
            s = str(s)
            s = s.strip().lower()
            # quitar tildes
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(c for c in s if not unicodedata.combining(c))
            # reemplazar caracteres no alfanuméricos por espacios
            s = re.sub(r'[^a-z0-9]+', ' ', s)
            s = s.strip()
            return s

        normalized_cols = {normalize(c): c for c in df.columns}

        # Mapa de nombres esperados a variantes comunes
        expected = {
            'encargado': ['encargado', 'responsable', 'responsable de ejecucion', 'responsable_ejecucion'],
            'maquina': ['maquina', 'máquina', 'equipo', 'equipo maquina', 'equipo_maquina'],
            'tipo_falla': ['tipo de falla', 'tipo_falla', 'falla', 'tipo'],
            'fecha_inicio': ['fecha inicio', 'fecha_inicio', 'fecha de inicio', 'inicio'],
            'fecha_termino': ['fecha termino', 'fecha_termino', 'fecha de termino', 'termino'],
            'dias': ['dias', 'días'],
            'personas': ['personas'],
            'hh': ['hh', 'horas', 'horas hombre'],
            'observacion': ['observacion', 'observación', 'observaciones'],
            'mantencion_lograda': ['mantencion lograda', 'mantencion_lograda', 'mantencion', 'realizada'],
            # include variants for order id like 'orden de trabajo', 'n 001 25 m', 'orden', 'nº', 'ot'
            'ot': ['ot', 'orden de trabajo', 'orden', 'n', 'numero', 'numero ot', 'nº', 'n°', 'numero_ot']
        }

        # Construir mapping de columnas reales a nombres canónicos
        # Use substring matching between normalized variants and normalized detected column names
        column_map = {}
        for canon, variants in expected.items():
            found = False
            for v in variants:
                nv = normalize(v)
                for k, original_col in normalized_cols.items():
                    # match exact or substring in either direction (covers 'n 001 25 m' matching 'n')
                    if nv == k or nv in k or k in nv:
                        column_map[canon] = original_col
                        found = True
                        break
                if found:
                    break

        # Comprobar columnas mínimas
        required_canon = ['encargado', 'maquina', 'tipo_falla', 'fecha_inicio']
        missing = [r for r in required_canon if r not in column_map]
        # Nota: no bloqueamos la importación si faltan columnas; las filas se importarán con valores por defecto/nulos
        # pero devolvemos en la respuesta qué canónicos no se detectaron.
        
        # Procesar cada fila
        # helper: buscar columna original por variantes normalizadas
        def find_col_by_variants(*variants):
            for v in variants:
                nv = normalize(v)
                if nv in normalized_cols:
                    return normalized_cols[nv]
            return None

        # Si no se detectaron columnas canónicas, devolver diagnóstico para que el usuario adapte el Excel
        if not column_map:
            return JsonResponse({
                'success': False,
                'message': 'No se detectaron columnas canónicas en el archivo. Revisa los encabezados.',
                'detected_columns': detected_columns,
                'row_count': row_count,
                'missing': required_canon,
                'error_type': 'NO_CANONICAL_COLUMNS'
            }, status=400)

        for index, row in df.iterrows():
            try:
                # Determinar OT (si existe columna ot, usarla; si no, generar uno)
                if 'ot' in column_map:
                    ot_val = row.get(column_map['ot'], None)
                    ot_num = str(ot_val).strip() if pd.notna(ot_val) and str(ot_val).strip() else f"OT-{int(datetime.now().timestamp()*1000)}"
                else:
                    ot_num = f"OT-{int(datetime.now().timestamp()*1000)}"
                
                # Validar si la OT ya existe
                if OrdenTrabajo.objects.filter(ot=ot_num).exists():
                    errores.append({
                        'fila': index + 2,  # +2 porque Excel empieza en 1 y tiene encabezados
                        'ot': ot_num,
                        'error': 'OT ya existe en el sistema',
                        'tipo': 'DUPLICATE'
                    })
                    continue
                
                # Validar y convertir fechas usando column_map
                try:
                    fecha_inicio_col = column_map.get('fecha_inicio')
                    fecha_termino_col = column_map.get('fecha_termino')
                    fecha_inicio = pd.to_datetime(row[fecha_inicio_col]) if fecha_inicio_col and pd.notna(row.get(fecha_inicio_col, None)) else datetime.now()
                    fecha_termino = pd.to_datetime(row[fecha_termino_col]) if fecha_termino_col and pd.notna(row.get(fecha_termino_col, None)) else None
                except Exception:
                    fecha_inicio = datetime.now()
                    fecha_termino = None
                
                # Validar y convertir números
                try:
                    dias = int(row.get(column_map.get('dias', ''), 0)) if column_map.get('dias') and pd.notna(row.get(column_map.get('dias'))) else 0
                    personas = int(row.get(column_map.get('personas', ''), 1)) if column_map.get('personas') and pd.notna(row.get(column_map.get('personas'))) else 1
                    hh = float(row.get(column_map.get('hh', ''), 0)) if column_map.get('hh') and pd.notna(row.get(column_map.get('hh'))) else 0
                except ValueError as e:
                    errores.append({
                        'fila': index + 2,
                        'ot': ot_num,
                        'error': f'Error en conversión de números: {str(e)}',
                        'tipo': 'NUMBER_FORMAT'
                    })
                    continue
                
                # Determinar valores principales con no_especificado para campos faltantes
                encargado_val = None
                if 'encargado' in column_map:
                    v = row.get(column_map.get('encargado'))
                    encargado_val = str(v).strip() if pd.notna(v) and str(v).strip() else 'no_especificado'
                else:
                    encargado_val = 'no_especificado'

                maquina_val = None
                if 'maquina' in column_map:
                    v = row.get(column_map.get('maquina'))
                    maquina_val = str(v).strip() if pd.notna(v) and str(v).strip() else 'no_especificado'
                else:
                    maquina_val = 'no_especificado'

                tipo_falla_val = None
                if 'tipo_falla' in column_map:
                    v = row.get(column_map.get('tipo_falla'))
                    tipo_falla_val = str(v).strip() if pd.notna(v) and str(v).strip() else 'no_especificado'
                else:
                    tipo_falla_val = 'no_especificado'

                observacion_val = ''
                if 'observacion' in column_map:
                    obs = row.get(column_map.get('observacion'))
                    observacion_val = str(obs).strip() if pd.notna(obs) else ''

                mantencion_val = 'NO'
                if 'mantencion_lograda' in column_map:
                    m = row.get(column_map.get('mantencion_lograda'))
                    mantencion_val = str(m)[:2].upper() if pd.notna(m) else 'NO'

                ot = OrdenTrabajo.objects.create(
                    ot=ot_num,
                    encargado=encargado_val,  # Already has no_especificado as default
                    maquina=maquina_val,      # Already has no_especificado as default
                    tipo_falla=tipo_falla_val, # Already has no_especificado as default
                    fecha_inicio=fecha_inicio if fecha_inicio else datetime.now(),
                    fecha_termino=fecha_termino if fecha_termino else None,
                    dias=max(0, dias if dias is not None else 0),
                    personas=max(1, personas if personas is not None else 1),
                    hh=max(0, hh if hh is not None else 0),
                    observacion=observacion_val.strip() if observacion_val else '',
                    mantencion_lograda=mantencion_val[:2].upper() if mantencion_val and mantencion_val[:2].upper() in ['SI', 'NO'] else 'NO',
                    fuente_archivo=archivo.name,
                    fila_origen=index + 2
                )

                # Marcar incompleta si faltaron columnas canónicas o si campos principales están vacíos
                if missing or not (encargado_val or maquina_val or tipo_falla_val):
                    ot.incompleta = True
                    ot.save()

                
                # --- Parsear tareas (tarea1..tarea5, tiempoEstimado1.. etc.) ---
                for i in range(1, 6):
                    # variantes para detalle
                    det_col = find_col_by_variants(f'tarea {i}', f'tarea{i}', f'detalle {i}', f'detalle{i}', f'descripcion tarea {i}')
                    te_col = find_col_by_variants(f'tiempo estimado {i}', f'tiempo_estimado{i}', f'tiempo estimado{i}', f'tiempoestimado{i}')
                    tr_col = find_col_by_variants(f'tiempo real {i}', f'tiempo_real{i}', f'tiempo real{i}', f'tiemporeal{i}')
                    detalle = None
                    if det_col:
                        v = row.get(det_col)
                        detalle = str(v).strip() if pd.notna(v) and str(v).strip() else None
                    tiempo_estimado = None
                    if te_col:
                        v = row.get(te_col)
                        try:
                            tiempo_estimado = int(v) if pd.notna(v) and str(v).strip() else None
                        except Exception:
                            tiempo_estimado = None
                    tiempo_real = None
                    if tr_col:
                        v = row.get(tr_col)
                        try:
                            tiempo_real = int(v) if pd.notna(v) and str(v).strip() else None
                        except Exception:
                            tiempo_real = None

                    if detalle or tiempo_estimado is not None or tiempo_real is not None:
                        Tarea.objects.create(
                            orden=ot,
                            numero_item=i,
                            detalle=detalle or '',
                            tiempo_estimado=tiempo_estimado or 0,
                            tiempo_real=tiempo_real or 0
                        )

                # --- Parsear repuestos (repuestoCodigo1..5, repuestoDesc1..5, repuestoCantidad1..5) ---
                for i in range(1, 6):
                    code_col = find_col_by_variants(f'repuesto codigo {i}', f'repuestocodigo{i}', f'repuesto_codigo{i}', f'codigo repuesto {i}', f'codigo_repuesto{i}')
                    desc_col = find_col_by_variants(f'repuesto desc {i}', f'repuesto desc{i}', f'repuesto descripcion {i}', f'repuestodesc{i}')
                    cant_col = find_col_by_variants(f'repuesto cantidad {i}', f'repuesto_cantidad{i}', f'repuestocantidad{i}', f'cantidad repuesto {i}')
                    code = None
                    if code_col:
                        v = row.get(code_col)
                        code = str(v).strip() if pd.notna(v) and str(v).strip() else None
                    desc = None
                    if desc_col:
                        v = row.get(desc_col)
                        desc = str(v).strip() if pd.notna(v) and str(v).strip() else None
                    cantidad = None
                    if cant_col:
                        v = row.get(cant_col)
                        try:
                            cantidad = int(v) if pd.notna(v) and str(v).strip() else None
                        except Exception:
                            cantidad = None

                    if code or desc or cantidad is not None:
                        Repuesto.objects.create(
                            orden=ot,
                            numero_item=i,
                            codigo=code or '',
                            descripcion=desc or '',
                            cantidad=cantidad or 1
                        )

                # --- Parsear insumos (insumoCodigo1..5 etc.) ---
                for i in range(1, 6):
                    code_col = find_col_by_variants(f'insumo codigo {i}', f'insumocodigo{i}', f'insumo_codigo{i}', f'codigo insumo {i}')
                    desc_col = find_col_by_variants(f'insumo desc {i}', f'insumo desc{i}', f'insumo descripcion {i}', f'insumodesc{i}')
                    cant_col = find_col_by_variants(f'insumo cantidad {i}', f'insumo_cantidad{i}', f'insumocantidad{i}', f'cantidad insumo {i}')
                    code = None
                    if code_col:
                        v = row.get(code_col)
                        code = str(v).strip() if pd.notna(v) and str(v).strip() else None
                    desc = None
                    if desc_col:
                        v = row.get(desc_col)
                        desc = str(v).strip() if pd.notna(v) and str(v).strip() else None
                    cantidad = None
                    if cant_col:
                        v = row.get(cant_col)
                        try:
                            cantidad = int(v) if pd.notna(v) and str(v).strip() else None
                        except Exception:
                            cantidad = None

                    if code or desc or cantidad is not None:
                        Insumo.objects.create(
                            orden=ot,
                            numero_item=i,
                            codigo=code or '',
                            descripcion=desc or '',
                            cantidad=cantidad or 1
                        )
                registros_procesados += 1
                
            except Exception as e:
                errores.append({
                    'fila': index + 2,
                    'ot': ot_num if 'ot_num' in locals() else 'N/A',
                    'error': str(e),
                    'tipo': 'GENERAL'
                })
        
        return JsonResponse({
            'success': True,
            'message': f'Carga completada: {registros_procesados} OT procesadas',
            'registros_procesados': registros_procesados,
            'errores': errores,
            'total_errores': len(errores)
        })
        
    except Exception as e:
        tb = traceback.format_exc()
        # log to server stdout
        print('💥 Error general en cargar_excel_ot:', str(e))
        print(tb)
        return JsonResponse({
            'success': False,
            'message': 'Error general en el procesamiento',
            'error_detail': str(e),
            'traceback': tb,
            'error_type': 'GENERAL_ERROR'
        }, status=500)

@require_http_methods(["GET"])
def generar_datos_powerbi(request):
    """Endpoint para generar datos para Power BI con mejor manejo de nulos"""
    from django.db.models import Count, Sum, Avg, Q, Case, When, F, Value, CharField
    from django.db.models.functions import Coalesce, ExtractYear, ExtractMonth
    
    # Datos de mantenciones por encargado (agrupando no_especificado)
    encargados_data = OrdenTrabajo.objects.annotate(
        encargado_norm=Case(
            When(encargado__in=['', None, 'no_especificado'], then=Value('No Especificado')),
            default='encargado',
            output_field=CharField()
        )
    ).values('encargado_norm').annotate(
        total_ot=Count('id'),
        total_horas=Coalesce(Sum('hh'), 0.0),
        promedio_horas=Coalesce(Avg('hh'), 0.0)
    ).order_by('-total_ot')
    
    # Datos de mantenciones por tipo de falla (agrupando no_especificado)
    fallas_data = OrdenTrabajo.objects.annotate(
        tipo_falla_norm=Case(
            When(tipo_falla__in=['', None, 'no_especificado'], then=Value('No Especificado')),
            default='tipo_falla',
            output_field=CharField()
        )
    ).values('tipo_falla_norm').annotate(
        total_mantenciones=Count('id'),
        total_horas=Coalesce(Sum('hh'), 0.0)
    ).order_by('-total_mantenciones')
    
    # Datos temporales (por mes) con valores default para nulos
    temporal_data = OrdenTrabajo.objects.annotate(
        año=ExtractYear('fecha_inicio'),
        mes=ExtractMonth('fecha_inicio'),
        encargado_norm=Case(
            When(encargado__in=['', None, 'no_especificado'], then=Value('No Especificado')),
            default='encargado',
            output_field=CharField()
        ),
        tipo_falla_norm=Case(
            When(tipo_falla__in=['', None, 'no_especificado'], then=Value('No Especificado')),
            default='tipo_falla',
            output_field=CharField()
        )
    ).values('año', 'mes', 'encargado_norm', 'tipo_falla_norm').annotate(
        cantidad_ot=Count('id'),
        horas_totales=Coalesce(Sum('hh'), 0.0)
    ).order_by('año', 'mes')
    
    # Eficiencia de mantención (SI/NO) con porcentajes
    total_ot = OrdenTrabajo.objects.count()
    eficiencia_data = OrdenTrabajo.objects.values('mantencion_lograda').annotate(
        cantidad=Count('id'),
        porcentaje=Case(
            When(total_ot__gt=0, then=100.0 * Count('id') / total_ot),
            default=Value(0.0)
        )
    ).order_by('-cantidad')
    
    response_data = {
        'encargados': list(encargados_data),
        'tipos_falla': list(fallas_data),
        'temporal': list(temporal_data),
        'eficiencia': list(eficiencia_data),
        'fecha_generacion': datetime.now().isoformat()
    }
    
    return JsonResponse(response_data)