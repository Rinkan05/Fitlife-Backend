## 1. Generación de Modelos ORM (Django)
**Prompt solicitado a la IA:** 
"Empecemos a definir los modelos para FitLife en gimnasio/models.py. Necesito los modelos Plan, Membresía (Activa, Vencida, Congelada), ClaseGrupal, Reserva (Confirmada, Lista de Espera) y RegistroAcceso con validación QR usando UUID."

**Resultado:** 
Se generó el código boilerplate con las relaciones `ForeignKey` y `OneToOneField` hacia el modelo `User` de Django, así como las opciones de estado (Choices) requeridas en el caso de estudio.

---

## 2. Configuración y Personalización Avanzada del Django Admin
**Prompt solicitado a la IA:**
"Genera la configuración del archivo admin.py para los modelos de FitLife, incluyendo filtros, búsquedas y campos visuales optimizados (badges de colores, acciones masivas para membresías y visualización de cupos de clases en tiempo real)."

**Resultado:**
Se configuró `gimnasio/admin.py` implementando:
- `MembresiaAdmin`: badges HTML con colores según estado (`Activa`, `Vencida`, `Congelada`), acciones por lote (`marcar_como_activa`, etc.), y visualización resumida del UUID del código QR.
- `ClaseGrupalAdmin`: indicadores en tiempo real de cupos confirmados versus cupo máximo, contador de personas en lista de espera y `ReservaInline` para administrar asistentes.
- `ReservaAdmin`: autocompletado para usuarios y clases, filtros temporales y badges de estado.
- `RegistroAccesoAdmin`: vista de auditoría de solo lectura con badges de acceso concedido o denegado y motivos de rechazo.

---

## 3. Implementación de Serializadores para DRF (Django REST Framework)
**Prompt solicitado a la IA:**
"Genera los serializadores en gimnasio/serializers.py para manejar las operaciones del sistema FitLife, contemplando el cálculo de días restantes de membresía, cupos de clases grupales, simulación de QR de baja latencia y payload del dashboard de aforo."

**Resultado:**
Se creó `gimnasio/serializers.py` con:
- `PlanSerializer` y `MembresiaSerializer` con métodos calculados (`SerializerMethodField`) para días restantes.
- `ClaseGrupalSerializer` con métricas de cupos ocupados, disponibles y lista de espera.
- `ReservaSerializer` y `CrearReservaSerializer`.
- `EscanearQRSerializer` optimizado con validación UUID para respuestas inmediatas en torniquetes.
- `RegistroAccesoSerializer` y `DashboardAforoSerializer` para auditoría y visualización de aforo.

---

## 4. Lógica de Vistas (Views) e Interfaz con Templates HTML
**Prompt solicitado a la IA:**
"Implementa en gimnasio/views.py la lógica para las vistas web con templates (autenticación, dashboard de aforo en vivo, reservas con control de concurrencia y lista de espera, carnet digital con QR y simulador de torniquete) y los endpoints API de alta velocidad con DRF."

**Resultado:**
Se construyó `gimnasio/views.py` y las plantillas en `Templates/`:
- `ValidarAccesoQRApiView`: endpoint `/api/acceso/escanear-qr/` optimizado con `select_related` y cálculo de latencia en milisegundos.
- `reservar_clase_view` y `cancelar_reserva_view`: transacciones atómicas (`transaction.atomic`) y bloqueo de fila (`select_for_update()`) para evitar condiciones de carrera, asignando lista de espera o promoviendo automáticamente ante cancelaciones.
- `dashboard_view` y `DashboardAforoApiView`: cálculo de aforo en sala (ventana móvil de 2 horas) con actualización periódica vía AJAX.
- `login_view` y `logout_view`: gestión de sesiones de usuario con Django Auth.
- Templates HTML responsivos con Bootstrap 5: `base.html`, `login.html`, `dashboard_aforo.html`, `clases.html`, `mi_membresia.html`, `simulador_acceso.html` y `planes.html`.

---

## 5. Configuración y Enrutamiento de URLs
**Prompt solicitado a la IA:**
"Configura el enrutamiento de URLs tanto para las vistas web de templates como para los endpoints de la API REST (usando DefaultRouter de DRF), integrándolo con el enrutador principal en core/urls.py."

