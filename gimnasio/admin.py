from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Plan, Membresia, ClaseGrupal, Reserva, RegistroAcceso, Pago

# ==============================================================================
# CONFIGURACIÓN DEL PANEL DE ADMINISTRACIÓN - FITLIFE
# ==============================================================================

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """
    Administración de Planes de entrenamiento:
    Permite visualizar precios, duración en días y buscar planes por nombre.
    """
    list_display = ('nombre', 'precio', 'duracion_dias')
    search_fields = ('nombre',)
    list_filter = ('duracion_dias',)
    ordering = ('precio',)


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    """
    Administración de Membresías de Socios:
    - Badges de color según estado (Activa, Vencida, Congelada).
    - Código QR UUID protegido de edición.
    - Acciones masivas para actualizar estados de clientes rápidamente.
    """
    list_display = (
        'usuario',
        'plan',
        'fecha_inicio',
        'fecha_fin',
        'estado_badge',
        'codigo_qr_resumen',
    )
    list_filter = ('estado', 'plan', 'fecha_fin')
    search_fields = ('usuario__username', 'usuario__email', 'codigo_qr')
    readonly_fields = ('codigo_qr',)
    actions = ['marcar_como_activa', 'marcar_como_congelada', 'marcar_como_vencida']

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        """Etiqueta visual estilizada para el estado de la membresía."""
        colores = {
            'Activa': '#28a745',    # Verde
            'Vencida': '#dc3545',   # Rojo
            'Congelada': '#ffc107', # Amarillo/Ámbar
        }
        color = colores.get(obj.estado, '#6c757d')
        texto_color = '#000' if obj.estado == 'Congelada' else '#fff'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            texto_color,
            obj.estado,
        )

    @admin.display(description='Código QR (UUID)')
    def codigo_qr_resumen(self, obj):
        """Muestra solo el prefijo del UUID para mantener la tabla limpia y legible."""
        return f"{str(obj.codigo_qr)[:8]}..."

    # Acciones masivas desde el panel administrativo
    @admin.action(description='Marcar seleccionadas como Activa')
    def marcar_como_activa(self, request, queryset):
        filas_actualizadas = queryset.update(estado='Activa')
        self.message_user(request, f"{filas_actualizadas} membresía(s) marcada(s) como Activa.")

    @admin.action(description='Marcar seleccionadas como Congelada')
    def marcar_como_congelada(self, request, queryset):
        filas_actualizadas = queryset.update(estado='Congelada')
        self.message_user(request, f"{filas_actualizadas} membresía(s) marcada(s) como Congelada.")

    @admin.action(description='Marcar seleccionadas como Vencida')
    def marcar_como_vencida(self, request, queryset):
        filas_actualizadas = queryset.update(estado='Vencida')
        self.message_user(request, f"{filas_actualizadas} membresía(s) marcada(s) como Vencida.")


class ReservaInline(admin.TabularInline):
    """
    Vista embebida para visualizar y gestionar reservas directamente dentro de cada clase.
    """
    model = Reserva
    extra = 0
    readonly_fields = ('fecha_reserva',)
    can_delete = True


@admin.register(ClaseGrupal)
class ClaseGrupalAdmin(admin.ModelAdmin):
    """
    Administración de Clases Grupales:
    - Control visual inmediato de cupos disponibles y ocupados.
    - Contador de personas en Lista de Espera.
    - Reservas integradas como Inline para gestión centralizada.
    """
    list_display = ('nombre', 'instructor', 'fecha_hora', 'cupo_maximo', 'cupos_ocupados', 'en_lista_espera')
    list_filter = ('fecha_hora', 'instructor')
    search_fields = ('nombre', 'instructor')
    inlines = [ReservaInline]

    @admin.display(description='Cupos Confirmados')
    def cupos_ocupados(self, obj):
        """Muestra el total de reservas confirmadas frente al cupo máximo con alerta de color."""
        total = obj.reservas.filter(estado='Confirmada').count()
        color = '#dc3545' if total >= obj.cupo_maximo else '#28a745'
        return format_html(
            '<strong style="color: {};">{}/{}</strong>',
            color,
            total,
            obj.cupo_maximo,
        )

    @admin.display(description='En Lista de Espera')
    def en_lista_espera(self, obj):
        """Total de socios esperando cupo si la clase está llena."""
        espera = obj.reservas.filter(estado='Espera').count()
        return format_html('<span style="color: #6c757d; font-weight: bold;">{} personas</span>', espera)


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    """
    Administración de Reservas individuales:
    - Búsqueda predictiva con autocompletado para Socios y Clases.
    - Distinción visual de reservas Confirmadas, en Espera o Canceladas.
    """
    list_display = ('usuario', 'clase', 'estado_badge', 'fecha_reserva')
    list_filter = ('estado', 'clase__fecha_hora')
    search_fields = ('usuario__username', 'clase__nombre')
    autocomplete_fields = ('usuario', 'clase')

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        colores = {
            'Confirmada': '#28a745', # Verde
            'Espera': '#17a2b8',     # Cian / Info
            'Cancelada': '#6c757d',  # Gris neutro
        }
        color = colores.get(obj.estado, '#343a40')
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.estado,
        )


@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(admin.ModelAdmin):
    """
    Auditoría y Log de Accesos Físicos al Gimnasio (Torniquete / Lector QR):
    - Registros de solo lectura para preservar la trazabilidad y la integridad de auditoría.
    - Jerarquía por fechas y visualización clara de accesos Concedidos vs Denegados con su motivo.
    """
    list_display = ('fecha_hora', 'socio', 'resultado_badge', 'motivo')
    list_filter = ('acceso_concedido', 'fecha_hora')
    search_fields = ('membresia__usuario__username', 'motivo')
    date_hierarchy = 'fecha_hora'
    readonly_fields = ('membresia', 'fecha_hora', 'acceso_concedido', 'motivo')

    @admin.display(description='Socio')
    def socio(self, obj):
        return obj.membresia.usuario.get_full_name() or obj.membresia.usuario.username

    @admin.display(description='Resultado')
    def resultado_badge(self, obj):
        if obj.acceso_concedido:
            return format_html('<span style="color: #28a745; font-weight: bold;">✔ CONCEDIDO</span>')
        return format_html('<span style="color: #dc3545; font-weight: bold;">✖ DENEGADO</span>')


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """
    Auditoría y Gestión de Pagos Electrónicos (Transbank Webpay Plus):
    - Trazabilidad de órdenes de compra, códigos de autorización y estado de la transacción.
    - Datos protegidos de solo lectura para preservar la integridad financiera.
    """
    list_display = ('orden_compra', 'usuario', 'plan', 'monto_formateado', 'estado_badge', 'codigo_autorizacion', 'fecha_pago')
    list_filter = ('estado', 'fecha_pago')
    search_fields = ('orden_compra', 'usuario__username', 'codigo_autorizacion')
    readonly_fields = ('orden_compra', 'usuario', 'plan', 'monto', 'token_ws', 'codigo_autorizacion', 'ultimos_cuatro_digitos', 'estado', 'fecha_pago')

    @admin.display(description='Monto')
    def monto_formateado(self, obj):
        return f"${int(obj.monto):,}".replace(',', '.')

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        colores = {
            'APROBADO': '#28a745',
            'RECHAZADO': '#dc3545',
            'PENDIENTE': '#ffc107',
            'ANULADO': '#6c757d',
        }
        color = colores.get(obj.estado, '#6c757d')
        texto_color = '#000' if obj.estado == 'PENDIENTE' else '#fff'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 10px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            texto_color,
            obj.estado,
        )

