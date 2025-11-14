from django.core.management.base import BaseCommand, CommandError
import pandas as pd
import os
import json
from ot_management.models import OT2025MecanicasRaw, OrdenTrabajo, Tarea, Repuesto, Insumo
import unicodedata, re


def normalize(s):
    if s is None:
        return ''
    s = str(s).strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return s.strip()


def map_row_to_models(row_dict, fila_num, filename, errors, created_counts):
    """Best-effort mapping from a row dict to OrdenTrabajo + related models.
    Updates created_counts dict with created model counts and appends to errors on failure.
    """
    try:
        # normalize keys
        norm_map = {normalize(k): k for k in row_dict.keys()}

        # helper to get original key by variants
        def find_key(*variants):
            for v in variants:
                nv = normalize(v)
                if nv in norm_map:
                    return norm_map[nv]
            return None

        # Get OT id or generate
        ot_key = find_key('ot', 'numero', 'numero ot', 'n')
        if ot_key:
            ot_val = row_dict.get(ot_key)
            ot_str = str(ot_val).strip() if ot_val is not None else None
        else:
            ot_str = f"OT-{int(__import__('time').time()*1000)}"

        # minimal fields
        encargado = None
        k = find_key('encargado', 'responsable')
        if k:
            encargado = row_dict.get(k)

        maquina = None
        k = find_key('maquina', 'equipo')
        if k:
            maquina = row_dict.get(k)

        tipo_falla = None
        k = find_key('tipo de falla', 'falla', 'tipo')
        if k:
            tipo_falla = row_dict.get(k)

        # dates and numeric
        fecha_inicio = None
        k = find_key('fecha inicio', 'fecha_inicio', 'inicio')
        if k and row_dict.get(k) is not None:
            try:
                fecha_inicio = pd.to_datetime(row_dict.get(k))
            except Exception:
                fecha_inicio = None

        fecha_termino = None
        k = find_key('fecha termino', 'fecha_termino', 'termino')
        if k and row_dict.get(k) is not None:
            try:
                fecha_termino = pd.to_datetime(row_dict.get(k))
            except Exception:
                fecha_termino = None

        try:
            dias = int(row_dict.get(find_key('dias', 'días')) or 0)
        except Exception:
            dias = 0
        try:
            personas = int(row_dict.get(find_key('personas')) or 1)
        except Exception:
            personas = 1
        try:
            hh = float(row_dict.get(find_key('hh', 'horas')) or 0)
        except Exception:
            hh = 0

        observacion = ''
        k = find_key('observacion', 'observaciones')
        if k:
            observacion = row_dict.get(k) or ''

        mantencion = 'NO'
        k = find_key('mantencion lograda', 'mantencion_lograda', 'mantencion')
        if k and row_dict.get(k) is not None:
            mantencion = str(row_dict.get(k))[:2].upper()

        # create OrdenTrabajo
        orden = OrdenTrabajo.objects.create(
            ot=ot_str,
            encargado=str(encargado) if encargado is not None else '',
            maquina=str(maquina) if maquina is not None else '',
            tipo_falla=str(tipo_falla) if tipo_falla is not None else '',
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
            dias=dias,
            personas=personas,
            hh=hh,
            observacion=str(observacion),
            mantencion_lograda=mantencion[:2] if mantencion else 'NO',
            fuente_archivo=filename,
            fila_origen=fila_num
        )
        created_counts['orden'] += 1

        # mark incomplete if main fields missing
        if not (encargado or maquina or tipo_falla):
            orden.incompleta = True
            orden.save()

        # create tareas (1..5)
        for i in range(1, 6):
            det = None
            k = find_key(f'tarea {i}', f'tarea{i}', f'detalle {i}')
            if k:
                det = row_dict.get(k)
            te = None
            k = find_key(f'tiempo estimado {i}', f'tiempo_estimado{i}')
            if k:
                try:
                    te = int(row_dict.get(k))
                except Exception:
                    te = 0
            tr = None
            k = find_key(f'tiempo real {i}', f'tiempo_real{i}')
            if k:
                try:
                    tr = int(row_dict.get(k))
                except Exception:
                    tr = 0
            if det or te or tr:
                Tarea.objects.create(
                    orden=orden,
                    numero_item=i,
                    detalle=str(det) if det is not None else '',
                    tiempo_estimado=te or 0,
                    tiempo_real=tr or 0
                )
                created_counts['tarea'] += 1

        # repuestos (1..5)
        for i in range(1, 6):
            code = None
            k = find_key(f'repuesto codigo {i}', f'codigo repuesto {i}', f'repuestocodigo{i}')
            if k:
                code = row_dict.get(k)
            desc = None
            k = find_key(f'repuesto desc {i}', f'repuestodesc{i}', f'repuesto descripcion {i}')
            if k:
                desc = row_dict.get(k)
            cant = None
            k = find_key(f'repuesto cantidad {i}', f'repuesto_cantidad{i}', f'cantidad repuesto {i}')
            if k:
                try:
                    cant = int(row_dict.get(k) or 1)
                except Exception:
                    cant = 1
            if code or desc or cant:
                Repuesto.objects.create(
                    orden=orden,
                    numero_item=i,
                    codigo=str(code) if code is not None else '',
                    descripcion=str(desc) if desc is not None else '',
                    cantidad=cant or 1
                )
                created_counts['repuesto'] += 1

        # insumos (1..5)
        for i in range(1, 6):
            code = None
            k = find_key(f'insumo codigo {i}', f'codigo insumo {i}', f'insumocodigo{i}')
            if k:
                code = row_dict.get(k)
            desc = None
            k = find_key(f'insumo desc {i}', f'insumodesc{i}', f'insumo descripcion {i}')
            if k:
                desc = row_dict.get(k)
            cant = None
            k = find_key(f'insumo cantidad {i}', f'insumo_cantidad{i}', f'cantidad insumo {i}')
            if k:
                try:
                    cant = int(row_dict.get(k) or 1)
                except Exception:
                    cant = 1
            if code or desc or cant:
                Insumo.objects.create(
                    orden=orden,
                    numero_item=i,
                    codigo=str(code) if code is not None else '',
                    descripcion=str(desc) if desc is not None else '',
                    cantidad=cant or 1
                )
                created_counts['insumo'] += 1

        return True
    except Exception as e:
        errors.append({'fila': fila_num, 'error': str(e)})
        return False