**Resultado:**
Se estructuró `gimnasio/urls.py` conectando:
- Rutas web para templates: `/`, `/login/`, `/logout/`, `/clases/`, `/mi-membresia/`, `/simulador-acceso/`, `/planes/`.
- Endpoints API especializados: `/api/acceso/escanear-qr/` y `/api/dashboard/aforo/`.
- Router automático de DRF: `/api/planes/`, `/api/membresias/`, `/api/clases/`, `/api/reservas/`, `/api/registros-acceso/`.
- Vinculación limpia en `core/urls.py`.

---

## 6. Comando de Poblado y Plan de Pruebas de Funcionamiento
**Prompt solicitado a la IA:**
"Asísteme en generar un comando de datos de prueba automáticos (seed data) para poblar la base de datos con planes, superusuario y socios en estado Activa, Congelada y Vencida, y una guía para validar todos los requerimientos de FitLife antes del despliegue en AWS."

**Resultado:**
Se creó el comando de gestión `python manage.py poblar_datos` en `gimnasio/management/commands/poblar_datos.py` con credenciales de prueba y un checklist paso a paso para validar la simulación de torniquete QR, concurrencia en reservas, lista de espera y control de aforo.

---

## 7. Configuración y Scripts para el Despliegue en AWS EC2
**Prompt solicitado a la IA:**
"Genera los archivos de configuración, scripts de automatización y la documentación paso a paso para desplegar FitLife en una instancia de AWS EC2 (Ubuntu) utilizando Gunicorn como WSGI server, Nginx como proxy inverso, PostgreSQL, gestión de variables de entorno y servicios Systemd."

**Resultado:**
Se crearon en la carpeta `deploy/` y en la raíz del proyecto:
- `requirements.txt` y `.env.example`: gestión limpia de dependencias y variables de producción.
- `deploy/fitlife.service`: unidad de servicio systemd para la ejecución desatendida y monitoreada de Gunicorn a través de sockets Unix.
- `deploy/nginx_fitlife.conf`: bloque de servidor Nginx configurado como reverse proxy y servidor de contenido estático optimizado (`/static/`).
- `deploy/setup_ec2.sh`: script bash de aprovisionamiento automatizado para Ubuntu 22.04 / 24.04 LTS.
- `deploy/README_AWS_EC2.md`: guía paso a paso completa con configuración de Security Groups de AWS, conexión SSH y comandos de operación en producción.

---

## 8. Mitigación de Rutas Inexistentes (Error 404) con re_path
**Prompt solicitado a la IA:**
"Mitiga el error 404 al acceder a URLs no definidas (ej: /clasesasdasd) mediante una regla re_path que capture cualquier ruta inexistente y renderice una pantalla amigable indicando 'La página <URL_COMPLETA> no ha sido encontrada' con un botón que permita 'Volver al dashboard'."

**Resultado:**
- Se implementó la vista `pagina_no_encontrada_view` en `gimnasio/views.py` obteniendo dinámicamente la URL absoluta con `request.build_absolute_uri()`.
- Se configuró la regla comodín al final de `gimnasio/urls.py`: `re_path(r'^(?P<ruta_inexistente>.*)$', pagina_no_encontrada_view)`.
- Se creó el template `Templates/404.html` estilizado con Bootstrap 5 que muestra el mensaje exacto solicitado y el botón `"Volver al dashboard"`.
- Se registró `handler404` en `core/urls.py` para soporte nativo en entornos de producción.

---

## 9. Integración de Pasarela de Pago Transbank Webpay Plus
**Prompt solicitado a la IA:**
"Integra la pasarela oficial de pagos de Transbank Webpay Plus (ambiente de Integración) para pagar y suscribir membresías en FitLife: incluye el modelo Pago con trazabilidad bancaria, vistas para iniciar la transacción y procesar el retorno (commit), activación automática de la membresía con renovación de QR tras el pago exitoso, y plantillas para redirección, voucher de comprobante y rechazo."

