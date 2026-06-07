#!/usr/bin/env bash
# install.sh — Instala dependencias Python para el Cyberdeck Smart Manufacturing
# Uso: bash app/install.sh

set -e

echo "=== Smart Manufacturing CIMA + Celda 3105 — Instalación de dependencias ==="

# Verificar Python 3.10+
python3 -c "import sys; assert sys.version_info >= (3,10), 'Se requiere Python 3.10+'" || {
    echo "ERROR: Python 3.10+ requerido"
    exit 1
}

pip install --break-system-packages \
    pywebview \
    paho-mqtt \
    influxdb-client \
    bcrypt \
    python-dotenv \
    pillow \
    reportlab

echo ""
echo "=== Instalación completada ==="
echo ""
echo "Para iniciar el Cyberdeck:"
echo "  python3 app/main.py"
echo ""
echo "Servicios requeridos en el RPi5:"
echo "  - Mosquitto (broker MQTT :1883)"
echo "  - InfluxDB  (:8086)"
echo "  - n8n       (:5678)"
echo "  - Node-RED  (:1880)"
echo "  - Grafana   (:3001)"
