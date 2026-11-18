from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid

from gimnasio.models import Plan, Membresia, ClaseGrupal, Reserva, RegistroAcceso


class Command(BaseCommand):
    help = 'Puebla la base de datos con datos de prueba realistas para FitLife'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Iniciando carga de datos de prueba para FitLife...'))

        # 1. Crear Superusuario Administrador si no existe
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@fitlife.cl',
                'first_name': 'Administrador',
                'last_name': 'FitLife',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('✔ Superusuario creado: usuario "admin" / clave "admin123"'))
        else:
            self.stdout.write(self.style.WARNING('ℹ El usuario "admin" ya existía.'))

        # 2. Crear Planes
        plan_mensual, _ = Plan.objects.get_or_create(
            nombre='Plan Mensual Silver',
            defaults={'precio': 29990.00, 'duracion_dias': 30}
        )
        plan_trimestral, _ = Plan.objects.get_or_create(
            nombre='Plan Trimestral Gold',
            defaults={'precio': 79990.00, 'duracion_dias': 90}
        )
        plan_anual, _ = Plan.objects.get_or_create(
            nombre='Plan Anual Black VIP',
            defaults={'precio': 249990.00, 'duracion_dias': 365}
        )
        self.stdout.write(self.style.SUCCESS('✔ 3 Planes creados (Mensual, Trimestral, Anual)'))

        # 3. Crear Socios con diferentes estados de membresía
        hoy = timezone.localdate()

        # Socio 1: Membresía ACTIVA
        user_activo, _ = User.objects.get_or_create(
            username='juan.activo',
            defaults={'first_name': 'Juan', 'last_name': 'Pérez', 'email': 'juan@fitlife.cl'}
        )
        user_activo.set_password('socio123')
        user_activo.save()

        m_activa, _ = Membresia.objects.get_or_create(
            usuario=user_activo,
            defaults={
                'plan': plan_anual,
                'fecha_inicio': hoy - timedelta(days=15),
                'fecha_fin': hoy + timedelta(days=350),
                'estado': 'Activa',
            }
        )

        # Socio 2: Membresía CONGELADA
        user_congelado, _ = User.objects.get_or_create(
            username='maria.congelada',
            defaults={'first_name': 'María', 'last_name': 'González', 'email': 'maria@fitlife.cl'}
        )
        user_congelado.set_password('socio123')
        user_congelado.save()

        m_congelada, _ = Membresia.objects.get_or_create(
            usuario=user_congelado,
            defaults={
                'plan': plan_trimestral,
                'fecha_inicio': hoy - timedelta(days=30),
                'fecha_fin': hoy + timedelta(days=60),
                'estado': 'Congelada',
            }
        )

        # Socio 3: Membresía VENCIDA
        user_vencido, _ = User.objects.get_or_create(
            username='carlos.vencido',
            defaults={'first_name': 'Carlos', 'last_name': 'Rodríguez', 'email': 'carlos@fitlife.cl'}
        )
        user_vencido.set_password('socio123')
        user_vencido.save()

        m_vencida, _ = Membresia.objects.get_or_create(
            usuario=user_vencido,
            defaults={
                'plan': plan_mensual,
                'fecha_inicio': hoy - timedelta(days=60),
                'fecha_fin': hoy - timedelta(days=5),
                'estado': 'Vencida',
            }
        )

        self.stdout.write(self.style.SUCCESS('✔ 3 Socios creados (clave común "socio123"):'))
        self.stdout.write(f'   - [ACTIVA]    {user_activo.username} -> QR UUID: {m_activa.codigo_qr}')
        self.stdout.write(f'   - [CONGELADA] {user_congelado.username} -> QR UUID: {m_congelada.codigo_qr}')
        self.stdout.write(f'   - [VENCIDA]   {user_vencido.username} -> QR UUID: {m_vencida.codigo_qr}')

        # 4. Crear Clases Grupales
        manana = timezone.now() + timedelta(days=1)
        clase_spinning, _ = ClaseGrupal.objects.get_or_create(
            nombre='Spinning Extreme',
            defaults={
                'fecha_hora': manana.replace(hour=18, minute=30, second=0, microsecond=0),
                'cupo_maximo': 2,  # Cupo intencionalmente bajo (2) para probar fácil la lista de espera
                'instructor': 'Franco Valenzuela',
            }
        )

        clase_yoga, _ = ClaseGrupal.objects.get_or_create(
            nombre='Power Yoga & Flex',
            defaults={
                'fecha_hora': manana.replace(hour=20, minute=0, second=0, microsecond=0),
                'cupo_maximo': 12,
                'instructor': 'Camila Silva',
            }
        )
        self.stdout.write(self.style.SUCCESS('✔ 2 Clases Grupales creadas (Spinning con 2 cupos para probar lista de espera)'))

        self.stdout.write(self.style.SUCCESS('\n🎉 ¡Poblado exitoso! Todos los datos de prueba están listos para la evaluación.'))

