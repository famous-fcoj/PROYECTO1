from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OrdenTrabajo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ot', models.CharField(max_length=20, unique=True)),
                ('encargado', models.CharField(max_length=100)),
                ('maquina', models.CharField(max_length=255)),
                ('tipo_falla', models.CharField(max_length=50)),
                ('fecha_inicio', models.DateTimeField(blank=True, null=True)),
                ('fecha_termino', models.DateTimeField(blank=True, null=True)),
                ('dias', models.IntegerField(default=0, help_text='Resultado de NETWORKDAYS')),
                ('personas', models.IntegerField(default=1)),
                ('hh', models.DecimalField(decimal_places=2, default=0, help_text='Horas hombre', max_digits=10)),
                ('observacion', models.TextField(blank=True)),
                ('mantencion_lograda', models.CharField(choices=[('SÍ', 'Sí'), ('NO', 'No')], default='NO', max_length=2)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Orden de trabajo',
                'verbose_name_plural': 'Órdenes de trabajo',
            },
        ),
    ]