class Command(BaseCommand):
    help = 'Import every row from OT 2025 MECANICAS.xlsx into table ot_2025_mecanicas'

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='Path to the Excel (.xlsx/.xls) or CSV file to import')
        parser.add_argument('--create-mapped', action='store_true', help='Also attempt to map each row into OrdenTrabajo/Tarea/Repuesto/Insumo')

    def handle(self, *args, **options):
        filepath = options['filepath']
        if not os.path.exists(filepath):
            raise CommandError(f"File not found: {filepath}")

        filename = os.path.basename(filepath)

        # Read with pandas, support xlsx/xls/csv
        try:
            if filename.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            elif filename.lower().endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                raise CommandError('Unsupported file type. Use .xlsx, .xls or .csv')
        except Exception as e:
            raise CommandError(f'Error reading file: {e}')

        total = 0
        errors = []
        created_counts = {'orden': 0, 'tarea': 0, 'repuesto': 0, 'insumo': 0}
        do_map = options.get('create_mapped', False)

        for index, row in df.iterrows():
            try:
                fila_num = int(index) + 2
                # drop NaN to keep JSON compact
                row_dict = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                data_json = json.dumps(row_dict, default=str, ensure_ascii=False)

                OT2025MecanicasRaw.objects.create(
                    fila=fila_num,
                    data=data_json,
                    fuente_archivo=filename
                )
                total += 1
                if total % 100 == 0:
                    self.stdout.write(f'Imported {total} rows...')

                if do_map:
                    # attempt to map/create domain models
                    mapped_ok = map_row_to_models(row_dict, fila_num, filename, errors, created_counts)
                    if not mapped_ok:
                        # mapping errors are appended into errors inside the function
                        pass
            except Exception as e:
                errors.append({'fila': index + 2, 'error': str(e)})

        self.stdout.write(self.style.SUCCESS(f'Import finished. Rows stored: {total}. Errors: {len(errors)}'))
        self.stdout.write(self.style.SUCCESS(f"Domain objects created: Orden={created_counts['orden']} Tarea={created_counts['tarea']} Repuesto={created_counts['repuesto']} Insumo={created_counts['insumo']}"))
        if errors:
            self.stdout.write('Sample errors:')
            for e in errors[:10]:
                self.stdout.write(str(e))
