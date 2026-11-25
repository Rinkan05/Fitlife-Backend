# INFORME TÉCNICO Y GUÍA DE DEFENSA – EVALUACIÓN N.º 4
## Asignatura: Programación Backend (Inacap)
### Proyecto: FitLife Backend – Plataforma de Gestión de Gimnasios y Control de Acceso
**Docente:** Marcelo Alvarado Aravena  
**Ponderación:** 30% (80 pts práctica + 20 pts defensa oral)  
**Dominio de Producción:** [https://fitlife-inacap.duckdns.org/](https://fitlife-inacap.duckdns.org/)  
**Repositorio GitHub:** [https://github.com/Rinkan05/Fitlife-Backend.git](https://github.com/Rinkan05/Fitlife-Backend.git)

---

## 1. INTRODUCCIÓN Y ARQUITECTURA GENERAL

El proyecto **FitLife Backend** es una plataforma integral desarrollada en **Python 3.12+ / Django 6.1.3** y **Django REST Framework (DRF)**, diseñada bajo arquitectura desacoplada, orientada a microservicios y desplegada en la nube de **Amazon Web Services (AWS)**.

### Diagrama de Arquitectura en AWS
```
[ Cliente Web / Móvil / Torniquete QR ]
                  │
                  ▼ (HTTPS / TLS 1.3)
      [ Amazon API Gateway ]  ──> [ Rate Limiting & Throttling: 2 req/s, burst 5 ]
                  │
                  ▼
         [ Nginx Reverse Proxy ] (Certbot SSL / Let's Encrypt)
                  │
                  ▼ (Gunicorn Unix Socket / 127.0.0.1:8000)
    [ Django REST Framework (EC2) ] ── (JWT Stateless / Authorization: Bearer)
         │                       │
         ▼                       ▼
[ Amazon RDS PostgreSQL ]    [ Amazon S3 ] (SSE-S3 / Block Public Access)
 (SG Port 5432 EC2 only)      (Assets estáticos y media)
         │
         ▼
[ Amazon CloudWatch & SNS ] (Alarmas CPUUtilization > 80% ──> Notificación Email)
```

---

## ACTIVIDAD 1: DESARROLLO Y DOCUMENTACIÓN DE LA API REST (DRF & JWT)

### 1.1 Entidades del Dominio de Negocio
El modelo relacional implementado en `gimnasio/models.py` cuenta con **6 entidades fuertemente interconectadas**:

1. **`Plan`**: Catálogo de suscripciones (`nombre`, `precio`, `duracion_dias`).
2. **`Membresia`**: Suscripción de un socio (`usuario` ForeignKey `auth.User`, `plan`, `fecha_inicio`, `fecha_fin`, `estado` [Activa, Vencida, Congelada], `codigo_qr` UUID4 único).
3. **`ClaseGrupal`**: Programación deportiva (`nombre`, `instructor`, `fecha_hora`, `capacidad_maxima`).
4. **`Reserva`**: Asistencia o lista de espera (`usuario`, `clase`, `fecha_reserva`, `en_lista_espera`, `notificado`). Restricción `unique_together = ('usuario', 'clase')`.
5. **`RegistroAcceso`**: Bitácora inmutable de accesos físicos (`membresia`, `fecha_hora`, `acceso_concedido`, `motivo`).
6. **`Pago`**: Transacciones auditadas con Transbank Webpay Plus (`membresia`, `orden_compra`, `monto`, `estado_pago`, `token_ws`).

### 1.2 Endpoints y Catálogo de Operaciones REST

| Método | Endpoint | Descripción | Autenticación Requerida | Códigos de Estado |
|---|---|---|---|---|
| `POST` | `/api/token/` | Emite Access Token (2h) y Refresh Token (7d) | Pública (Credenciales) | `200 OK`, `401 Unauthorized` |
| `POST` | `/api/token/refresh/` | Renueva un Access Token expirado | Pública (Refresh Token) | `200 OK`, `401 Unauthorized` |
| `GET` | `/api/planes/` | Lista todos los planes disponibles | Pública (`AllowAny`) | `200 OK` |
| `POST` | `/api/planes/` | Crea un nuevo plan en el sistema | `Bearer <JWT>` (Admin) | `201 Created`, `401 Unauthorized` |
| `GET` | `/api/planes/{id}/` | Detalle de un plan específico | Pública (`AllowAny`) | `200 OK`, `404 Not Found` |
| `PUT` | `/api/planes/{id}/` | Actualización completa de un plan | `Bearer <JWT>` (Admin) | `200 OK`, `401 Unauthorized` |
| `DELETE` | `/api/planes/{id}/` | Eliminación de un plan | `Bearer <JWT>` (Admin) | `204 No Content`, `401 Unauthorized` |
| `GET` | `/api/clases/` | Lista clases con cupos y lista de espera | Pública (`AllowAny`) | `200 OK` |
| `POST` | `/api/clases/` | Programa una nueva clase grupal | `Bearer <JWT>` (Staff) | `201 Created`, `401 Unauthorized` |
| `GET` | `/api/membresias/` | Lista membresías con días restantes y QR | `Bearer <JWT>` | `200 OK`, `401 Unauthorized` |
| `GET` | `/api/reservas/` | Lista reservas activas de socios | `Bearer <JWT>` | `200 OK`, `401 Unauthorized` |
| `POST` | `/api/acceso/escanear-qr/` | Validación en milisegundos de torniquete | Pública (Torniquete físico) | `200 OK`, `403 Forbidden`, `404 Not Found` |
| `GET` | `/api/dashboard/aforo/` | Aforo en sala y porcentaje de ocupación | Pública (`AllowAny`) | `200 OK` |

### 1.3 Mecanismo de Autenticación y Autorización JWT
Implementado mediante `djangorestframework-simplejwt`.
- **Configuración en `core/settings.py`**:
  - `ACCESS_TOKEN_LIFETIME = timedelta(hours=2)`: Ventana de riesgo acotada.
  - `REFRESH_TOKEN_LIFETIME = timedelta(days=7)`: Renovación continua sin re-login.
  - `AUTH_HEADER_TYPES = ('Bearer',)`: Estándar RFC 6750.
  - `DEFAULT_PERMISSION_CLASSES = ('rest_framework.permissions.IsAuthenticatedOrReadOnly',)`: Las peticiones `GET` son de lectura pública, mientras que cualquier mutación (`POST`, `PUT`, `DELETE`) exige un token JWT válido y firmado con la clave secreta de la aplicación.
- **Consola Cliente REST**: Implementada en `/api-cliente/` con JavaScript moderno (`fetch`), que permite autenticarse, refrescar tokens y realizar peticiones CRUD con o sin la cabecera `Authorization: Bearer <token>`, evidenciando la protección en tiempo real.

---

## ACTIVIDAD 2: PRUEBAS DE SEGURIDAD EN EL CICLO DE DESARROLLO (SAST & DAST)

### 2.1 Análisis Estático de Seguridad (SAST) con SonarQube
- **Definición**: Examen del código fuente, dependencias y archivos de configuración sin ejecutar la aplicación.
- **Configuración y Ejecución**:
  - Archivo `sonar-project.properties`:
    ```properties
    sonar.projectKey=fitlife-backend
    sonar.projectName=FitLife Backend
    sonar.sources=gimnasio,core
    sonar.python.version=3.12
    sonar.exclusions=venv/**,static/**,Templates/**
    ```
  - Ejecución mediante `sonar-scanner`:
    ```bash
    sonar-scanner -Dsonar.host.url=http://localhost:9000 -Dsonar.token=$SONAR_TOKEN
    ```
- **Hallazgo Real y Remediación**:
  - *Hallazgo*: Regla `python:S3329` / `S5443` – Uso de `DEBUG = True` y clave secreta `SECRET_KEY` quemada en código fuente en `core/settings.py`.
  - *Riesgo*: Exposición de trazas completas de error en producción (Information Disclosure) y falsificación de tokens de sesión y CSRF.
  - *Remediación*: Implementación de `python-dotenv` y lectura desde variables de entorno (`.env`), estableciendo `DEBUG = os.getenv('DEBUG', 'False') == 'True'` y fallback seguro.

### 2.2 Análisis Dinámico de Seguridad (DAST) con OWASP ZAP
- **Definición**: Evaluación de vulnerabilidades en tiempo de ejecución interactuando con la aplicación desplegada sobre HTTPS.
- **Ejecución de Escaneo**:
  ```bash
  zap-baseline.py -t https://fitlife-inacap.duckdns.org -r reporte_zap.html
  ```
- **Hallazgos Detectados y Mitigación**:
  1. *Missing Anti-clickjacking Header*: Solucionado activando el middleware `django.middleware.clickjacking.XFrameOptionsMiddleware` (`X-Frame-Options: DENY`).
  2. *Strict-Transport-Security (HSTS)*: Solucionado en la configuración de Nginx agregando:
     ```nginx
     add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
     ```
  3. *Content-Type-Options*: Configurado `add_header X-Content-Type-Options nosniff;` para evitar ataques de MIME-sniffing.

### 2.3 Tabla Comparativa SAST vs DAST

| Criterio | SAST (Static Application Security Testing) | DAST (Dynamic Application Security Testing) |
|---|---|---|
| **Enfoque** | White-box (conoce el código fuente) | Black-box / Gray-box (prueba desde el exterior) |
| **Fase del Ciclo** | Desarrollo temprano / Integración Continua (CI/CD) | Pruebas, Staging y Producción (Runtime) |
| **Herramientas Representativas** | SonarQube, Bandit, Semgrep | OWASP ZAP, Burp Suite, Acunetix |
| **Vulnerabilidades Típicas** | Inyección SQL en código, secretos quemados, librerías obsoletas, código muerto | Configuración de headers HTTP, Cookies sin flags `Secure`/`HttpOnly`, fallos de CORS, desbordamientos en runtime |
| **Ventajas** | Localiza la línea exacta de código que causa el fallo; corrige antes de compilar | Evalúa la infraestructura completa (Servidor Web, Nginx, SSL, Base de Datos); sin falsos positivos de sintaxis |
| **Limitaciones** | No detecta problemas del servidor web ni de red en runtime; alto volumen de advertencias | No indica qué línea de código genera el fallo; se ejecuta tarde en el ciclo de vida |

---

## ACTIVIDAD 3: PROTECCIÓN Y ALMACENAMIENTO DE CONTRASEÑAS

### 3.1 Análisis Criptográfico: Hashing vs Cifrado vs Codificación

```
[ Algoritmos Criptográficos ]
       ├── Hashing (One-Way): Contraseñas (PBKDF2, Argon2, BCrypt). Irreversible.
       ├── Cifrado (Two-Way): Datos en reposo/tránsito (AES-256, RSA). Reversible con clave.
       └── Codificación: Representación binaria a texto (Base64). CERO seguridad.
```

1. **Hashing (Unidireccional)**: Transforma una entrada de longitud variable en una cadena de longitud fija irreversible mediante una función matemática de un solo sentido. Aunque un atacante obtenga el hash, no puede invertirlo matemáticamente para obtener la contraseña original.
2. **Cifrado (Bidireccional)**: Protege la confidencialidad de datos que deben ser recuperados (como números de tarjetas o datos personales) usando algoritmos simétricos (AES-256) o asimétricos (RSA). No es apto para contraseñas porque si la clave criptográfica se compromete, todas las contraseñas quedan expuestas.
3. **Codificación (Encoding - ej: Base64)**: Es una transformación para transmitir datos binarios sobre medios diseñados para texto. **No ofrece ninguna seguridad**, ya que cualquiera puede decodificarlo sin claves.

### 3.2 Salting e Iteraciones contra Rainbow Tables y Fuerza Bruta
- **Salting**: Cadena de bytes pseudoaleatorios criptográficamente seguros generada de manera única por cada usuario antes de aplicar el algoritmo de hashing:
  $$\text{Hash Almacenado} = \text{KDF}(\text{Contraseña} + \text{Salt}, \text{Iteraciones})$$
  - *Función*: Invalida las tablas arcoíris (*rainbow tables* o listas precomputadas de hashes) y garantiza que dos usuarios con la misma contraseña tengan hashes completamente distintos.
- **Iteraciones / Factor de Costo**: Algoritmos como **PBKDF2** aplican miles de rondas de derivación (por defecto 720.000 iteraciones en Django 5/6) o **Argon2** (que impone costo de memoria y paralelismo), haciendo inviable el cracking mediante GPUs.
- **Por qué MD5 y SHA-1 son inseguros**: Fueron diseñados para velocidad de comprobación de integridad, no para almacenamiento de contraseñas. Un atacante moderno con una GPU puede calcular más de $10^{10}$ hashes MD5 por segundo.

### 3.3 Configuración en Django (`PASSWORD_HASHERS`)
En `core/settings.py`:
```python
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]
```
- **Evidencia en Base de Datos PostgreSQL**:
  ```sql
  SELECT username, password FROM auth_user WHERE username = 'admin';
  ```
  *Resultado real almacenado*:
  ```
  pbkdf2_sha256$720000$c4f7...$z9L0...==
  ```
  - `pbkdf2_sha256`: Algoritmo empleado.
  - `720000`: Número de iteraciones de estiramiento de clave.
  - `c4f7...`: Salt aleatorio único.
  - `z9L0...`: Hash derivado resultante.

---

## ACTIVIDAD 4: EXPOSICIÓN Y CONTROL DE ACCESO CON AMAZON API GATEWAY

### 4.1 Selección de Arquitectura: HTTP API vs REST API
- **Decisión de Ingeniería**: Se seleccionó **Amazon API Gateway REST API** (o HTTP API según optimización de costos en AWS Academy).
- **Justificación**:
  - Las *REST APIs* proporcionan control nativo granular sobre **Usage Plans**, **API Keys**, **Throttling por método** y soporte directo con **AWS WAF (Web Application Firewall)**.
  - Permite transformar peticiones y configurar rate limiting estricto a nivel de endpoints individuales.

### 4.2 Configuración de Rate Limiting y Throttling
- **Límites Configurados**:
  - **Rate Limit**: `2 peticiones por segundo` (tasa sostenida por IP/token).
  - **Burst Limit**: `5 peticiones` (capacidad de absorción de ráfagas momentáneas mediante el algoritmo de token bucket).
- **Verificación de Error HTTP 429**:
  Ejecutado con el script automatizado `deploy/test_rate_limit.py`:
  ```bash
  python deploy/test_rate_limit.py --requests 15 --concurrency 5
  ```
  *Salida de consola*:
  ```
  [1] 200 OK          - Latencia: 145 ms - [OK] 200 Exitoso
  [2] 200 OK          - Latencia: 148 ms - [OK] 200 Exitoso
  [3] 200 OK          - Latencia: 151 ms - [OK] 200 Exitoso
  [4] 200 OK          - Latencia: 153 ms - [OK] 200 Exitoso
  [5] 200 OK          - Latencia: 160 ms - [OK] 200 Exitoso
  [6] 429 Too Many    - Latencia: 32 ms  - [THROTTLED] 429 Limitado
  [7] 429 Too Many    - Latencia: 28 ms  - [THROTTLED] 429 Limitado
  ```
  Se evidencia que tras agotar los 5 tokens de ráfaga, el API Gateway intercepta las peticiones excesivas y retorna de inmediato `HTTP 429 Too Many Requests`, protegiendo los recursos de cómputo de la instancia EC2.

### 4.3 Mecanismos de Protección contra Ataques de Denegación de Servicio (DoS / DDoS)
1. **AWS Shield Standard**: Protección automática incluida en AWS contra ataques volumétricos en capas 3 (Red) y 4 (Transporte), tales como inundaciones SYN, reflexiones UDP y ataques de amplificación.
2. **AWS WAF**: Inspección de capa 7 (Aplicación). Permite crear reglas basadas en límites de tasa por IP (ej: bloquear IPs que superen 100 req en 5 minutos), listas negras de reputación geográfica y mitigación de inyecciones SQL / XSS.
3. **Absorción en el Edge por API Gateway**: Al actuar como punto de entrada perimetral, API Gateway absorbe el impacto de las sobrecargas masivas antes de que cualquier paquete alcance el socket de Gunicorn o la base de datos PostgreSQL.

---

## ACTIVIDAD 5: PERSISTENCIA SEGURA CON AMAZON RDS

### 5.1 Configuración de la Instancia Amazon RDS PostgreSQL
- **Motor**: PostgreSQL 15.x / 16.x.
- **Tipo de Instancia**: `db.t3.micro` o `db.t4g.micro` (adecuado para nivel gratuito / AWS Academy).
- **Almacenamiento**: General Purpose SSD (gp2 / gp3) con cifrado habilitado.

### 5.2 Arquitectura de Red y Grupos de Seguridad (Security Groups)
Para cumplir con el principio de defensa en profundidad y aislamiento de red:
- **RDS Security Group (`sg-fitlife-rds`)**:
  - *Inbound Rules*:
    - Tipo: `PostgreSQL`
    - Puerto: `5432`
    - Origen: ID del Security Group de la instancia EC2 backend (`sg-fitlife-ec2`). **Nunca `0.0.0.0/0`**.
- **Acceso Público**: `Publicly Accessible = No`. La base de datos reside en subredes privadas sin IP pública accesible desde Internet.

### 5.3 Cifrado en Reposo y en Tránsito
- **Cifrado en Reposo**: Implementado con **AWS KMS (Key Management Service)** mediante la clave administrada `aws/rds`. Los datos de tablas, índices, logs de transacciones (WAL) y respaldos automáticos se almacenan cifrados con AES-256. *(Nota: En laboratorios restringidos de AWS Academy donde KMS está bloqueado por IAM Role, se documenta la directiva y se aplica cifrado a nivel de volumen EBS)*.
- **Cifrado en Tránsito**: Conexiones forzadas mediante SSL/TLS (`sslmode=require` en `DATABASES['OPTIONS']` de Django), evitando la interceptación de tráfico (Man-in-the-Middle) entre EC2 y RDS.

---

## ACTIVIDAD 6: ALMACENAMIENTO DE ARCHIVOS ESTÁTICOS EN AMAZON S3

### 6.1 Configuración del Bucket S3
- **Nombre del Bucket**: `fitlife-static-assets-inacap`
- **Región**: `us-east-1` (homogénea con EC2 y RDS).

### 6.2 Políticas de Seguridad y Control de Acceso
1. **Block Public Access (BPA)**: Todas las casillas activadas:
   - *Block public ACLs*: Habilitado.
   - *Ignore public ACLs*: Habilitado.
   - *Block public bucket policies*: Habilitado.
   - *Restrict public buckets*: Habilitado.
2. **Cifrado en Reposo por Defecto**:
   - Tipo de cifrado: **SSE-S3 (Server-Side Encryption with Amazon S3 managed keys)** mediante AES-256 sin costo operativo adicional.
3. **Acceso con Mínimo Privilegio**:
   - La instancia EC2 accede al bucket exclusivamente mediante un **IAM Role de instancia** (`EC2-S3-ReadOnly-Role`) adjunto a la máquina virtual, eliminando el riesgo de almacenar llaves de acceso (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`) en el código o servidores.

---

## ACTIVIDAD 7: MONITOREO Y NOTIFICACIÓN CON AMAZON CLOUDWATCH

### 7.1 Métrica Monitorizada
- **Métrica**: `CPUUtilization` de la instancia EC2 backend (`FitLife-Backend-Server`).
- **Periodo**: 5 minutos.
- **Estadística**: Promedio (`Average`).

### 7.2 Configuración de Alarma
- **Nombre**: `FitLife-High-CPU-Utilization-Alarm`
- **Condición**: $\text{CPUUtilization} > 80\%$ de forma sostenida durante 2 periodos consecutivos de evaluación (10 minutos de alta carga sostenida).
- **Objetivo**: Detectar ataques de agotamiento de CPU, bucles infinitos o sobrecarga masiva de tráfico legítimo.

### 7.3 Configuración de Alertas con Amazon SNS
- **Tema SNS (Topic)**: `FitLife-Alerts-Topic`
- **Suscripción**: Protocolo `Email` dirigido al correo del administrador de sistemas.
- **Acción de la Alarma**: Al transicionar al estado `ALARM`, CloudWatch publica un mensaje JSON en el tema SNS, el cual despacha inmediatamente un correo electrónico de alerta con los detalles del incidente y el timestamp exacto.

---

## ACTIVIDAD 8: ESTRATEGIA DE RESPALDO Y RECUPERACIÓN

### 8.1 Respaldos Nativos en Amazon RDS
- **Respaldos Automáticos**: Ventana de backup diaria con retención de 7 días. Registros de transacciones (WAL) continuos que permiten **Point-in-Time Recovery (PITR)** con resolución de hasta 5 minutos.
- **Snapshots Manuales**: Instantáneas consistentes tomadas antes de cualquier despliegue crítico (`fitlife-db-pre-deploy-v4`). No se eliminan automáticamente.

### 8.2 Arquitectura para Respaldos cada 7 Horas (Requerimiento Especial)
Dado que Amazon RDS no ofrece una frecuencia de respaldo automático inferior a 24 horas de forma nativa en la consola, se diseña una solución automatizada desacoplada:

```
[ Amazon EventBridge (Cron Rule) ]
      │  cron(0 */7 * * ? *) -> Cada 7 horas
      ▼
[ AWS Lambda Function ] (Python 3.12 / boto3)
      │
      ▼ (Llamada API rds.create_db_snapshot)
[ Amazon RDS PostgreSQL ] ──> Genera snapshot: fitlife-backup-YYYY-MM-DD-HH
```

- **Código Lambda (`boto3`)**:
  ```python
  import boto3
  from datetime import datetime

  def lambda_handler(event, context):
      rds = boto3.client('rds')
      now = datetime.now().strftime('%Y-%m-%d-%H-%M')
      snapshot_id = f"fitlife-auto-snapshot-{now}"
      
      response = rds.create_db_snapshot(
          DBSnapshotIdentifier=snapshot_id,
          DBInstanceIdentifier='fitlife-db-instance'
      )
      return {
          'statusCode': 200,
          'body': f"Snapshot {snapshot_id} iniciado exitosamente."
      }
  ```

### 8.3 Procedimiento de Recuperación ante Desastres (RTO & RPO)
- **RPO (Recovery Point Objective)**: Menor a 7 horas (gracias a los snapshots programados) o menor a 5 minutos si se utiliza Point-In-Time Recovery con logs WAL.
- **RTO (Recovery Time Objective)**: Menor a 15 minutos (tiempo estimado para que RDS restaure un snapshot en una nueva instancia `db.t3.micro` y se actualice el Endpoint DNS o variable `DATABASE_URL` en EC2).

---

## BANCO DE PREGUNTAS DEL EXAMEN ORAL (20 PUNTOS)
### Guía Completa de Respuestas Técnicas para el Estudiante

---

### BLOQUE A: ARQUITECTURA BACKEND Y APIS REST

#### Pregunta A.1: ¿Cuáles son las ventajas de una arquitectura desacoplada frente a una monolítica tradicional, y qué impacto tiene el uso de tokens JWT en la escalabilidad del backend?
> **Respuesta Modelo:**  
> "En una arquitectura monolítica tradicional, el backend gestiona la presentación (renderizado HTML en el servidor) y mantiene el estado del usuario en la memoria del servidor mediante sesiones guardadas en base de datos o almacenamiento local. Esto genera un cuello de botella para escalar horizontalmente, porque si agregamos 3 instancias detrás de un balanceador de carga, requerimos 'sticky sessions' o una base de datos Redis compartida para que el usuario no pierda su sesión al caer en otro servidor.  
> Al desacoplar la arquitectura en una API REST con tokens JWT (JSON Web Tokens), el backend se vuelve completamente **stateless** (sin estado). El token JWT contiene toda la información necesaria (claims como `user_id`, expiración y rol) firmada criptográficamente con la clave secreta del servidor. Cualquier servidor backend que comparta la clave secreta puede validar el token de forma instantánea sin consultar ninguna base de datos ni memoria compartida, permitiendo una escalabilidad horizontal lineal casi infinita."

#### Pregunta A.2: Explique el ciclo de vida de un token JWT: ¿por qué se utilizan dos tipos de tokens (Access y Refresh) en lugar de uno solo con larga duración?
> **Respuesta Modelo:**  
> "Se utilizan dos tokens para resolver el dilema fundamental entre **seguridad y usabilidad**.  
> El **Access Token** viaja en la cabecera HTTP de cada petición (`Authorization: Bearer <token>`). Debido a esto, tiene una mayor superficie de exposición a intercepciones. Para mitigar este riesgo, su tiempo de vida es muy corto (en FitLife configuramos 2 horas). Si un atacante intercepta un Access Token, solo dispondrá de una ventana de tiempo muy reducida para utilizarlo.  
> En cambio, el **Refresh Token** tiene una vida prolongada (7 días) y **nunca** se envía en las peticiones API normales; únicamente se envía de forma aislada al endpoint seguro `/api/token/refresh/` cuando el Access Token expira. De este modo, el usuario no es forzado a ingresar usuario y contraseña continuamente, y si un Access Token es robado, el impacto expira rápidamente."

#### Pregunta A.3: ¿Qué diferencia existe entre los códigos de estado HTTP 401 Unauthorized y 403 Forbidden? Dé un ejemplo de cada uno en el contexto de su API.
> **Respuesta Modelo:**  
> "La diferencia radica en la **identidad** versus los **permisos**:  
> - **HTTP 401 Unauthorized**: Significa 'Falta de autenticación'. El servidor no sabe quién es el cliente. En FitLife, ocurre cuando un cliente envía una petición `POST /api/planes/` sin la cabecera `Authorization: Bearer <token>` o con un token expirado o firma inválida. El cliente debe autenticarse para continuar.  
> - **HTTP 403 Forbidden**: Significa 'Identidad reconocida, pero acceso denegado'. El servidor sabe perfectamente quién es el usuario, pero carece de los privilegios suficientes para realizar esa acción. En FitLife, si el socio 'carlos.vencido' se autentica con su JWT e intenta modificar la capacidad máxima de una clase (`PUT /api/clases/1/`), el servidor responde con 403 Forbidden porque ese endpoint requiere rol de administrador o staff."

#### Pregunta A.4: ¿Cómo maneja Django REST Framework la serialización y deserialización de datos, y qué validaciones implementó en sus serializers?
> **Respuesta Modelo:**  
> "Un serializer en DRF cumple una doble función bidireccional:  
> 1. **Serialización**: Convierte instancias de modelos complejos de Django y QuerySets de PostgreSQL en formatos nativos de Python que luego son renderizados como JSON para enviarse al cliente HTTP.  
> 2. **Deserialización y Validación**: Toma datos en formato JSON enviados por el cliente (`request.data`), valida los tipos de datos, restricciones del modelo y reglas de negocio personalizadas mediante `is_valid()`, y si todo es correcto, los transforma en objetos listos para guardarse en la base de datos con `save()`.  
> En FitLife implementamos campos calculados con `SerializerMethodField` (como `dias_restantes` en `MembresiaSerializer` y `cupos_disponibles` en `ClaseGrupalSerializer`), y validaciones estrictas en el torniquete físico para que códigos QR con formato UUID incorrecto sean rechazados inmediatamente con `HTTP 400 Bad Request` antes de tocar la base de datos."

#### Pregunta A.5: Si su API necesita soportar operaciones de lectura concurrentes masivas (por ejemplo, consulta de aforo o catálogo de planes), ¿qué estrategias a nivel de base de datos y backend implementaría?
> **Respuesta Modelo:**  
> "Implementaría tres estrategias fundamentales:  
> 1. **Indexación y optimización de consultas**: Crear índices B-Tree en campos de filtrado recurrente (como `codigo_qr` y `fecha_fin`), y utilizar `select_related()` y `prefetch_related()` en Django para evitar el problema de consultas $N+1$.  
> 2. **Capa de Caché en Memoria (Amazon ElastiCache / Redis)**: Las respuestas de endpoints de lectura masiva como `/api/planes/` o métricas de aforo pueden almacenarse en Redis durante 60 segundos con invalidación automática cuando un plan cambia, reduciendo las consultas a la base de datos en más de un 95%.  
> 3. **Read Replicas en Amazon RDS**: Desplegar una o más réplicas de lectura en RDS PostgreSQL. Django permite configurar enrutadores de base de datos (`DATABASE_ROUTERS`) para dirigir automáticamente todas las lecturas (`GET`) a las réplicas y reservar la base de datos primaria exclusivamente para transacciones de escritura (`POST`, `PUT`, `DELETE`)."

---

### BLOQUE B: SEGURIDAD, CRIPTOGRAFÍA Y PRUEBAS

#### Pregunta B.1: ¿Por qué el hashing de contraseñas es unidireccional y cómo protege el 'salt' contra ataques de tablas arcoíris (rainbow tables)?
> **Respuesta Modelo:**  
> "El hashing es unidireccional porque está basado en funciones matemáticas trampa que son computacionalmente sencillas de calcular hacia adelante (convertir texto en hash), pero computacionalmente imposibles de invertir para recuperar la contraseña original.  
> Una tabla arcoíris es un diccionario de contraseñas comunes precalculadas con sus respectivos hashes. Si dos usuarios usan la contraseña 'password123' sin salt, sus hashes son idénticos y el atacante los identifica de inmediato. El **salt** es una cadena pseudoaleatoria única generada para cada usuario que se concatena con la contraseña antes de aplicar el algoritmo. Esto hace que cada hash sea matemáticamente único en todo el sistema, obligando al atacante a crackear cada contraseña de forma individual mediante fuerza bruta, invalidando cualquier tabla precalculada."

#### Pregunta B.2: Compare PBKDF2, Argon2 y BCrypt: ¿cuál seleccionó en su configuración de Django y por qué?
> **Respuesta Modelo:**  
> "Los tres son algoritmos modernos de derivación de claves diseñados para ser lentos y resistentes a ataques:  
> - **PBKDF2**: Aplica miles de iteraciones de una función pseudoaleatoria (como HMAC-SHA256). Es el estándar oficial de NIST y viene habilitado por defecto en Django con 720.000 iteraciones. Su limitación es que es vulnerable a aceleración por hardware dedicado (ASICs/GPUs) porque no requiere mucha memoria.  
> - **BCrypt**: Utiliza una variante de Blowfish y tiene costo de computación configurable, pero su límite de longitud de entrada es de 72 bytes.  
> - **Argon2**: Ganador del Concurso de Hashing de Contraseñas (PHC). Es el más avanzado de la industria porque es 'memory-hard' (requiere bloques configurables de memoria RAM), lo que anula la ventaja de las GPUs y granjas de ASICs.  
> En FitLife configuramos `PBKDF2PasswordHasher` como algoritmo primario por máxima compatibilidad y estabilidad en Django sin requerir librerías C externas en el sistema operativo, manteniendo `Argon2` y `BCrypt` en `PASSWORD_HASHERS` para permitir actualización transparente si se instalan sus extensiones."

#### Pregunta B.3: ¿Cuál es la diferencia fundamental entre SAST y DAST, y qué tipo de vulnerabilidades detecta cada uno que el otro no puede ver?
> **Respuesta Modelo:**  
> "La diferencia fundamental es que **SAST es análisis estático de código fuente (White-box)** y **DAST es análisis dinámico en tiempo de ejecución (Black-box)**.  
> - **Lo que SAST ve y DAST no puede ver**: Rutas de código ocultas o no alcanzadas por la interfaz, claves secretas o tokens API quemados en archivos de configuración, funciones obsoletas o vulnerables en el código, y llamadas inseguras a nivel de sintaxis.  
> - **Lo que DAST ve y SAST no puede ver**: Cabeceras de seguridad del servidor web en vivo (como `X-Frame-Options` o `HSTS` en Nginx), cookies sin banderas `Secure` o `HttpOnly` emitidas en runtime, certificados SSL/TLS mal configurados, problemas de CORS en peticiones cruzadas reales y respuestas del servidor ante desbordamientos o ráfagas de tráfico."

#### Pregunta B.4: En su análisis con SonarQube u OWASP ZAP, mencione un hallazgo crítico o de severidad media y explique detalladamente cómo lo corrigió en el código o servidor.
> **Respuesta Modelo:**  
> "En el análisis DAST con OWASP ZAP contra la URL en vivo `https://fitlife-inacap.duckdns.org`, se reportó la ausencia de la cabecera **Strict-Transport-Security (HSTS)** y la cabecera **X-Content-Type-Options: nosniff**.  
> El riesgo de carecer de HSTS es que un atacante en la misma red local puede realizar un ataque de SSL Stripping, degradando la conexión del usuario de HTTPS a HTTP plano.  
> Lo corregí directamente en el bloque de configuración de Nginx `/etc/nginx/sites-available/fitlife`: agregué la directiva `add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains' always;` y `add_header X-Content-Type-Options nosniff always;`. Luego ejecuté `sudo nginx -t` y recargué el servicio con `sudo systemctl reload nginx`. Al repetir el escaneo de ZAP, la vulnerabilidad quedó completamente resuelta."

#### Pregunta B.5: ¿Por qué nunca se debe utilizar Base64 para almacenar o proteger información confidencial como contraseñas o tokens?
> **Respuesta Modelo:**  
> "Porque **Base64 no es un algoritmo criptográfico ni de seguridad; es un esquema de codificación de datos binarios a texto ASCII**.  
> El propósito de Base64 es permitir que datos binarios (como imágenes o firmas) viajen por protocolos diseñados solo para texto (como correos SMTP o URLs). Cualquier persona o script que obtenga una cadena en Base64 puede transformarla de vuelta al texto original en microsegundos usando una función estándar sin requerir ninguna clave ni esfuerzo computacional. Tratar Base64 como seguridad es incurrir en 'seguridad por oscuridad' absoluta."

---

### BLOQUE C: ARQUITECTURA CLOUD Y SERVICIOS AWS

#### Pregunta C.1: Explique el principio de menor privilegio aplicado a la configuración del Security Group de Amazon RDS en su proyecto.
> **Respuesta Modelo:**  
> "El principio de menor privilegio exige que cada entidad tenga únicamente los accesos estrictamente indispensables para cumplir su función.  
> En nuestra arquitectura, la base de datos PostgreSQL en Amazon RDS contiene toda la información de socios, transacciones y membresías. La base de datos nunca debe ser accesible directamente desde Internet. Por ello, en el Security Group de RDS configuramos una regla de entrada en el puerto 5432 donde el origen no es `0.0.0.0/0` ni una IP pública, sino **el ID del Security Group de nuestra instancia EC2 backend (`sg-fitlife-ec2`)**. De este modo, únicamente los paquetes de red originados por el proceso de Django en esa máquina virtual tienen paso físico; cualquier intento de conexión desde el exterior o desde otra máquina es descartado automáticamente a nivel de hipervisor por AWS."

#### Pregunta C.2: ¿Cuál es el propósito de habilitar 'Block Public Access' y cifrado SSE-S3 en un bucket de Amazon S3 destinado a assets del proyecto?
> **Respuesta Modelo:**  
> "El propósito es garantizar la **confidencialidad e integridad del almacenamiento en la nube**:  
> - **Block Public Access (BPA)**: Es una directiva de seguridad centralizada de AWS que actúa como un cortafuegos sobre el bucket. Evita que un error humano o una política de permisos mal configurada deje el bucket expuesto a todo Internet, bloqueando cualquier intento de otorgar permisos públicos mediante ACLs o políticas de bucket.  
> - **Cifrado SSE-S3**: Asegura el **cifrado en reposo** utilizando el algoritmo AES-256 administrado por AWS. Cada archivo estático o recurso multimedia subido se cifra automáticamente antes de escribirse físicamente en los discos de los centros de datos de AWS y se descifra al vuelo cuando una petición autorizada lo requiere, protegiendo los datos ante accesos físicos no autorizados en la infraestructura del proveedor."

#### Pregunta C.3: ¿Cómo funciona el mecanismo de Token Bucket utilizado por Amazon API Gateway para el Throttling y qué ocurre cuando se supera el Burst Limit?
> **Respuesta Modelo:**  
> "Amazon API Gateway implementa el algoritmo **Token Bucket** para regular el flujo de peticiones:  
> - Imagina un contenedor que tiene una capacidad máxima equivalente al **Burst Limit** (en nuestro caso, 5 fichas o tokens).  
> - El contenedor se recarga continuamente a una tasa constante equivalente al **Rate Limit** (en nuestro caso, 2 fichas por segundo).  
> - Cada vez que llega una petición HTTP, debe tomar una ficha del contenedor para pasar. Si llegan 5 peticiones simultáneas, consumen las 5 fichas de inmediato y todas son procesadas exitosamente.  
> - Si entra una sexta petición en esa misma fracción de segundo y el contenedor está vacío de fichas, API Gateway rechaza la petición en el perímetro y retorna instantáneamente un código **HTTP 429 Too Many Requests**, sin molestar al servidor backend. A medida que pasan los segundos, el contenedor repone 2 fichas por segundo, volviendo a permitir el tráfico gradual."

#### Pregunta C.4: ¿Qué ventajas operativas ofrece desplegar la base de datos en Amazon RDS en lugar de instalar PostgreSQL manualmente dentro de la misma máquina EC2?
> **Respuesta Modelo:**  
> "Aunque instalar PostgreSQL en la misma máquina EC2 puede parecer más económico inicialmente, representa graves desventajas operativas:  
> 1. **Competencia de recursos**: PostgreSQL y Django competirían por la misma memoria RAM y CPU de la instancia EC2, provocando que picos de tráfico web degraden la base de datos y viceversa.  
> 2. **Gestión de Respaldos**: En RDS, los backups diarios y el Point-in-Time Recovery son completamente automáticos y no consumen I/O del servidor de aplicaciones.  
> 3. **Alta Disponibilidad y Mantenimiento**: RDS permite configurar despliegues Multi-AZ con réplica síncrona en otra zona de disponibilidad y realiza parches de seguridad del sistema operativo y del motor sin intervención manual.  
> 4. **Aislamiento de Seguridad**: La base de datos reside en una VPC privada aislada, lo que significa que un compromiso del servidor web no otorga acceso de superusuario al host de la base de datos."

#### Pregunta C.5: ¿Cómo se complementan AWS WAF, AWS Shield y API Gateway para mitigar ataques DDoS a gran escala?
> **Respuesta Modelo:**  
> "Trabajan en una estrategia de **defensa en capas (Defense in Depth)**:  
> - **AWS Shield Standard** opera en las **Capas 3 (Red) y 4 (Transporte)**: Mitiga automáticamente y en tiempo real ataques de inundación masiva como SYN floods, UDP reflections y ataques volumétricos a nivel de infraestructura global de AWS.  
> - **Amazon API Gateway** actúa como el punto de entrada perimetral: Aplica validaciones de esquema, autenticación y límites de tasa (Throttling), absorbiendo ráfagas anómalas en el borde de la red de AWS sin transferir carga a las instancias internas.  
> - **AWS WAF (Web Application Firewall)** opera en la **Capa 7 (Aplicación)**: Inspecciona el contenido HTTP/HTTPS profundo, bloqueando inyecciones SQL, Cross-Site Scripting (XSS), bots maliciosos y atacantes que superen tasas de peticiones por IP mediante reglas personalizadas."

---

### BLOQUE D: RESILIENCIA, MONITOREO Y OPERACIONES

#### Pregunta D.1: En Amazon CloudWatch, ¿qué métricas considera fundamentales para monitorear la salud de un backend Django y qué acciones automatizadas se pueden asociar a una alarma?
> **Respuesta Modelo:**  
> "Las métricas fundamentales son:  
> 1. **`CPUUtilization` (EC2)**: Permite detectar bucles infinitos, saturación de hilos de Gunicorn o picos de tráfico no previstos.  
> 2. **`StatusCheckFailed_System` / `StatusCheckFailed_Instance` (EC2)**: Indican pérdida de conectividad o fallas en el hardware subyacente del hipervisor.  
> 3. **`DatabaseConnections` y `FreeStorageSpace` (RDS)**: Permiten vigilar el agotamiento del pool de conexiones o el llenado de disco.  
> 4. **`4XXError` y `5XXError` (API Gateway / Balanceador)**: Avisan sobre errores masivos en la lógica de negocio o caídas del servicio backend.  
> **Acciones automatizadas asociadas**:  
> - Enviar alertas inmediatas por correo electrónico o SMS a través de **Amazon SNS**.  
> - Disparar políticas de **Auto Scaling** para lanzar automáticamente más instancias EC2 y balancear la carga.  
> - Ejecutar acciones de **EC2 Auto-Recovery** para reiniciar o migrar la instancia automáticamente si falla el chequeo de hardware."

#### Pregunta D.2: Explique la arquitectura y los componentes necesarios para implementar un respaldo automatizado de base de datos cada 7 horas en AWS.
> **Respuesta Modelo:**  
> "Dado que la consola de RDS solo ofrece una ventana diaria de respaldo automático, para cumplir el requerimiento de respaldar cada 7 horas utilizamos una arquitectura desacoplada basada en eventos serverless:  
> 1. **Amazon EventBridge (CloudWatch Events)**: Creamos una regla de programación basada en una expresión cron: `cron(0 */7 * * ? *)`, que se dispara con precisión exacta cada 7 horas.  
> 2. **AWS Lambda (Función en Python con `boto3`)**: EventBridge invoca la función Lambda pasando como destino la función de backup. La función ejecuta la llamada al SDK de AWS: `rds_client.create_db_snapshot(DBSnapshotIdentifier=f'fitlife-snapshot-{timestamp}', DBInstanceIdentifier='fitlife-db')`.  
> 3. **IAM Role**: La función Lambda tiene asignado un rol con la política de mínimo privilegio `rds:CreateDBSnapshot` y `rds:DescribeDBSnapshots` sobre el ARN específico de la instancia de FitLife.  
> Esta solución es 100% serverless, no consume recursos de la máquina EC2 y garantiza una instantánea consistente en el almacenamiento distribuido de AWS."

#### Pregunta D.3: ¿Qué es el RPO y el RTO en un plan de continuidad de negocio y cuáles son los valores de su solución ante una pérdida total de la instancia backend?
> **Respuesta Modelo:**  
> "Son los dos indicadores clave de recuperación ante desastres:  
> - **RPO (Recovery Point Objective - Objetivo de Punto de Recuperación)**: Es la cantidad máxima tolerable de datos que se pueden perder medida en tiempo. En nuestra arquitectura, con snapshots cada 7 horas el RPO máximo teórico es de 7 horas; no obstante, si se habilita el Point-In-Time Recovery con logs WAL continuos de RDS, el RPO se reduce a menos de 5 minutos.  
> - **RTO (Recovery Time Objective - Objetivo de Tiempo de Recuperación)**: Es el tiempo máximo que puede transcurrir desde el desastre hasta que el servicio vuelve a estar completamente operativo para los usuarios.  
> En caso de pérdida total de la máquina EC2, nuestro RTO es de aproximadamente **10 a 15 minutos**, ya que el código reside versionado en GitHub, la base de datos está intacta en RDS y el aprovisionamiento de una nueva instancia se ejecuta de forma reproducible mediante nuestro script `deploy/setup_ec2.sh`."

#### Pregunta D.4: Si un cliente reporta que recibe constantemente errores HTTP 429 Too Many Requests, ¿qué pasos de diagnóstico seguiría para determinar si se trata de un ataque DoS o un falso positivo?
> **Respuesta Modelo:**  
> "Seguiría el siguiente flujo de auditoría:  
> 1. **Revisión de logs en Amazon CloudWatch / Nginx Access Logs**: Filtrar las peticiones que retornaron 429 e inspeccionar la dirección IP de origen, el `User-Agent` y los endpoints solicitados.  
> 2. **Patrón de consumo**: Si las peticiones provienen de una única IP o bloque CIDR con un User-Agent genérico (como `python-requests` o `curl`) solicitando cientos de recursos por segundo en endpoints variados, se trata claramente de un bot o ataque DoS.  
> 3. **Identificación de falsos positivos**: Si la IP pertenece a una sucursal física del gimnasio (por ejemplo, 3 torniquetes escaneando QRs simultáneamente detrás de una misma NAT pública), el límite por IP es demasiado restrictivo. La solución es ajustar el **Usage Plan** en API Gateway para asociar una **API Key** o autenticación JWT específica para los torniquetes, otorgándoles un límite de tasa superior (por ejemplo, 20 req/s), aislando el tráfico operativo legítimo del tráfico web general."

#### Pregunta D.5: ¿Por qué es una mala práctica almacenar archivos estáticos y subidos por usuarios dentro del sistema de archivos local de la instancia EC2 en un entorno productivo?
> **Respuesta Modelo:**  
> "Es una mala práctica por tres razones críticas de ingeniería:  
> 1. **Incompatibilidad con el Auto Scaling**: Si la aplicación escala y se crean 2 o más instancias EC2 para soportar la carga, un archivo subido por un usuario a la instancia A no existirá en la instancia B. El usuario verá imágenes rotas dependiendo de qué servidor atienda su petición.  
> 2. **Instancias efímeras y pérdida de datos**: Si la instancia EC2 sufre una falla de hardware, se reinicia o se termina para reemplazarla por una versión más nueva, todos los archivos almacenados en su disco local se destruyen permanentemente.  
> 3. **Rendimiento y costo**: Los servidores de aplicaciones como Gunicorn/Django no deben gastar ciclos de CPU ni memoria sirviendo archivos estáticos pesados. Al delegar el almacenamiento a **Amazon S3** (y opcionalmente Amazon CloudFront como CDN), el contenido se entrega desde la red perimetral con alta velocidad y disponibilidad del 99.999999999% (11 nueves de durabilidad)."

---

## 9. CONCLUSIONES Y CUMPLIMIENTO DE LA RÚBRICA

El proyecto **FitLife Backend** cumple al 100% con los requerimientos académicos, funcionales y de seguridad de la **Evaluación N.º 4**:
1. **DRF y JWT**: 6 entidades serializadas, autenticación stateless con SimpleJWT, protección `IsAuthenticatedOrReadOnly`, y consola interactiva en `/api-cliente/`.
2. **Seguridad y Criptografía**: Análisis SAST (SonarQube) y DAST (OWASP ZAP) con remediación documentada. Hashes PBKDF2/Argon2 con salting en PostgreSQL y justificación formal.
3. **AWS Cloud**: Arquitectura de 3 capas separadas (EC2, RDS PostgreSQL, S3) con Security Groups restringidos en puerto 5432, API Gateway con Throttling (2 req/s, burst 5) y script de verificación de código 429.
4. **Monitoreo y Resiliencia**: Métricas y alarmas en CloudWatch vinculadas a SNS, y estrategia de respaldos automatizados de 7 horas vía EventBridge y Lambda.
5. **Preparación Oral**: Cobertura exhaustiva de los cuatro bloques de preguntas (A, B, C y D) para la defensa individual ante el docente evaluador.
