#!/bin/bash
# ==============================================================================
# SCRIPT DE ACTUALIZACIÓN AUTOMÁTICA DUCKDNS PARA AWS EC2
# Configura un cronjob para mantener el dominio apuntando a la IP pública de EC2
# ==============================================================================

# Reemplaza estos dos valores con los datos de tu cuenta en https://www.duckdns.org/
DUCKDNS_DOMAIN="${1:-fitlife-gym}"
DUCKDNS_TOKEN="${2:-TU_TOKEN_DUCKDNS_AQUI}"

LOG_FILE="/home/ubuntu/duckdns.log"

echo "[$(date)] Actualizando IP en DuckDNS para dominio: ${DUCKDNS_DOMAIN}.duckdns.org..." >> "$LOG_FILE"

RESPUESTA=$(curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=")

echo "[$(date)] Respuesta de DuckDNS: ${RESPUESTA}" >> "$LOG_FILE"

if [ "$RESPUESTA" = "OK" ]; then
    echo "✔ Dominio ${DUCKDNS_DOMAIN}.duckdns.org actualizado correctamente."
else
    echo "✖ Error actualizando DuckDNS. Verifica tu dominio y token."
fi

