from django.db import models
from datetime import datetime
from decimal import Decimal

class OrdenTrabajo(models.Model):
    # Definimos los 3 estados posibles
    ESTADOS_CHOICES = [
        ('PENDIENTE', 'En Espera'),
        ('EN_PROCESO', 'En Ejecución'),
        ('FINALIZADA', 'Finalizada'),
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
    fecha_inicio = models.DateTimeField(null=True, blank=True, default=datetime.now) 
    fecha_termino = models.DateTimeField(null=True, blank=True)
    dias = models.IntegerField(default=0)
    personas = models.IntegerField(default=1)
    hh = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacion = models.TextField(blank=True)
    
    # CAMBIO PRINCIPAL: Nuevo campo 'estado' con valor por defecto PENDIENTE
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='PENDIENTE')
    
    revisado_por = models.CharField(max_length=100, blank=True)
    fecha_revision = models.DateField(null=True, blank=True)
    recibido_por = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    incompleta = models.BooleanField(default=False)

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

class Repuesto(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, related_name='repuestos', on_delete=models.CASCADE)
    numero_item = models.PositiveIntegerField()
    codigo = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    cantidad = models.IntegerField(default=1)

    class Meta:
        ordering = ['numero_item']

class Insumo(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, related_name='insumos', on_delete=models.CASCADE)
    numero_item = models.PositiveIntegerField()
    codigo = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    cantidad = models.IntegerField(default=1)

    class Meta:
        ordering = ['numero_item']