# 🏋️ FitLife - Plataforma de Control de Asistencia y Reserva de Clases

**Evaluación Parcial N°3: Desarrollo Backend (30%)**  
**Institución:** INACAP  
**Docente:** Marcelo Alvarado Aravena  
**Caso Asignado:** Proyecto 2 - FitLife  
**Stack Tecnológico:** Python, Django, Django REST Framework (DRF), PostgreSQL, Gunicorn, Nginx, AWS EC2, DuckDNS y Transbank Webpay Plus.

---

## 🌐 Enlaces de Acceso en Producción (AWS EC2)

* **URL Principal de la Aplicación (IP Pública / DNS):**  
  `http://<TU_IP_PUBLICA_O_ELASTICA>/` o `https://<TU_SUBDOMINIO>.duckdns.org/`
* **Panel de Administración (Django Admin):**  
  `http://<TU_IP_PUBLICA_O_ELASTICA>/admin/`  
  * **Usuario Administrador:** `admin`  
  * **Contraseña:** `admin123`
* **Simulador de Torniquete y Lector QR:**  
  `http://<TU_IP_PUBLICA_O_ELASTICA>/simulador-acceso/`
* **Control de Aforo en Tiempo Real:**  
  `http://<TU_IP_PUBLICA_O_ELASTICA>/`
* **Catálogo de Planes y Pago Webpay Plus:**  
  `http://<TU_IP_PUBLICA_O_ELASTICA>/planes/`
* **Reserva de Clases Grupales:**  
  `http://<TU_IP_PUBLICA_O_ELASTICA>/clases/`
* **Endpoints API REST (DRF):**  
  `http://<TU_IP_PUBLICA_O_ELASTICA>/api/`

---

## 📌 Cumplimiento de Requerimientos del Caso (FitLife)

| Requerimiento del Caso | Implementación Técnica | Estado |
| :--- | :--- | :---: |
| **1. CRUD y administración de Planes, Pagos y Estados de Membresía** | Modelos `Plan`, `Pago` y `Membresia` (estados: *Activa*, *Vencida*, *Congelada*). Integración real con **Transbank Webpay Plus** que activa o renueva la membresía automáticamente tras la aprobación bancaria. | ✔ 100% |
| **2. Validación y registro de acceso físico mediante lectura/simulación QR** | Generación de UUID único por socio. Endpoint de **baja latencia** (`/api/acceso/escanear-qr/`) optimizado con `select_related` y auditoría obligatoria en `RegistroAcceso`. Interfaz interactiva de torniquete con respuesta visual instantánea (Concedido/Denegado) y medición de milisegundos. | ✔ 100% |
| **3. Reserva de clases con manejo automático de cupos y lista de espera** | Transacciones atómicas (`transaction.atomic`) y bloqueo de fila (`select_for_update`) en PostgreSQL para evitar condiciones de carrera. Paso automático a **Lista de Espera** cuando el cupo está agotado y **promoción automática** al liberarse un cupo. | ✔ 100% |
| **4. Dashboard de control de aforo en tiempo real** | Tablero en vivo con cálculo de aforo en sala (ventana móvil de permanencia), porcentaje de ocupación respecto a capacidad máxima, ingresos del día y sondeo asíncrono cada 5 segundos vía AJAX. | ✔ 100% |

---

## 🛡️ Rúbrica de Evaluación y Criterios Técnicos

### 1. Base de Datos Relacional PostgreSQL
- Conexión configurada en [`core/settings.py`](core/settings.py) mediante variables de entorno para desarrollo local y producción en AWS EC2.
- Migraciones del ORM aplicadas: `0001_initial.py` y `0002_pago.py`.
- Integridad referencial con llaves foráneas (`ForeignKey`, `OneToOneField`) y transacciones atómicas.

