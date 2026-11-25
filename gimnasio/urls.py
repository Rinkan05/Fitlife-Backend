from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    # Vistas de autenticación y templates
    login_view,
    logout_view,
    dashboard_view,
    mi_membresia_view,
    clases_view,
    reservar_clase_view,
    cancelar_reserva_view,
    simulador_acceso_view,
    planes_catalogo_view,
    iniciar_pago_membresia_view,
    retorno_pago_webpay_view,
    api_cliente_view,
    pagina_no_encontrada_view,
    # Endpoints API de baja latencia y dashboard
    ValidarAccesoQRApiView,
    DashboardAforoApiView,
    # ViewSets REST
    PlanViewSet,
    MembresiaViewSet,
    ClaseGrupalViewSet,
    ReservaViewSet,
    RegistroAccesoViewSet,
)

# Router para la API REST de DRF
router = DefaultRouter()
router.register(r'planes', PlanViewSet, basename='api-plan')
router.register(r'membresias', MembresiaViewSet, basename='api-membresia')
router.register(r'clases', ClaseGrupalViewSet, basename='api-clase')
router.register(r'reservas', ReservaViewSet, basename='api-reserva')
router.register(r'registros-acceso', RegistroAccesoViewSet, basename='api-registro-acceso')

urlpatterns = [
    # -------------------------------------------------------------------------
    # 1. VISTAS WEB BASADAS EN TEMPLATES (INTERFAZ FITLIFE)
    # -------------------------------------------------------------------------
    path('', dashboard_view, name='dashboard'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('mi-membresia/', mi_membresia_view, name='mi_membresia'),
    path('clases/', clases_view, name='clases'),
    path('clases/<int:clase_id>/reservar/', reservar_clase_view, name='reservar_clase'),
    path('reservas/<int:reserva_id>/cancelar/', cancelar_reserva_view, name='cancelar_reserva'),
    path('simulador-acceso/', simulador_acceso_view, name='simulador_acceso'),
    path('planes/', planes_catalogo_view, name='planes'),
    # Pasarela de pagos con Transbank Webpay Plus
    path('pago/iniciar/<int:plan_id>/', iniciar_pago_membresia_view, name='iniciar_pago_membresia'),
    path('pago/retorno/', retorno_pago_webpay_view, name='retorno_pago_webpay'),
    # Consola cliente REST API & JWT (Evaluación 4)
    path('api-cliente/', api_cliente_view, name='api_cliente'),

    # -------------------------------------------------------------------------
    # 2. ENDPOINTS ESPECIALIZADOS DE LA API REST Y AUTENTICACIÓN JWT
    # -------------------------------------------------------------------------
    # Autenticación JWT (SimpleJWT)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Validación y registro de código QR en milisegundos para torniquetes físicos
    path('api/acceso/escanear-qr/', ValidarAccesoQRApiView.as_view(), name='api_escanear_qr'),
    # Datos de aforo en vivo para dashboards y clientes externos
    path('api/dashboard/aforo/', DashboardAforoApiView.as_view(), name='api_dashboard_aforo'),

    # -------------------------------------------------------------------------
    # 3. CRUD REST COMPLETO (DRF ROUTER)
    # -------------------------------------------------------------------------
    path('api/', include(router.urls)),

    # -------------------------------------------------------------------------
    # 4. MITIGACIÓN DE ERROR 404 CON RE_PATH (CATCH-ALL)
    # -------------------------------------------------------------------------
    # Captura cualquier ruta que no coincida con los patrones anteriores
    re_path(r'^(?P<ruta_inexistente>.*)$', pagina_no_encontrada_view, name='pagina_no_encontrada'),
]
