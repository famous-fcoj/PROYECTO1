from django.db import models

class OrdenTrabajo(models.Model):
    MANTENCION_CHOICES = [
        ('SÍ', 'Sí'),
        ('NO', 'No'),
    ]
    
    ot = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(blank=True)
    marca = models.CharField(max_length=100, blank=True)
    encargado = models.CharField(max_length=100)
    maquina = models.CharField(max_length=255)
    tipo_accion = models.CharField(max_length=100, blank=True)
    odometro = models.IntegerField(default=0)
    ubicacion = models.CharField(max_length=255, blank=True)
    modelo = models.CharField(max_length=255, blank=True)
    supervisor = models.CharField(max_length=100, blank=True)
    fecha_planificada = models.DateField(null=True, blank=True)
    tipo_falla = models.CharField(max_length=50)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_termino = models.DateTimeField(null=True, blank=True)
    dias = models.IntegerField(default=0)
    personas = models.IntegerField(default=1)
    hh = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacion = models.TextField(blank=True)
    mantencion_lograda = models.CharField(max_length=2, choices=MANTENCION_CHOICES, default='NO')
    revisado_por = models.CharField(max_length=100, blank=True)
    fecha_revision = models.DateField(null=True, blank=True)
    recibido_por = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Flag para indicar que la OT proviene de una importación incompleta
    incompleta = models.BooleanField(default=False)
    # Para trazabilidad: nombre del archivo fuente y número de fila en el archivo
    fuente_archivo = models.CharField(max_length=255, blank=True)
    fila_origen = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Orden de trabajo"
        verbose_name_plural = "Órdenes de trabajo"

    def __str__(self):
        return f"OT {self.ot} - {self.maquina}"


class Tarea(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, related_name='tareas', on_delete=models.CASCADE)
    numero_item = models.PositiveIntegerField()
    detalle = models.TextField()
    tiempo_estimado = models.IntegerField(default=0)
    tiempo_real = models.IntegerField(default=0)

    class Meta:
        ordering = ['numero_item']

    def __str__(self):
        return f"Tarea {self.numero_item} - OT {self.orden.ot}"


class Repuesto(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, related_name='repuestos', on_delete=models.CASCADE)
    numero_item = models.PositiveIntegerField()
    codigo = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    cantidad = models.IntegerField(default=1)

    class Meta:
        ordering = ['numero_item']

    def __str__(self):
        return f"Repuesto {self.codigo} (OT {self.orden.ot})"


class Insumo(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, related_name='insumos', on_delete=models.CASCADE)
    numero_item = models.PositiveIntegerField()
    codigo = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    cantidad = models.IntegerField(default=1)

    class Meta:
        ordering = ['numero_item']

    def __str__(self):
        return f"Insumo {self.codigo} (OT {self.orden.ot})"


class OT2025MecanicasRaw(models.Model):
    """Raw storage table for the file 'OT 2025 MECANICAS.xlsx'.
    Each row of the spreadsheet is stored as a JSON string in `data`.
    The DB table name is explicitly set to 'ot_2025_mecanicas' as requested.
    """
    fila = models.IntegerField(null=True, blank=True)
    data = models.TextField(help_text='JSON dump of the row values')
    fuente_archivo = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ot_2025_mecanicas'
        verbose_name = 'OT 2025 Mecanicas - Raw row'
        verbose_name_plural = 'OT 2025 Mecanicas - Raw rows'

    def __str__(self):
        return f"Fila {self.fila} - {self.fuente_archivo}"