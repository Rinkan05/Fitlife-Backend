# 📋 Receta AWS Adaptada: Despliegue de FitLife Backend en EC2 (Inacap)

Esta guía adapta paso a paso la **Receta AWS de Inacap (Ubuntu + Gunicorn + Nginx + DRF)** específicamente para nuestro proyecto **FitLife Backend**, conectado a tu repositorio GitHub: `https://github.com/Rinkan05/Fitlife-Backend.git` y configurado con **PostgreSQL, DuckDNS y Transbank Webpay**.

---

## ETAPA 1: Preparar la Infraestructura en AWS (EC2 y VPC)

1. **Lanzar Instancia EC2**:
   - Consola AWS → **EC2** → **"Lanzar instancia"**.
   - **Nombre:** `fitlife-backend` (o el nombre que prefieras).
   - **AMI:** Ubuntu Server 22.04 LTS (x64).
   - **Tipo de instancia:** `t2.micro` o `t3.micro` (Capa gratuita / Free tier).
   - **Par de claves (Key Pair):** Selecciona o crea tu par de claves (ej: `claves.pem`).
   - **Configuración de red:**
     - VPC por defecto.
     - Asignación automática de IP pública: **Habilitar**.
   - **Grupo de seguridad (Security Group) - Reglas de Entrada (Inbound):**
     - **SSH (22):** Desde tu IP (o cualquier IP si estás en red variable).
     - **HTTP (80):** Desde cualquier IP (`0.0.0.0/0`).
     - **HTTPS (443):** Desde cualquier IP (`0.0.0.0/0`) para DuckDNS con SSL.
     - **ICMP (All ICMP - IPv4):** Para pruebas de ping.

2. **Asignar IP Elástica (Elastic IP)**:
   - EC2 → Red y seguridad → **"IPs elásticas"** → **Asignar nueva IP**.
   - Selecciona la IP recién asignada → Acciones → **"Asociar dirección IP elástica"** → Selecciona tu instancia `fitlife-backend`.

