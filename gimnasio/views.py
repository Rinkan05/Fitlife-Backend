import time
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Plan, Membresia, ClaseGrupal, Reserva, RegistroAcceso, Pago
from .webpay_service import WebpayService
from .serializers import (
    PlanSerializer,
    MembresiaSerializer,
    ClaseGrupalSerializer,
    ReservaSerializer,
    RegistroAccesoSerializer,
    EscanearQRSerializer,
    DashboardAforoSerializer,
)

# Constante de capacidad máxima del gimnasio para control de aforo
CAPACIDAD_MAXIMA_GIMNASIO = 80


# ==============================================================================
# 1. VISTAS DE AUTENTICACIÓN Y SESIONES (TEMPLATES)
# ==============================================================================

def login_view(request):
    """Manejo de inicio de sesión con sesiones seguras de Django."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'¡Bienvenido a FitLife, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Credenciales incorrectas. Verifique su usuario y contraseña.')

    return render(request, 'login.html')


def logout_view(request):
    """Cierre de sesión y destrucción de sesión activa."""
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')


# ==============================================================================
# 2. VISTAS BASADAS EN TEMPLATES (INTERFAZ DE USUARIO)
# ==============================================================================

@login_required(login_url='login')
def dashboard_view(request):
    """
    Dashboard en tiempo real para el control de aforo y métricas de acceso.
    Calcula la estimación de personas en sala durante las últimas 2 horas.
    """
    hoy = timezone.localdate()
    ahora = timezone.now()
    hace_dos_horas = ahora - timedelta(hours=2)

    # Accesos concedidos en la ventana reciente (estimación de permanencia en sala)
    aforo_actual = RegistroAcceso.objects.filter(
        fecha_hora__gte=hace_dos_horas,
        acceso_concedido=True
    ).count()

    # Métricas del día actual
    accesos_hoy = RegistroAcceso.objects.filter(
        fecha_hora__date=hoy,
        acceso_concedido=True
    ).count()

    denegados_hoy = RegistroAcceso.objects.filter(
        fecha_hora__date=hoy,
        acceso_concedido=False
    ).count()

    porcentaje_ocupacion = round((aforo_actual / CAPACIDAD_MAXIMA_GIMNASIO) * 100, 1)

    ultimos_accesos = RegistroAcceso.objects.select_related('membresia__usuario', 'membresia__plan').order_by('-fecha_hora')[:10]

    contexto = {
        'aforo_actual': aforo_actual,
        'capacidad_maxima': CAPACIDAD_MAXIMA_GIMNASIO,
        'porcentaje_ocupacion': min(porcentaje_ocupacion, 100.0),
        'accesos_hoy': accesos_hoy,
        'denegados_hoy': denegados_hoy,
        'ultimos_accesos': ultimos_accesos,
    }
    return render(request, 'dashboard_aforo.html', contexto)


@login_required(login_url='login')
def mi_membresia_view(request):
    """Visualización del carnet virtual, estado de membresía y código QR del socio."""
    membresia = Membresia.objects.select_related('plan').filter(usuario=request.user).first()
    
    dias_restantes = 0
    if membresia:
        hoy = timezone.localdate()
        if membresia.fecha_fin >= hoy:
            dias_restantes = (membresia.fecha_fin - hoy).days

    contexto = {
        'membresia': membresia,
        'dias_restantes': dias_restantes,
    }
    return render(request, 'mi_membresia.html', contexto)


@login_required(login_url='login')
def clases_view(request):
    """
    Listado de clases grupales disponibles con indicación de cupos y estado
    de reserva del usuario actual.
    """
    ahora = timezone.now()
    clases = ClaseGrupal.objects.filter(fecha_hora__gte=ahora).order_by('fecha_hora')

    # Identificar las reservas del usuario actual para resaltar su estado en la UI
    reservas_usuario = {
        r.clase_id: r for r in Reserva.objects.filter(usuario=request.user, clase__in=clases)
    }

    clases_data = []
    for c in clases:
        confirmadas = c.reservas.filter(estado='Confirmada').count()
        en_espera = c.reservas.filter(estado='Espera').count()
        reserva_propia = reservas_usuario.get(c.id)

        clases_data.append({
            'clase': c,
            'confirmadas': confirmadas,
            'cupo_maximo': c.cupo_maximo,
            'disponibles': max(0, c.cupo_maximo - confirmadas),
            'en_espera': en_espera,
            'reserva_propia': reserva_propia,
        })

    return render(request, 'clases.html', {'clases_data': clases_data})


@login_required(login_url='login')
def reservar_clase_view(request, clase_id):
    """
    Lógica de negocio para reserva de clase:
    - Uso de transacción atómica y select_for_update para control de concurrencia.
    - Si el cupo está disponible -> Confirmada.
    - Si el cupo está agotado -> Pasa automáticamente a Lista de Espera.
    """
    if request.method != 'POST':
        return redirect('clases')

    with transaction.atomic():
        clase = get_object_or_404(ClaseGrupal.objects.select_for_update(), id=clase_id)

        # Validar si ya posee una reserva activa
        reserva_existente = Reserva.objects.filter(
            clase=clase,
            usuario=request.user
        ).exclude(estado='Cancelada').first()

        if reserva_existente:
            messages.warning(
                request,
                f'Ya posees una reserva en estado "{reserva_existente.get_estado_display()}" para esta clase.'
            )
            return redirect('clases')

        # Contar cupos confirmados actuales
        cupos_confirmados = clase.reservas.filter(estado='Confirmada').count()

        if cupos_confirmados < clase.cupo_maximo:
            # Hay cupo -> Confirmada
            Reserva.objects.create(
                clase=clase,
                usuario=request.user,
                estado='Confirmada'
            )
            messages.success(request, f'¡Reserva confirmada exitosamente para {clase.nombre}!')
        else:
            # No hay cupo -> Lista de Espera automática
            Reserva.objects.create(
                clase=clase,
                usuario=request.user,
                estado='Espera'
            )
            messages.info(
                request,
                f'La clase {clase.nombre} está llena. Has quedado registrado en la LISTA DE ESPERA. Si alguien cancela, tu cupo ascenderá automáticamente.'
            )

    return redirect('clases')


@login_required(login_url='login')
def cancelar_reserva_view(request, reserva_id):
    """
    Cancelación de reserva y promoción automática de lista de espera:
    Si un usuario con reserva Confirmada cancela, el primer socio en Espera
    es promovido automáticamente a Confirmada.
    """
    if request.method != 'POST':
        return redirect('clases')

    with transaction.atomic():
        reserva = get_object_or_404(
            Reserva.objects.select_for_update(),
            id=reserva_id,
            usuario=request.user
        )

        estaba_confirmada = (reserva.estado == 'Confirmada')
        clase = reserva.clase
        reserva.estado = 'Cancelada'
        reserva.save()

        # Si liberó un cupo confirmado, buscar a la primera persona en lista de espera
        if estaba_confirmada:
            siguiente_en_espera = Reserva.objects.select_for_update().filter(
                clase=clase,
                estado='Espera'
            ).order_by('fecha_reserva').first()

            if siguiente_en_espera:
                siguiente_en_espera.estado = 'Confirmada'
                siguiente_en_espera.save()
                messages.info(
                    request,
                    f'Se liberó un cupo y se promovió automáticamente a {siguiente_en_espera.usuario.username} desde la lista de espera.'
                )

        messages.success(request, 'Tu reserva ha sido cancelada.')

    return redirect('clases')


def simulador_acceso_view(request):
    """
    Página web interactiva que simula el lector físico / torniquete del gimnasio.
    Permite validar códigos QR con respuesta inmediata visual.
    """
    membresias_ejemplo = Membresia.objects.select_related('usuario', 'plan').all()[:6]
    return render(request, 'simulador_acceso.html', {'membresias_ejemplo': membresias_ejemplo})


def planes_catalogo_view(request):
    """Catálogo público de planes ofrecidos por FitLife."""
    planes = Plan.objects.all().order_by('precio')
    return render(request, 'planes.html', {'planes': planes})


# ==============================================================================
# 2.1 PAGOS ELECTRÓNICOS CON TRANSBANK WEBPAY PLUS
# ==============================================================================

@login_required(login_url='login')
def iniciar_pago_membresia_view(request, plan_id):
    """
    Inicia el flujo de pago con Transbank Webpay Plus para contratar o renovar un plan.
    Crea el registro de Pago (PENDIENTE) y redirige a la pasarela bancaria oficial.
    """
    plan = get_object_or_404(Plan, id=plan_id)
    hoy = timezone.now()
    orden_compra = f"FL-{request.user.id}-{int(hoy.timestamp())}"
    monto = int(plan.precio)
    session_id = request.session.session_key or f"SES-{request.user.id}"
    return_url = request.build_absolute_uri('/pago/retorno/')

    try:
        resultado = WebpayService.iniciar_transaccion(
            buy_order=orden_compra,
            session_id=session_id,
            amount=monto,
            return_url=return_url
        )

        token_ws = resultado.get('token')
        url_webpay = resultado.get('url')

        # Guardar registro de auditoría del pago
        Pago.objects.create(
            usuario=request.user,
            plan=plan,
            monto=plan.precio,
            orden_compra=orden_compra,
            token_ws=token_ws,
            estado='PENDIENTE'
        )

        return render(request, 'pago_redireccion.html', {
            'url_webpay': url_webpay,
            'token_ws': token_ws,
            'plan': plan,
            'monto': monto,
        })
    except Exception as e:
        messages.error(request, f'No fue posible conectar con Transbank Webpay: {str(e)}')
        return redirect('planes')


@csrf_exempt
def retorno_pago_webpay_view(request):
    """
    Endpoint de retorno de Transbank Webpay Plus:
    Recibe la respuesta de la pasarela bancaria, confirma la transacción (Commit),
    actualiza el pago y activa/renueva la membresía del socio automáticamente.
    """
    # Transbank puede enviar datos por POST o GET
    token_ws = request.POST.get('token_ws') or request.GET.get('token_ws')
    tbk_token = request.POST.get('TBK_TOKEN') or request.GET.get('TBK_TOKEN')

    # Caso 1: El usuario anuló la compra en el formulario de Transbank
    if tbk_token and not token_ws:
        pago = Pago.objects.filter(token_ws=tbk_token).first()
        if pago:
            pago.estado = 'ANULADO'
            pago.save(update_fields=['estado'])
        return render(request, 'pago_fallido.html', {
            'motivo': 'El pago fue cancelado por el usuario en la pasarela de Webpay.',
            'pago': pago,
        })

    if not token_ws:
        return render(request, 'pago_fallido.html', {
            'motivo': 'No se recibió el token de confirmación de Transbank.',
        })

    pago = Pago.objects.select_related('usuario', 'plan').filter(token_ws=token_ws).first()

    try:
        resultado = WebpayService.confirmar_transaccion(token_ws)
        status_webpay = resultado.get('status')

        if status_webpay == 'AUTHORIZED' and resultado.get('response_code') == 0:
            # Pago APROBADO por el banco
            card_detail = resultado.get('card_detail', {})
            ultimos_cuatro = card_detail.get('card_number', '****')
            cod_autorizacion = resultado.get('authorization_code', 'N/A')

            if pago:
                pago.estado = 'APROBADO'
                pago.codigo_autorizacion = cod_autorizacion
                pago.ultimos_cuatro_digitos = ultimos_cuatro
                pago.save()

                usuario = pago.usuario
                plan = pago.plan
            else:
                usuario = request.user
                plan = Plan.objects.first()

            # Activar o renovar membresía automáticamente
            hoy = timezone.localdate()
            nueva_fecha_fin = hoy + timedelta(days=plan.duracion_dias)

            membresia, creada = Membresia.objects.get_or_create(
                usuario=usuario,
                defaults={
                    'plan': plan,
                    'fecha_inicio': hoy,
                    'fecha_fin': nueva_fecha_fin,
                    'estado': 'Activa',
                }
            )

            if not creada:
                membresia.plan = plan
                membresia.fecha_inicio = hoy
                membresia.fecha_fin = nueva_fecha_fin
                membresia.estado = 'Activa'
                membresia.save()

            contexto = {
                'pago': pago,
                'resultado': resultado,
                'plan': plan,
                'membresia': membresia,
                'ultimos_cuatro': ultimos_cuatro,
                'cod_autorizacion': cod_autorizacion,
            }
            return render(request, 'pago_exitoso.html', contexto)

        else:
            # Pago RECHAZADO por el banco
            if pago:
                pago.estado = 'RECHAZADO'
                pago.save(update_fields=['estado'])

            return render(request, 'pago_fallido.html', {
                'motivo': f'La transacción fue rechazada por el emisor bancario (Estado: {status_webpay}).',
                'pago': pago,
                'resultado': resultado,
            })

    except Exception as e:
        if pago:
            pago.estado = 'RECHAZADO'
            pago.save(update_fields=['estado'])
        return render(request, 'pago_fallido.html', {
            'motivo': f'Ocurrió un error al procesar el pago con Webpay: {str(e)}',
            'pago': pago,
        })



# ==============================================================================
# 3. ENDPOINTS API REST (DRF) - BAJA LATENCIA Y SERVICIOS
# ==============================================================================

class ValidarAccesoQRApiView(APIView):
    """
    Endpoint de alta velocidad y baja latencia para el lector QR / torniquete físico:
    POST /api/acceso/escanear-qr/
    Body: {"codigo_qr": "UUID-HEX-FORMAT"}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        inicio_ms = time.time()
        serializer = EscanearQRSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    'acceso_concedido': False,
                    'motivo': 'Formato de código QR inválido',
                    'errores': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        codigo_qr = serializer.validated_data['codigo_qr']
        hoy = timezone.localdate()

        # Consulta indexada directa por UUID con select_related para evitar consultas N+1
        membresia = Membresia.objects.select_related('usuario', 'plan').filter(codigo_qr=codigo_qr).first()

        if not membresia:
            latencia_ms = round((time.time() - inicio_ms) * 1000, 2)
            return Response(
                {
                    'acceso_concedido': False,
                    'motivo': 'Membresía no encontrada / Código QR no registrado',
                    'latencia_ms': latencia_ms,
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Evaluación de reglas de negocio
        acceso_concedido = False
        motivo = ''

        if membresia.estado == 'Congelada':
            acceso_concedido = False
            motivo = 'Membresía Congelada'
        elif membresia.estado == 'Vencida' or membresia.fecha_fin < hoy:
            acceso_concedido = False
            motivo = 'Membresía Vencida'
            if membresia.estado != 'Vencida':
                membresia.estado = 'Vencida'
                membresia.save(update_fields=['estado'])
        elif membresia.estado == 'Activa' and membresia.fecha_fin >= hoy:
            acceso_concedido = True
            motivo = 'Acceso Autorizado'
        else:
            acceso_concedido = False
            motivo = f'Estado de membresía no válido ({membresia.estado})'

        # Auditoría física obligatoria
        registro = RegistroAcceso.objects.create(
            membresia=membresia,
            acceso_concedido=acceso_concedido,
            motivo=motivo
        )

        latencia_ms = round((time.time() - inicio_ms) * 1000, 2)

        return Response(
            {
                'acceso_concedido': acceso_concedido,
                'motivo': motivo,
                'socio': membresia.usuario.get_full_name() or membresia.usuario.username,
                'plan': membresia.plan.nombre,
                'fecha_fin': membresia.fecha_fin,
                'timestamp': registro.fecha_hora.isoformat(),
                'latencia_ms': latencia_ms,
            },
            status=status.HTTP_200_OK if acceso_concedido else status.HTTP_403_FORBIDDEN
        )


class DashboardAforoApiView(APIView):
    """
    Endpoint de sondeo en tiempo real para el control de aforo:
    GET /api/dashboard/aforo/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        hoy = timezone.localdate()
        hace_dos_horas = timezone.now() - timedelta(hours=2)

        aforo_actual = RegistroAcceso.objects.filter(
            fecha_hora__gte=hace_dos_horas,
            acceso_concedido=True
        ).count()

        accesos_hoy = RegistroAcceso.objects.filter(
            fecha_hora__date=hoy,
            acceso_concedido=True
        ).count()

        denegados_hoy = RegistroAcceso.objects.filter(
            fecha_hora__date=hoy,
            acceso_concedido=False
        ).count()

        porcentaje = round((aforo_actual / CAPACIDAD_MAXIMA_GIMNASIO) * 100, 1)

        data = {
            'aforo_actual': aforo_actual,
            'capacidad_maxima': CAPACIDAD_MAXIMA_GIMNASIO,
            'porcentaje_ocupacion': min(porcentaje, 100.0),
            'accesos_hoy': accesos_hoy,
            'accesos_denegados_hoy': denegados_hoy,
            'ultima_actualizacion': timezone.now(),
        }
        serializer = DashboardAforoSerializer(data)
        return Response(serializer.data)


# ==============================================================================
# 4. VIEWSETS REST COMPLETOS PARA PLANES, MEMBRESÍAS Y RESERVAS
# ==============================================================================

class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all().order_by('precio')
    serializer_class = PlanSerializer


class MembresiaViewSet(viewsets.ModelViewSet):
    queryset = Membresia.objects.select_related('usuario', 'plan').all()
    serializer_class = MembresiaSerializer


class ClaseGrupalViewSet(viewsets.ModelViewSet):
    queryset = ClaseGrupal.objects.all().order_by('fecha_hora')
    serializer_class = ClaseGrupalSerializer


class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.select_related('usuario', 'clase').all()
    serializer_class = ReservaSerializer


class RegistroAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegistroAcceso.objects.select_related('membresia__usuario', 'membresia__plan').order_by('-fecha_hora')
    serializer_class = RegistroAccesoSerializer


# ==============================================================================
# 5. MITIGACIÓN DE RUTAS INEXISTENTES (CUSTOM 404 VIEW)
# ==============================================================================

def pagina_no_encontrada_view(request, *args, **kwargs):
    """
    Vista personalizada para mitigar rutas inexistentes o errores 404:
    Muestra la URL solicitada ("La pagina <URL> no ha sido encontrada")
    y un botón de navegación para "Volver al dashboard".
    """
    url_solicitada = request.build_absolute_uri()
    return render(request, '404.html', {'url_solicitada': url_solicitada}, status=404)

