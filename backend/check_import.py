import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comnetal_backend.settings')
django.setup()

from ot_management.models import OT2025MecanicasRaw

count = OT2025MecanicasRaw.objects.count()
print(f"OT2025MecanicasRaw rows: {count}")

# show 5 sample rows
for obj in OT2025MecanicasRaw.objects.all()[:5]:
    print('---')
    print(f'fila: {obj.fila} fuente: {obj.fuente_archivo} created: {obj.created_at}')
    print(obj.data[:1000])
