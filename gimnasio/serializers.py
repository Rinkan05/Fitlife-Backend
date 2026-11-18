from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Plan, Membresia, ClaseGrupal, Reserva, RegistroAcceso

# ==============================================================================
# SERIALIZERS - FITLIFE BACKEND (DRF)
# ==============================================================================

class UsuarioSimpleSerializer(serializers.ModelSerializer):
    """Información simplificada del socio o usuario del sistema."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class PlanSerializer(serializers.ModelSerializer):
    """Serializer para el CRUD de Planes de suscripción."""
    class Meta:
        model = Plan
        fields = ['id', 'nombre', 'precio', 'duracion_dias']


class MembresiaSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Membresías:
    Incluye datos del socio, el plan suscrito y el token UUID para el código QR.
    """
    usuario = UsuarioSimpleSerializer(read_only=True)
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(), source='plan', write_only=True
    )
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='usuario', write_only=True
    )
    dias_restantes = serializers.SerializerMethodField()

    class Meta:
        model = Membresia
        fields = [
            'id',
            'usuario',
            'usuario_id',
            'plan',
            'plan_id',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'codigo_qr',
            'dias_restantes',
        ]
        read_only_fields = ['codigo_qr']

    def get_dias_restantes(self, obj):
        """Calcula cuántos días le quedan a la membresía respecto a la fecha actual."""
        hoy = timezone.localdate()
        if obj.fecha_fin >= hoy:
            return (obj.fecha_fin - hoy).days
        return 0


class ClaseGrupalSerializer(serializers.ModelSerializer):
    """
    Serializer para Clases Grupales:
    Expone los cupos ocupados, disponibles y la cantidad de socios en lista de espera.
    """
    cupos_ocupados = serializers.SerializerMethodField()
    cupos_disponibles = serializers.SerializerMethodField()
    en_lista_espera = serializers.SerializerMethodField()

    class Meta:
        model = ClaseGrupal
        fields = [
            'id',
            'nombre',
            'instructor',
            'fecha_hora',
            'cupo_maximo',
            'cupos_ocupados',
            'cupos_disponibles',
            'en_lista_espera',
        ]

    def get_cupos_ocupados(self, obj):
        return obj.reservas.filter(estado='Confirmada').count()

    def get_cupos_disponibles(self, obj):
        ocupados = self.get_cupos_ocupados(obj)
        disponibles = obj.cupo_maximo - ocupados
        return max(0, disponibles)

    def get_en_lista_espera(self, obj):
        return obj.reservas.filter(estado='Espera').count()


class ReservaSerializer(serializers.ModelSerializer):
    """
    Serializer para la consulta de Reservas.
    """
    usuario = UsuarioSimpleSerializer(read_only=True)
    clase_detalle = ClaseGrupalSerializer(source='clase', read_only=True)

    class Meta:
        model = Reserva
        fields = [
            'id',
            'usuario',
            'clase',
            'clase_detalle',
            'estado',
            'fecha_reserva',
        ]
        read_only_fields = ['estado', 'fecha_reserva']


class CrearReservaSerializer(serializers.Serializer):
    """
    Serializer para la acción de reservar una clase:
    Recibe la clase_id a reservar. El usuario se obtiene del request autenticado
    (o parámetro opcional si es gestionado por un administrador).
    """
    clase_id = serializers.IntegerField(required=True)
    usuario_id = serializers.IntegerField(required=False, help_text="Opcional: solo para administradores")


class EscanearQRSerializer(serializers.Serializer):
    """
    Serializer de alta velocidad y baja latencia para el lector/torniquete de acceso QR.
    Valida únicamente el formato UUID antes de consultar la base de datos.
    """
    codigo_qr = serializers.UUIDField(required=True, help_text="UUID del código QR del socio")


class RegistroAccesoSerializer(serializers.ModelSerializer):
    """
    Serializer para auditoría de accesos registrados en torniquetes.
    """
    socio_nombre = serializers.SerializerMethodField()
    socio_username = serializers.CharField(source='membresia.usuario.username', read_only=True)
    plan_nombre = serializers.CharField(source='membresia.plan.nombre', read_only=True)

    class Meta:
        model = RegistroAcceso
        fields = [
            'id',
            'membresia',
            'socio_username',
            'socio_nombre',
            'plan_nombre',
            'fecha_hora',
            'acceso_concedido',
            'motivo',
        ]
        read_only_fields = '__all__'

    def get_socio_nombre(self, obj):
        user = obj.membresia.usuario
        return user.get_full_name() or user.username


class DashboardAforoSerializer(serializers.Serializer):
    """
    Serializer para el payload del dashboard en tiempo real de control de aforo.
    """
    aforo_actual = serializers.IntegerField()
    capacidad_maxima = serializers.IntegerField()
    porcentaje_ocupacion = serializers.FloatField()
    accesos_hoy = serializers.IntegerField()
    accesos_denegados_hoy = serializers.IntegerField()
    ultima_actualizacion = serializers.DateTimeField()