3. **Vincular a DuckDNS (Paso Extra)**:
   - Entra a [duckdns.org](https://www.duckdns.org/).
   - En tu subdominio (ej: `fitlife-inacap.duckdns.org`), actualiza el campo **current IP** con tu **IP Elástica** de AWS.

---

## ETAPA 2: Conectarte a la Instancia (desde Windows)

Abre **PowerShell** en tu equipo local:

```powershell
# Ir a la carpeta donde descargaste tu clave .pem
cd C:\Users\Maxi\Downloads

# Asegurar permisos estrictos en Windows (evita error "Permissions are too open")
icacls "claves.pem" /inheritance:r
icacls "claves.pem" /grant:r "$($env:USERNAME):R"

# Conectarte a la IP elástica
ssh -i "claves.pem" ubuntu@<TU_IP_ELASTICA>
```

---

## ETAPA 3: Configurar el Servidor Ubuntu e Instalar Paquetes

Una vez dentro de la consola de Ubuntu en AWS, ejecuta:

```bash
# 1. Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar herramientas, Python, Nginx, Git y PostgreSQL
sudo apt install python3-pip python3-venv nginx git libpq-dev postgresql postgresql-contrib -y
```

---

## ETAPA 4: Descargar FitLife desde GitHub y Configurar Base de Datos

En lugar de crear un proyecto vacío, clonamos directamente tu proyecto FitLife en la carpeta estándar `/home/ubuntu/apps`:

```bash
# 1. Crear directorio apps
mkdir -p /home/ubuntu/apps && cd /home/ubuntu/apps

# 2. Clonar tu repositorio oficial
git clone https://github.com/Rinkan05/Fitlife-Backend.git fitlife-backend
cd fitlife-backend

# 3. Crear y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate

# 4. Instalar las dependencias del proyecto
pip install --upgrade pip
pip install -r requirements.txt

# 5. Configurar PostgreSQL local en Ubuntu
sudo -u postgres psql -c "CREATE DATABASE fitlife_db;"
sudo -u postgres psql -c "CREATE USER fitlife_user WITH PASSWORD 'Inacap.2030';"
sudo -u postgres psql -c "ALTER ROLE fitlife_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE fitlife_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE fitlife_user SET timezone TO 'America/Santiago';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE fitlife_db TO fitlife_user;"

# 6. Crear archivo .env para producción
cp .env.example .env
nano .env
```

> **En el archivo `.env` edita:**
> ```ini
> SECRET_KEY=una-clave-secreta-larga-y-aleatoria-para-produccion
> DEBUG=False
> ALLOWED_HOSTS=localhost,127.0.0.1,<TU_IP_ELASTICA>,<TU_SUBDOMINIO>.duckdns.org
> DB_NAME=fitlife_db
> DB_USER=fitlife_user
> DB_PASSWORD=Inacap.2030
> DB_HOST=localhost
> DB_PORT=5432
> ```
> *(Guarda con `Ctrl + O`, presiona `Enter` y sal con `Ctrl + X`)*.

```bash
# 7. Ejecutar migraciones, recolectar estáticos y cargar datos de prueba
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py poblar_datos

# 8. Prueba rápida de DRF (Opcional)
python manage.py runserver 0.0.0.0:8000
# (Prueba abrir en navegador http://<TU_IP_ELASTICA>:8000 y luego detén con Ctrl + C)
```

---

## ETAPA 5: Configurar Gunicorn (WSGI Server con Systemd)

```bash
# 1. Crear el servicio systemd
sudo nano /etc/systemd/system/gunicorn.service
```

**Pega el siguiente contenido:**

```ini
[Unit]
Description=Gunicorn daemon for FitLife Backend
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/apps/fitlife-backend
EnvironmentFile=/home/ubuntu/apps/fitlife-backend/.env
ExecStart=/home/ubuntu/apps/fitlife-backend/venv/bin/gunicorn --workers 3 --bind unix:/home/ubuntu/apps/fitlife-backend/fitlife.sock core.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Iniciar y habilitar el servicio:**

```bash
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn
```

---

## ETAPA 6: Configurar Permisos del Árbol de Directorios (Solución Inacap)

Para evitar el típico error **502 Bad Gateway / Permission Denied** que detalla la guía de Inacap:

```bash
# Añadir usuarios a grupos cruzados
sudo usermod -aG www-data ubuntu
sudo usermod -aG ubuntu www-data

# Ajustar permisos para que Nginx pueda acceder al socket
sudo chmod 755 /home/ubuntu
sudo chmod 775 /home/ubuntu/apps
sudo chmod 775 /home/ubuntu/apps/fitlife-backend
sudo chown -R ubuntu:www-data /home/ubuntu/apps/fitlife-backend
```

---

## ETAPA 7: Configurar Nginx como Proxy Inverso y Servidor de Estáticos

```bash
# 1. Crear configuración en Nginx
sudo nano /etc/nginx/sites-available/fitlife
```

**Pega el siguiente bloque:**

```nginx
server {
    listen 80;
    server_name _;  # Si usas DuckDNS, coloca: tu-dominio.duckdns.org www.tu-dominio.duckdns.org;

    client_max_body_size 20M;

    # Archivos estáticos
    location /static/ {
        alias /home/ubuntu/apps/fitlife-backend/staticfiles/;
        expires 30d;
    }

    # Proxy hacia el socket de Gunicorn
    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/apps/fitlife-backend/fitlife.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    error_log /var/log/nginx/fitlife_error.log;
    access_log /var/log/nginx/fitlife_access.log;
}
```

**Activar el sitio y reiniciar Nginx:**

```bash
sudo ln -sf /etc/nginx/sites-available/fitlife /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## ETAPA 8 (Opcional pero Recomendada): Certificado SSL Gratuito con Certbot (DuckDNS)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d <TU_SUBDOMINIO>.duckdns.org
```

---

## ETAPA 9: Probar y Validar la Plataforma

Abre tu navegador en:
- `http://<TU_IP_ELASTICA>/` o `https://<TU_SUBDOMINIO>.duckdns.org/`
- **Dashboard de Aforo:** `/`
- **Torniquete QR:** `/simulador-acceso/`
- **Clases Grupales y Lista de Espera:** `/clases/`
- **Planes & Transbank Webpay:** `/planes/`
- **API REST (DRF):** `/api/`
- **Django Admin:** `/admin/` (Login: `admin` / `admin123`)