**Resultado:**
- Se añadió el modelo `Pago` en `gimnasio/models.py` (orden de compra, token, código de autorización, últimos dígitos y estado) registrado en `gimnasio/admin.py`.
- Se implementó `WebpayService` en `gimnasio/webpay_service.py` con comunicación REST directa con Transbank Integration y las credenciales oficiales de Sandbox (`Tbk-Api-Key-Id: 597055555532` y `Tbk-Api-Key-Secret: 579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C`).
- Se resolvieron errores de autenticación HTTP 401 asegurando el header oficial de 64 caracteres de Transbank Developers.
- Se crearon las vistas `iniciar_pago_membresia_view` y `retorno_pago_webpay_view` (`@csrf_exempt`).
- Se diseñaron los templates `pago_redireccion.html`, `pago_exitoso.html` y `pago_fallido.html`, actualizando el catálogo `planes.html` con botones de pago directo.

---

## 10. Configuración de DNS Dinámico con DuckDNS y Certificados SSL para AWS EC2
**Prompt solicitado a la IA:**
"Configura el uso de DuckDNS como servicio de DNS dinámico para la instancia de AWS EC2 y habilita certificados SSL (HTTPS) con Let's Encrypt / Certbot, actualizando settings.py, nginx y la guía de despliegue."

**Resultado:**
- Se creó el script de actualización periódica `deploy/duckdns_update.sh` para crontab en Ubuntu EC2.
- Se actualizó `deploy/nginx_fitlife.conf` con soporte para el subdominio `.duckdns.org`.
- Se configuró `CSRF_TRUSTED_ORIGINS` y `ALLOWED_HOSTS` en `core/settings.py` para permitir peticiones seguras desde subdominios de DuckDNS y la pasarela de Transbank.
- Se expandió `deploy/README_AWS_EC2.md` con las instrucciones detalladas de vinculación de IP y emisión de certificados SSL con Certbot.


---

## 11. Restricción de Visibilidad del Acceso a Django Admin por Roles
**Prompt solicitado a la IA:**
"El acceso directo al Django Admin se puede ver por cualquiera en la barra de navegación; ocúltalo para todos los usuarios y déjalo visible exclusivamente para usuarios administradores (staff/superuser)."

**Resultado:**
- Se condicionó la visualización del botón de Django Admin en `Templates/base.html` con la directiva `{% if user.is_authenticated and user.is_staff %}`.
- De esta manera, los usuarios anónimos y socios regulares (`juan.activo`, `maria.congelada`, etc.) no ven el enlace al panel administrativo, preservando el principio de seguridad por rol y dejando el acceso visible únicamente al superusuario `admin`.


---

## 12. Optimización del Control de Aforo con Conteo de Socios Únicos
**Prompt solicitado a la IA:**
"Si un mismo socio escanea varias veces su código QR, los ingresos se acumulaban inflando el aforo; modifica la lógica para que el aforo en sala conserve y cuente únicamente a cada socio una sola vez (IDs únicos)."

**Resultado:**
- Se actualizó el cálculo de `aforo_actual` en `dashboard_view` y `DashboardAforoApiView` agregando `.values('membresia__usuario').distinct().count()`.
- Ahora, sin importar cuántas veces pase su QR un socio en la ventana reciente, en el aforo físico de las instalaciones cuenta estrictamente como 1 persona presente.


---

## 13. Restricción del Panel de Pruebas de Torniquete por Roles
**Prompt solicitado a la IA:**
"En el simulador de torniquete, los socios regulares podían ver y simular los códigos QR de los demás usuarios; oculta las tarjetas de prueba rápida para socios normales y déjalas visibles únicamente para el administrador, permitiendo a los socios normales escanear solo su propio código QR."

**Resultado:**
- En `Templates/simulador_acceso.html`, se encapsuló la lista de membresías de prueba dentro de `{% if user.is_authenticated and user.is_staff %}`.
- Para socios regulares autenticados, se dispuso un botón personal exclusivo (`Escanear Mi Carnet`) que valida únicamente su propio `user.membresia.codigo_qr`, impidiendo que un usuario suplante a otros en el simulador.


---

## 14. Integración de Autenticación Stateless con JWT (Evaluación 4)
**Prompt solicitado a la IA:**
"Configura la autenticación y autorización basada en tokens JWT en FitLife utilizando `djangorestframework-simplejwt`. Configura los endpoints `/api/token/` y `/api/token/refresh/`, añade los ajustes de expiración (2h de Access y 7d de Refresh) y protege los ViewSets con `IsAuthenticatedOrReadOnly` para que cualquier operación de escritura requiera un token Bearer válido."

