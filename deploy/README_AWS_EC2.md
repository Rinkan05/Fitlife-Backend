# 🚀 Guía de Despliegue en AWS EC2 con DuckDNS y Transbank Webpay - FitLife Backend

Esta guía documenta los pasos para desplegar la aplicación **FitLife** (Django, DRF, PostgreSQL, Gunicorn, Nginx, Dominio DuckDNS y Pasarela Transbank Webpay Plus) en una máquina virtual de **Amazon Web Services (AWS EC2)**.

---

## 1. Requisitos Previos en AWS

1. **Crear una Instancia EC2**:
   - **AMI:** Ubuntu Server 22.04 LTS o 24.04 LTS (64-bit x86).
   - **Tipo de instancia:** `t2.micro` o `t3.micro` (Capa Gratuita / Free Tier).
   - **Key Pair:** Generar o seleccionar un par de claves `.pem` (ej: `fitlife-key.pem`).
   - **Almacenamiento:** 10 a 20 GB gp3.

2. **Configuración de Security Group (Reglas de Entrada / Inbound Rules)**:
   Debes habilitar los siguientes puertos en el Security Group de tu instancia en AWS:

   | Tipo | Protocolo | Puerto | Origen (Source) | Descripción |
   | :--- | :--- | :--- | :--- | :--- |
   | **SSH** | TCP | `22` | Tu IP o `0.0.0.0/0` | Conexión remota por terminal |
   | **HTTP** | TCP | `80` | `0.0.0.0/0` | Tráfico web Nginx |
   | **HTTPS** | TCP | `443` | `0.0.0.0/0` | Tráfico web seguro (SSL Let's Encrypt) |

---

## 2. Configurar Dominio Gratuito con DuckDNS

1. Ve a [https://www.duckdns.org/](https://www.duckdns.org/) e inicia sesión (Google, GitHub, etc.).
2. En la sección **domains**, ingresa el subdominio deseado (ej: `fitlife-gym`).
3. En el campo **current ip**, coloca la **Dirección IPv4 pública** de tu instancia AWS EC2.
4. Presiona **update ip**.
5. Copia tu **token** personal de DuckDNS (cadena alfanumérica en la parte superior).

---

## 3. Conexión SSH a la Instancia EC2

Desde tu máquina local:

```bash
# Permisos de solo lectura para la clave PEM
chmod 400 fitlife-key.pem

# Conectar a la IP pública de la instancia EC2
ssh -i "fitlife-key.pem" ubuntu@<TU_IP_PUBLICA_EC2>
```

---

## 4. Clonar el Repositorio y Ejecutar el Aprovisionamiento

Una vez dentro de la terminal de Ubuntu:

```bash
cd /home/ubuntu
git clone <URL_DE_TU_REPOSITORIO_GIT> fitlife-backend
cd fitlife-backend

# Dar permisos de ejecución a los scripts
chmod +x deploy/setup_ec2.sh
chmod +x deploy/duckdns_update.sh

# Ejecutar el aprovisionamiento automatizado (PostgreSQL, Nginx, Gunicorn, Python)
./deploy/setup_ec2.sh
```

---

## 5. Configurar el Cron de Actualización Dinámica DuckDNS

Para asegurar que tu subdominio de DuckDNS siempre apunte a tu EC2 aunque reinicies la máquina:

```bash
# Probar el script de actualización manual
./deploy/duckdns_update.sh "fitlife-gym" "TU_TOKEN_DUCKDNS_AQUI"

# Abrir el editor de tareas programadas (crontab)
crontab -e
```

Agrega la siguiente línea al final del archivo para que se actualice cada 10 minutos:
```cron
*/10 * * * * /home/ubuntu/fitlife-backend/deploy/duckdns_update.sh fitlife-gym TU_TOKEN_DUCKDNS_AQUI >/dev/null 2>&1
```

---

## 6. Variables de Entorno de Producción (`.env`)

Edita el archivo `.env` en la raíz del proyecto:

```bash
nano .env
```

Ajusta los valores con tu dominio de DuckDNS:
```ini
SECRET_KEY=clave-secreta-larga-y-aleatoria-de-produccion
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,fitlife-gym.duckdns.org,<TU_IP_PUBLICA_EC2>

DB_NAME=fitlife_db
DB_USER=fitlife_user
DB_PASSWORD=Inacap.2030
DB_HOST=localhost
DB_PORT=5432
```

Reinicia el servicio Gunicorn:
```bash
sudo systemctl restart fitlife
```

---

## 7. Configuración de Nginx y Certificado SSL Gratuito (HTTPS)

1. Ajusta tu archivo Nginx con tu dominio DuckDNS:
```bash
sudo nano /etc/nginx/sites-available/fitlife
# Asegúrate de que la directiva server_name tenga:
# server_name fitlife-gym.duckdns.org;
sudo nginx -t
sudo systemctl restart nginx
```

2. Genera el certificado SSL oficial con Certbot (Let's Encrypt):
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d fitlife-gym.duckdns.org
```
- Ingresa tu correo electrónico cuando te lo solicite.
- Acepta los términos de servicio (`Y`).
- Certbot modificará Nginx automáticamente para redirigir todo el tráfico HTTP a **HTTPS seguro**.

---

## 8. Pruebas de Transbank Webpay Plus en Producción

El sistema está integrado directamente con el ambiente de Integración oficial de Transbank.

Para simular pagos reales de membresías en `https://fitlife-gym.duckdns.org/planes/`:

1. Elige un plan y haz clic en **"Pagar con Webpay Plus"**.
2. Serás transferido a la pasarela bancaria de Transbank.
3. Utiliza los datos oficiales de tarjeta de prueba de Transbank:

| Tipo | Número de Tarjeta | Fecha Vencimiento | CVV | Clave Webpay |
| :--- | :--- | :--- | :--- | :--- |
| **Crédito (Aprobada)** | `4051 8856 0044 6623` | Mayor al mes actual (ej: `12/28`) | `123` | Clave: `123` (RUT: `11.111.111-1`) |
| **Crédito (Rechazada)** | `5186 0595 5959 0568` | Mayor al mes actual | `123` | - |

4. Al autorizar la compra, Transbank redirige a `pago/retorno/` donde se genera el voucher de comprobante con código de autorización y la membresía del socio queda **Activa** automáticamente con su código QR renovado.
