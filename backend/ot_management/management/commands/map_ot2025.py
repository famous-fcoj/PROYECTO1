from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import pandas as pd
import unicodedata
from pathlib import Path
import re

from ot_management.models import OrdenTrabajo, Tarea, Repuesto, Insumo, OT2025MecanicasRaw

BASE = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_PATH = (BASE / 'OT 2025 MECANICAS.xlsx').resolve()

def normalize(s):
    if s is None:
        return ''
    s = str(s)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()

def safe_iat(df, r, c):
    # Return None if out of bounds
    if r < 0 or c < 0:
        return None
    if r >= df.shape[0] or c >= df.shape[1]:
        return None
    try:
        v = df.iat[r, c]
    except Exception:
        return None
    return v

def get_adjacent_value(df, r, c):
    # try right cells then below with bounds checks
    for dc in [1,2,3]:
        v = safe_iat(df, r, c+dc)
        if v is not None and str(v).strip():
            return str(v).strip()
    for dr in [1,2]:
        v = safe_iat(df, r+dr, c)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None

def find_cell(df, needle):
    n = normalize(needle)
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            v = safe_iat(df, r, c)
            if v is None:
                continue
            if n in normalize(v):
                return r, c, v
    return None


class Command(BaseCommand):
    help = 'Map formatted "OT 2025 MECANICAS.xlsx" (sheet-per-OT) into OrdenTrabajo/Tarea/Repuesto/Insumo. Use --dry-run first.'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, help='Path to XLSX file', default=str(DEFAULT_PATH))
        parser.add_argument('--dry-run', action='store_true', help='Parse and report without saving DB objects')
        parser.add_argument('--limit', type=int, help='Limit number of sheets to process', default=0)
        parser.add_argument('--overwrite', action='store_true', help='If an OT exists, delete and replace it')

    def handle(self, *args, **options):
        path = Path(options['path']).expanduser().resolve()
        dry_run = options['dry_run']
        limit = options['limit'] or 0

        if not path.exists():
            raise CommandError(f'File not found: {path}')

        self.stdout.write(f'Mapping formatted XLSX: {path}  (dry-run={dry_run})')

        xls = pd.ExcelFile(str(path))
        created = {'orden':0, 'tarea':0, 'repuesto':0, 'insumo':0}
        errors = []

        for i, sheet in enumerate(xls.sheet_names):
            if limit and i >= limit:
                break
            try:
                df = xls.parse(sheet_name=sheet, header=None, dtype=str)
                # store raw sheet dump for traceability
                try:
                    raw_data = df.fillna('').to_json(orient='split', force_ascii=False)
                    if not dry_run:
                        OT2025MecanicasRaw.objects.create(fila=i+1, data=raw_data, fuente_archivo=path.name)
                except Exception as e:
                    # continue but log
                    errors.append({'sheet': sheet, 'error': f'raw_store_error: {e}'} )

                # find OT number cell (contains 'N°:')
                cell = find_cell(df, 'n°') or find_cell(df, 'n:') or find_cell(df, 'nº')
                if cell:
                    r,c,v = cell
                    ot_str = str(v).strip()
                else:
                    ot_str = sheet

                def normalize_ot(s):
                    if not s:
                        return s
                    s = str(s)
                    # try to extract patterns like 001 - 25 or 001-25
                    m = re.search(r"(\d+\s*-\s*\d+)", s)
                    if m:
                        return m.group(1).replace(' ', '')
                    # fallback: remove common prefixes and collapse whitespace
                    s2 = re.sub(r"n\s*[:º-]*", '', s, flags=re.IGNORECASE)
                    s2 = re.sub(r"[^A-Za-z0-9\-]", ' ', s2)
                    s2 = re.sub(r"\s+", ' ', s2).strip()
                    return s2

                ot_key = normalize_ot(ot_str)
                overwrite = options.get('overwrite', False)

                # Fecha
                fecha = None
                cell = find_cell(df, 'fecha')
                if cell:
                    r,c,_ = cell
                    raw_fecha = get_adjacent_value(df, r, c)
                    try:
                        fecha = pd.to_datetime(raw_fecha, errors='coerce') if raw_fecha else None
                    except Exception:
                        fecha = None

                # Equipo/Maquina
                maquina = None
                cell = find_cell(df, 'equipo/maquina') or find_cell(df, 'equipo')
                if cell:
                    r,c,_ = cell
                    maquina = get_adjacent_value(df, r, c)

                # Descripcion
                descripcion = None
                cell = find_cell(df, 'descripcion')
                if cell:
                    r,c,_ = cell
                    descripcion = get_adjacent_value(df, r, c)

                # Responsable
                encargado = None
                cell = find_cell(df, 'responsable de ejecucion') or find_cell(df, 'responsable')
                if cell:
                    r,c,_ = cell
                    encargado = get_adjacent_value(df, r, c)

                # Build object but optionally don't save (dry-run)
                try:
                    # deduplicate based on normalized OT key
                    # Try to find existing by simple filters first
                    existing_qs = None
                    if ot_key:
                        existing_qs = OrdenTrabajo.objects.filter(ot__icontains=ot_key)
                    else:
                        existing_qs = OrdenTrabajo.objects.filter(ot__iexact=ot_str)

                    # If the simple query didn't find anything, try a normalized match in Python
                    if not existing_qs.exists():
                        candidates = []
                        for o in OrdenTrabajo.objects.all():
                            try:
                                existing_norm = normalize_ot(o.ot)
                            except Exception:
                                existing_norm = ''
                            if ot_key and existing_norm and ot_key and (existing_norm == ot_key or ot_key in existing_norm or existing_norm in ot_key):
                                candidates.append(o.id)
                            elif not ot_key and o.ot == ot_str:
                                candidates.append(o.id)
                        if candidates:
                            existing_qs = OrdenTrabajo.objects.filter(id__in=candidates)

                    if existing_qs and existing_qs.exists():
                        if overwrite and not dry_run:
                            # delete existing and allow creation below
                            cnt = existing_qs.count()
                            existing_qs.delete()
                            self.stdout.write(f'OT existed, deleted prior to overwrite ({cnt} rows): {ot_key or ot_str}')
                        else:
                            self.stdout.write(f'OT exists, skipping: {ot_str}')
                            continue

                    # Create the OrdenTrabajo (or count in dry-run)
                    if dry_run:
                        created['orden'] += 1
                        orden = None
                    else:
                        # wrap creation in a transaction for safety
                        with transaction.atomic():
                            orden = OrdenTrabajo.objects.create(
                                ot=ot_str,
                                encargado=encargado or '',
                                maquina=maquina or '',
                                tipo_falla='',
                                fecha_inicio=fecha.to_pydatetime() if fecha is not None and not pd.isna(fecha) else None,
                                observacion=descripcion or '',
                                fuente_archivo=path.name
                            )
                        created['orden'] += 1

                        # parse tareas
                        task_cell = find_cell(df, 'tareas a ejecutar')
                        if task_cell:
                            tr,tc,_ = task_cell
                            # assume tasks start a few rows below header
                            for rr in range(tr+1, df.shape[0]):
                                item = safe_iat(df, rr, 0)
                                if item is None or not str(item).strip().isdigit():
                                    # stop when next section header or blank
                                    val0 = safe_iat(df, rr, 0) or ''
                                    if 'repuestos' in normalize(val0) or 'insumos' in normalize(val0):
                                        break
                                    continue
                                detalle = safe_iat(df, rr, 1) or ''
                                tiempo = None
                                for cc in range(2, min(6, df.shape[1])):
                                    val = safe_iat(df, rr, cc)
                                    if val is not None and any(ch.isdigit() for ch in str(val)):
                                        tiempo = str(val)
                                        break
                                if dry_run:
                                    created['tarea'] += 1
                                else:
                                    Tarea.objects.create(orden=orden, numero_item=int(str(item).strip()), detalle=str(detalle), tiempo_estimado=0, tiempo_real=0)
                                    created['tarea'] += 1

                        # repuestos
                        rep_cell = find_cell(df, 'repuestos requeridos') or find_cell(df, 'repuestos')
                        if rep_cell:
                            rr,rc,_ = rep_cell
                            for rrr in range(rr+1, df.shape[0]):
                                itm = safe_iat(df, rrr, 0)
                                if itm is None or (isinstance(itm, str) and not itm.strip()):
                                    val0 = safe_iat(df, rrr, 0) or ''
                                    if 'insumos' in normalize(val0):
                                        break
                                    continue
                                codigo = safe_iat(df, rrr, 1) or ''
                                desc = safe_iat(df, rrr, 2) or ''
                                cantidad = 1
                                try:
                                    raw_cant = safe_iat(df, rrr, 3)
                                    if raw_cant is not None and str(raw_cant).strip().isdigit():
                                        cantidad = int(str(raw_cant).strip())
                                except Exception:
                                    cantidad = 1
                                if dry_run:
                                    created['repuesto'] += 1
                                else:
                                    Repuesto.objects.create(orden=orden, numero_item=int(str(itm).strip()) if str(itm).strip().isdigit() else 1, codigo=str(codigo) if codigo else '', descripcion=str(desc) if desc else '', cantidad=cantidad)
                                    created['repuesto'] += 1

                        # insumos (same approach)
                        ins_cell = find_cell(df, 'insumos requeridos') or find_cell(df, 'insumos')
                        if ins_cell:
                            ir,ic,_ = ins_cell
                            for rrr in range(ir+1, df.shape[0]):
                                itm = safe_iat(df, rrr, 0)
                                if itm is None or (isinstance(itm, str) and not itm.strip()):
                                    val0 = safe_iat(df, rrr, 0) or ''
                                    if 'finalizacion' in normalize(val0) or 'firmas' in normalize(val0):
                                        break
                                    continue
                                codigo = safe_iat(df, rrr, 1) or ''
                                desc = safe_iat(df, rrr, 2) or ''
                                cantidad = 1
                                try:
                                    raw_cant = safe_iat(df, rrr, 3)
                                    if raw_cant is not None and str(raw_cant).strip().isdigit():
                                        cantidad = int(str(raw_cant).strip())
                                except Exception:
                                    cantidad = 1
                                if dry_run:
                                    created['insumo'] += 1
                                else:
                                    Insumo.objects.create(orden=orden, numero_item=int(str(itm).strip()) if str(itm).strip().isdigit() else 1, codigo=str(codigo) if codigo else '', descripcion=str(desc) if desc else '', cantidad=cantidad)
                                    created['insumo'] += 1

                except Exception as e:
                    errors.append({'sheet': sheet, 'error': str(e)})
                    self.stderr.write(f'Error mapping sheet {sheet} {e}')
            except Exception as e:
                errors.append({'sheet': sheet, 'error': str(e)})
                self.stderr.write(f'Error reading sheet {sheet} {e}')

        self.stdout.write(f'Mapping finished. created: {created} errors: {errors[:20]}')
