#!/bin/bash
# ==============================================================================
# SCRIPT DE APROVISIONAMIENTO Y DESPLIEGUE - FITLIFE EN AWS EC2
# Sistema Operativo objetivo: Ubuntu 22.04 / 24.04 LTS
# ==============================================================================

set -e  # Detener script si algún comando falla

echo "=========================================================="
echo "    INICIANDO DESPLIEGUE DE FITLIFE BACKEND EN AWS EC2    "
echo "=========================================================="

# 1. Actualización de paquetes del sistema
echo "[1/7] Actualizando paquetes del sistema..."
sudo apt update && sudo apt upgrade -y

# 2. Instalación de dependencias del sistema y PostgreSQL
echo "[2/7] Instalando Python, Nginx, PostgreSQL y bibliotecas necesarias..."
sudo apt install -y python3-pip python3-venv python3-dev \
    libpq-dev postgresql postgresql-contrib nginx curl git ufw

# 3. Configuración de Base de Datos PostgreSQL local
echo "[3/7] Configurando PostgreSQL..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'fitlife_db'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE fitlife_db;"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = 'fitlife_user'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER fitlife_user WITH PASSWORD 'Inacap.2030';"

sudo -u postgres psql -c "ALTER ROLE fitlife_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE fitlife_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE fitlife_user SET timezone TO 'America/Santiago';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE fitlife_db TO fitlife_user;"

# 4. Configurar Entorno Virtual de Python y Dependencias
echo "[4/7] Configurando entorno virtual e instalando requerimientos..."
cd /home/ubuntu/fitlife-backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Generar archivo .env si no existe
echo "[5/7] Configurando variables de entorno (.env)..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Recuerda editar .env con tu IP pública o dominio de EC2."
fi

# 6. Migraciones, recolección de estáticos y poblado inicial
echo "[6/7] Ejecutando migraciones, collectstatic y seed data..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py poblar_datos

# 7. Configuración de Gunicorn (Systemd) y Nginx
echo "[7/7] Configurando servicios Systemd y Nginx..."
sudo cp deploy/fitlife.service /etc/systemd/system/fitlife.service
sudo systemctl daemon-reload
sudo systemctl start fitlife
sudo systemctl enable fitlife

# Configurar Nginx
sudo cp deploy/nginx_fitlife.conf /etc/nginx/sites-available/fitlife
sudo ln -sf /etc/nginx/sites-available/fitlife /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Firewall básico
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
echo "y" | sudo ufw enable || true

echo "=========================================================="
echo "    ✔ DESPLIEGUE COMPLETADO EXITOSAMENTE EN AWS EC2       "
echo "    Accede vía navegador con la IP pública de tu EC2      "
echo "=========================================================="

