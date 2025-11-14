from django.core.management.base import BaseCommand
from ot_management.models import OrdenTrabajo, Tarea, Repuesto, Insumo, OT2025MecanicasRaw


class Command(BaseCommand):
    help = 'Eliminar todas las filas de OrdenTrabajo, Tarea, Repuesto, Insumo y OT2025MecanicasRaw (reset de datos).'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='Confirmar ejecución. Si no se pasa, solo muestra el conteo.')

    def handle(self, *args, **options):
        confirm = options.get('confirm', False)

        counts = {
            'ordenes': OrdenTrabajo.objects.count(),
            'tareas': Tarea.objects.count(),
            'repuestos': Repuesto.objects.count(),
            'insumos': Insumo.objects.count(),
            'raw': OT2025MecanicasRaw.objects.count()
        }

        self.stdout.write('Conteo actual de filas:')
        for k, v in counts.items():
            self.stdout.write(f'  {k}: {v}')

        if not confirm:
            self.stdout.write('\nEjecución en modo seguro: para borrar los datos vuelva a llamar este comando con --confirm')
            return

        # Borrar en orden correcto para mantener integridad referencial
        self.stdout.write('\nBorrando datos...')
        Tarea.objects.all().delete()
        Repuesto.objects.all().delete()
        Insumo.objects.all().delete()
        OrdenTrabajo.objects.all().delete()
        OT2025MecanicasRaw.objects.all().delete()

        self.stdout.write('Borrado completado. Nuevos conteos:')
        self.stdout.write(f"  ordenes: {OrdenTrabajo.objects.count()}")
        self.stdout.write(f"  tareas: {Tarea.objects.count()}")
        self.stdout.write(f"  repuestos: {Repuesto.objects.count()}")
        self.stdout.write(f"  insumos: {Insumo.objects.count()}")
        self.stdout.write(f"  raw: {OT2025MecanicasRaw.objects.count()}")