### 2. Uso y Personalización Avanzada del Administrador de Django
- Configurado en [`gimnasio/admin.py`](gimnasio/admin.py):
  - **Badges visuales HTML** con colores para estados de membresía (*Verde*, *Amarillo*, *Rojo*) y estados de reservas.
  - **Acciones masivas:** cambiar estados en lote (*Marcar como Activa/Congelada/Vencida*).
  - **Inlines tabulares:** `ReservaInline` dentro de `ClaseGrupalAdmin` para visualizar y gestionar asistentes directamente.
  - **Búsquedas y filtros predictivos** por socio, plan, fechas y autocompletado en reservas.
  - **Auditoría protegida:** registros de acceso y pagos en modo solo lectura para garantizar trazabilidad.

### 3. Seguridad, Sesiones y Mitigación de Errores
- Manejo de sesiones de usuario con Django Authentication (`login_view`, `logout_view`).
- Decoradores `@login_required` para áreas restringidas (Mi Membresía, Reservas, Pagos).
- Mitigación de rutas inválidas (Error 404) mediante regla `re_path` y plantilla personalizada [`Templates/404.html`](Templates/404.html) con botón directo de retorno al dashboard.
- Protección CSRF configurada con `CSRF_TRUSTED_ORIGINS` para soporte de DuckDNS y Webpay.

### 4. Inteligencia Artificial como Apoyo al Desarrollo
- El archivo [`prompts_ia.md`](prompts_ia.md) detalla cronológicamente las 10 etapas de desarrollo asistido por IA, incluyendo prompts formulados, resultados técnicos, correcciones y optimizaciones.

### 5. Despliegue en AWS Cloud (EC2 + Gunicorn + Nginx + DuckDNS)
- La guía paso a paso basada en la **Receta AWS de INACAP** se encuentra documentada en:
  👉 [`deploy/RECETA_AWS_FITLIFE.md`](deploy/RECETA_AWS_FITLIFE.md)

---

## 🚀 Instrucciones de Ejecución Local

### 1. Clonar el Repositorio y Crear Entorno Virtual
```bash
git clone https://github.com/Rinkan05/Fitlife-Backend.git
cd Fitlife-Backend

python -m venv venv
# En Windows:
.\venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Migraciones y Carga Automática de Datos de Prueba
```bash
python manage.py migrate
python manage.py poblar_datos
```
> El comando `poblar_datos` crea automáticamente:
> - Superusuario: `admin` / `admin123`
> - Socios de prueba (clave: `socio123`):
>   - `juan.activo` (Membresía Activa)
>   - `maria.congelada` (Membresía Congelada)
>   - `carlos.vencido` (Membresía Vencida)
> - Clases grupales con cupos limitados para probar la lista de espera.
> - Planes de entrenamiento.

### 3. Iniciar Servidor de Desarrollo
```bash
python manage.py runserver
```
Accede a `http://127.0.0.1:8000/`.

---

## ☁️ Despliegue en AWS EC2 (Receta INACAP)

Para desplegar en una instancia Ubuntu en AWS EC2 siguiendo la receta oficial de la asignatura, consulta la guía detallada:
📄 [**deploy/RECETA_AWS_FITLIFE.md**](deploy/RECETA_AWS_FITLIFE.md)

Comandos rápidos de aprovisionamiento en la máquina virtual:
```bash
mkdir -p /home/ubuntu/apps && cd /home/ubuntu/apps
git clone https://github.com/Rinkan05/Fitlife-Backend.git fitlife-backend
cd fitlife-backend
chmod +x deploy/setup_ec2.sh
./deploy/setup_ec2.sh
```

---

## 💳 Tarjetas de Prueba para Transbank Webpay Plus (Sandbox)

Al presionar **"Pagar con Webpay Plus"** en `/planes/`:
* **Número de Tarjeta (Crédito Aprobada):** `4051 8856 0044 6623`
* **Vencimiento:** Cualquier fecha futura (ej: `12/28`) | **CVV:** `123`
* **Autenticación Banco Emisor:** RUT `11.111.111-1` | Clave: `123`
* **Tarjeta Rechazada:** `5186 0595 5959 0568`
