#!/usr/bin/env bash
# install.sh — Instala dependencias Python para la app Smart Manufacturing
# Uso: bash app/install.sh

set -e

echo "=== Smart Manufacturing CIMA — Instalación de dependencias ==="

# Verificar Python 3.10+
python3 -c "import sys; assert sys.version_info >= (3,10), 'Se requiere Python 3.10+'" || {
    echo "ERROR: Python 3.10+ requerido"
    exit 1
}

pip install \
    customtkinter \
    influxdb-client \
    pyfingerprint \
    bcrypt \
    python-dotenv \
    pillow

echo ""
echo "=== Instalación completada ==="
echo ""
echo "Para iniciar la app:"
echo "  python3 app/main.py"
echo ""
echo "Para cambiar a modo REAL (sensor AS608 conectado):"
echo "  Editar app/config.py → SIMULATION_MODE = False"
echo "  Verificar puerto UART → AS608_PORT = '/dev/ttyS0'"
echo ""
echo "Puerto UART RPi5 GPIO14(RX)/GPIO15(TX) ↔ AS608 TX/RX"
