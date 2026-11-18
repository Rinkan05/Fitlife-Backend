from django.db import models
from django.contrib.auth.models import User
import uuid

class Plan(models.Model):
    nombre = models.CharField(max_length=100) # Ej: Plan Mensual, Plan Anual
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_dias = models.IntegerField(default=30)

    def __str__(self):
        return self.nombre

class Membresia(models.Model):
    ESTADOS_MEMBRESIA = [
        ('Activa', 'Activa'),
        ('Vencida', 'Vencida'),
        ('Congelada', 'Congelada'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS_MEMBRESIA, default='Activa')
    codigo_qr = models.UUIDField(default=uuid.uuid4, editable=False, unique=True) # Para simular el QR

    def __str__(self):
        return f"{self.usuario.username} - {self.plan.nombre} ({self.estado})"

class ClaseGrupal(models.Model):
    nombre = models.CharField(max_length=100) # Ej: Spinning, Yoga
    fecha_hora = models.DateTimeField()
    cupo_maximo = models.IntegerField()
    instructor = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"

class Reserva(models.Model):
    ESTADOS_RESERVA = [
        ('Confirmada', 'Confirmada'),
        ('Espera', 'En Lista de Espera'),
        ('Cancelada', 'Cancelada'),
    ]
    clase = models.ForeignKey(ClaseGrupal, on_delete=models.CASCADE, related_name='reservas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADOS_RESERVA, default='Confirmada')
    fecha_reserva = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.clase.nombre} ({self.estado})"

class RegistroAcceso(models.Model):
    membresia = models.ForeignKey(Membresia, on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    acceso_concedido = models.BooleanField(default=False)
    motivo = models.CharField(max_length=100, blank=True, null=True) # Ej: "Membresía Vencida"

    def __str__(self):
        return f"Acceso {'OK' if self.acceso_concedido else 'DENEGADO'} - {self.membresia.usuario.username} a las {self.fecha_hora.strftime('%H:%M')}"


class Pago(models.Model):
    ESTADOS_PAGO = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('ANULADO', 'Anulado por Usuario'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pagos')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    orden_compra = models.CharField(max_length=50, unique=True)
    token_ws = models.CharField(max_length=100, blank=True, null=True)
    codigo_autorizacion = models.CharField(max_length=20, blank=True, null=True)
    ultimos_cuatro_digitos = models.CharField(max_length=4, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='PENDIENTE')
    fecha_pago = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago #{self.orden_compra} - {self.usuario.username} - ${self.monto} ({self.estado})"
