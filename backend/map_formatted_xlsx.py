import os
import django
import pandas as pd
import unicodedata, re
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comnetal_backend.settings')
django.setup()

BASE = Path(__file__).resolve().parent
PATH = BASE / '..' / 'OT 2025 MECANICAS.xlsx'
PATH = PATH.resolve()
print('Mapping formatted XLSX:', PATH)

def normalize(s):
    if s is None:
        return ''
    s = str(s)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()

def get_adjacent_value(df, r, c):
    # try right cells then below
    for dc in [1,2,3]:
        try:
            v = df.iat[r, c+dc]
            if pd.notna(v) and str(v).strip():
                return str(v).strip()
        except Exception:
            pass
    for dr in [1,2]:
        try:
            v = df.iat[r+dr, c]
            if pd.notna(v) and str(v).strip():
                return str(v).strip()
        except Exception:
            pass
    return None

def find_cell(df, needle):
    n = normalize(needle)
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if pd.isna(v):
                continue
            if n in normalize(v):
                return r, c, v
    return None

from ot_management.models import OrdenTrabajo, Tarea, Repuesto, Insumo
created = {'orden':0, 'tarea':0, 'repuesto':0, 'insumo':0}
errors = []

xls = pd.ExcelFile(str(PATH))
for sheet in xls.sheet_names:
    try:
        df = xls.parse(sheet_name=sheet, header=None, dtype=str)
        # find OT number cell (contains 'N°:')
        cell = find_cell(df, 'n°') or find_cell(df, 'n:') or find_cell(df, 'nº')
        if cell:
            r,c,v = cell
            ot_str = str(v).strip()
        else:
            ot_str = sheet

        # Fecha
        fecha = None
        cell = find_cell(df, 'fecha')
        if cell:
            r,c,_ = cell
            fecha = get_adjacent_value(df, r, c)

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

        # Create OrdenTrabajo (best-effort)
        try:
            if OrdenTrabajo.objects.filter(ot=ot_str).exists():
                print('OT exists, skipping:', ot_str)
            else:
                orden = OrdenTrabajo.objects.create(
                    ot=ot_str,
                    encargado=encargado or '',
                    maquina=maquina or '',
                    tipo_falla='',
                    fecha_inicio=fecha or None,
                    observacion=descripcion or '',
                    fuente_archivo=str(PATH.name)
                )
                created['orden'] += 1

                # parse tareas
                # find 'TAREAS A EJECUTAR' then subsequent rows that start with item numbers
                task_cell = find_cell(df, 'tareas a ejecutar')
                if task_cell:
                    tr,tc,_ = task_cell
                    # assume tasks start a few rows below header
                    for rr in range(tr+2, tr+20):
                        try:
                            item = df.iat[rr,0]
                        except Exception:
                            item = None
                        if pd.isna(item) or not str(item).strip().isdigit():
                            # stop if we hit an empty or non-digit and next header 'REPUESTOS'
                            if 'repuestos' in normalize(str(df.iat[rr,0] if not pd.isna(df.iat[rr,0]) else '')):
                                break
                            continue
                        detalle = df.iat[rr,1] if pd.notna(df.iat[rr,1]) else ''
                        tiempo = None
                        # search for time in later columns
                        for cc in range(2,6):
                            try:
                                val = df.iat[rr,cc]
                                if pd.notna(val) and any(ch.isdigit() for ch in str(val)):
                                    tiempo = str(val)
                                    break
                            except Exception:
                                pass
                        Tarea.objects.create(orden=orden, numero_item=int(str(item).strip()), detalle=str(detalle), tiempo_estimado=0, tiempo_real=0)
                        created['tarea'] += 1

                # repuestos
                rep_cell = find_cell(df, 'repuestos requeridos')
                if rep_cell:
                    rr,rc,_ = rep_cell
                    for rrr in range(rr+2, rr+40):
                        try:
                            itm = df.iat[rrr,0]
                        except Exception:
                            itm = None
                        if pd.isna(itm):
                            # end when blank block or next section
                            if 'insumos' in normalize(str(df.iat[rrr,0] if not pd.isna(df.iat[rrr,0]) else '')):
                                break
                            continue
                        # description possibly in col2
                        codigo = df.iat[rrr,1] if pd.notna(df.iat[rrr,1]) else ''
                        desc = df.iat[rrr,2] if pd.notna(df.iat[rrr,2]) else ''
                        cantidad = None
                        try:
                            cantidad = int(df.iat[rrr,3]) if pd.notna(df.iat[rrr,3]) else 1
                        except Exception:
                            cantidad = 1
                        Repuesto.objects.create(orden=orden, numero_item=int(str(itm).strip()) if str(itm).strip().isdigit() else 1, codigo=str(codigo) if codigo else '', descripcion=str(desc) if desc else '', cantidad=cantidad)
                        created['repuesto'] += 1

        except Exception as e:
            errors.append({'sheet': sheet, 'error': str(e)})
            print('Error mapping sheet', sheet, e)
    except Exception as e:
        errors.append({'sheet': sheet, 'error': str(e)})
        print('Error reading sheet', sheet, e)

print('Mapping finished. created:', created, 'errors:', errors[:10])