**Resultado:**
- Se instaló y configuró `rest_framework_simplejwt` en `requirements.txt` y `core/settings.py`.
- Se añadieron `TokenObtainPairView` y `TokenRefreshView` en `gimnasio/urls.py`.
- Se configuró la política global `IsAuthenticatedOrReadOnly`, garantizando que la lectura de planes y clases sea pública, pero la creación, modificación y eliminación requiera el token en la cabecera `Authorization: Bearer <token>`.


---

## 15. Configuración y Demostración de Criptografía de Contraseñas (Evaluación 4)
**Prompt solicitado a la IA:**
"Ajusta la configuración de `PASSWORD_HASHERS` en Django para evidenciar el almacenamiento irreversible de contraseñas mediante PBKDF2 y Argon2, explicando el rol del salt y las iteraciones frente a algoritmos vulnerables como MD5 o SHA-1."

**Resultado:**
- Se definió la lista `PASSWORD_HASHERS` en `core/settings.py` priorizando `PBKDF2PasswordHasher` con 720.000 iteraciones y soporte para `Argon2` y `BCrypt`.
- Se documentó en el informe técnico la estructura del hash almacenado en PostgreSQL (`pbkdf2_sha256$720000$...`), demostrando que las contraseñas nunca se guardan en texto plano y que el salt único por usuario anula ataques de tablas arcoíris.


---

## 16. Construcción de la Consola Cliente REST Interactiva (Evaluación 4)
**Prompt solicitado a la IA:**
"Diseña una interfaz web interactiva que consuma la API REST de FitLife usando JavaScript nativo. Debe permitir obtener tokens JWT, refrescarlos, visualizar los tokens activos, y realizar operaciones CRUD completas (GET, POST, PUT, DELETE) con un interruptor para enviar o no la cabecera Authorization: Bearer, demostrando los códigos HTTP 200, 201, 401 y 403 en vivo."

**Resultado:**
- Se creó `Templates/api_cliente.html` y la vista `api_cliente_view` en `/api-cliente/`.
- La interfaz cuenta con presets de credenciales, visualizador de tokens, consola HTTP con selector de métodos y endpoints, plantillas JSON predefinidas para planes y clases, medición de latencia y visor de respuestas JSON con badges de estado HTTP.


---

## 17. Script de Verificación de Rate Limiting y Throttling en API Gateway (Evaluación 4)
**Prompt solicitado a la IA:**
"Desarrolla un script en Python que envíe una ráfaga concurrente de peticiones HTTP a un endpoint de la API para probar el mecanismo de Throttling (2 req/s con burst de 5), evidenciando el código de estado HTTP 429 Too Many Requests y generando un reporte en consola."

**Resultado:**
- Se creó el script `deploy/test_rate_limit.py` utilizando `ThreadPoolExecutor` y `urllib.request`.
- El script permite configurar URL, cantidad de peticiones y concurrencia, imprimiendo una tabla en tiempo real con latencias y códigos HTTP, destacando las peticiones aceptadas (200) y limitadas (429) con un resumen estadístico.


---

## 18. Elaboración del Informe Técnico y Banco de Preguntas Oral (Evaluación 4)
**Prompt solicitado a la IA:**
"Genera el informe técnico completo para la Evaluación 4 cubriendo las 8 actividades de la rúbrica (DRF & JWT, SAST SonarQube, DAST OWASP ZAP, Hashing de contraseñas, Amazon API Gateway, Amazon RDS con Security Groups, Amazon S3 con Block Public Access, CloudWatch/SNS, y respaldos automáticos cada 7 horas con EventBridge y Lambda) más las respuestas detalladas para los cuatro bloques de preguntas del examen oral."

**Resultado:**
- Se generó el documento maestro `deploy/INFORME_TECNICO_EVALUACION_4.md` con más de 400 líneas de contenido técnico riguroso, diagramas de arquitectura, comandos de escaneo, tablas comparativas, código Lambda en Python para backups y las respuestas a las 20 preguntas del banco oral (Bloques A, B, C y D).
