from django.db import models

class OrdenTrabajo(models.Model):
    MANTENCION_CHOICES = [
        ('SÍ', 'Sí'),
        ('NO', 'No'),
    ]
    
    ot = models.CharField(max_length=20, unique=True)
    encargado = models.CharField(max_length=100)
    maquina = models.CharField(max_length=255)
    tipo_falla = models.CharField(max_length=50)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_termino = models.DateTimeField(null=True, blank=True)
    dias = models.IntegerField(default=0)
    personas = models.IntegerField(default=1)
    hh = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacion = models.TextField(blank=True)
    mantencion_lograda = models.CharField(max_length=2, choices=MANTENCION_CHOICES, default='NO')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Orden de trabajo"
        verbose_name_plural = "Órdenes de trabajo"