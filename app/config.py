"""Configuración central — Smart Manufacturing CIMA + Celda 3105."""

RPi_IP      = "127.0.0.1"  # Red Celda 3105 — actualizar al cambiar de red
MQTT_BROKER = RPi_IP           # Broker corre en el mismo RPi5

SERVICES = {
    "mosquitto": {"port": 1883, "type": "tcp",  "label": "MQTT"},
    "influxdb":  {"port": 8086, "type": "http", "path": "/health",     "label": "InfluxDB"},
    "nodered":   {"port": 1880, "type": "http", "path": "/",           "label": "Node-RED"},
    "n8n":       {"port": 5678, "type": "http", "path": "/",           "label": "n8n"},
    "grafana":   {"port": 3001, "type": "http", "path": "/api/health", "label": "Grafana"},
}

FINGERPRINT_ENABLED = False  # False = solo PIN; True = 2FA huella + PIN (requiere JM-101B conectado)

# MQTT — conexión local desde la app (sin TLS, misma máquina)
MQTT_PORT_LOCAL = 1883
MQTT_APP_USER   = "smfg_user"
MQTT_APP_PASS   = "SmartMfg2024!"

# Sensor AS608 — conexión UART (RPi5: TX→GPIO15, RX→GPIO14, VCC→Pin1 3.3V, GND→Pin6)
# Puertos a intentar en orden: serial0 es el symlink canónico en RPi5
AS608_PORT      = "/dev/ttyAMA10"   # serial0 → ttyAMA10 en esta RPi5
AS608_BAUD      = 57600
AS608_TIMEOUT_S = 5                 # segundos antes de omitir huella por timeout

# SCT-013-000 100A/50mA — salida de corriente, burden externo (Rb=30Ω)
# Irms = (Vrms_medido / Rb) * (Np/Ns) * SCT_CALIBRATION

# Tarifas energéticas
TARIFA_KWH_MXN = 2.80          # MXN / kWh
BASELINE_FACTOR = 1.15          # baseline = promedio_historico * 1.15

# InfluxDB
INFLUXDB_BUCKET     = "sensor-data"
INFLUXDB_ORG        = "smart-manufacturing"
ENERGY_MEASUREMENT  = "cima_energy"
MACHINE_ID_PLANTA1  = "torno"       # machine_id publicado por el ESP32 de CIMA

# Seguridad
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_MINUTES    = 5

# UI
APP_TITLE      = "Smart Manufacturing CIMA"
APP_GEOMETRY   = "1920x1080"
APP_MIN_SIZE   = (1280, 720)
HEALTH_INTERVAL_S = 60          # segundos entre health checks

# Screen resolution — se detecta en runtime; estos valores son el fallback
SCREEN_WIDTH  = 1024   # Actualizar si cambia la pantalla
SCREEN_HEIGHT = 600
UI_SCALE = min(SCREEN_WIDTH / 1920, SCREEN_HEIGHT / 1080)

# Colores — paleta industrial oscura
COLOR_BG        = "#1a1a2e"
COLOR_BG2       = "#16213e"
COLOR_BG3       = "#0f3460"
COLOR_ACCENT    = "#00d4aa"
COLOR_ALERT     = "#ff4757"
COLOR_WARN      = "#ffa502"
COLOR_TEXT      = "#e8e8e8"
COLOR_TEXT_DIM  = "#8a8a9a"
COLOR_GREEN     = "#2ed573"

# Roles válidos
ROLES = ("admin", "planta1", "planta2")

# PLC S7-1200 — Celda 3105
PLC_IP           = "192.168.1.50"
PLC_PORT         = 102
PLC_RACK         = 0
PLC_SLOT         = 1
MQTT_TOPIC_CELDA = "celda3105/plc"
TURNO_HORAS      = 8

MQTT_TOPIC_RFID_SCAN      = "cima/rfid/scan"
MQTT_TOPIC_RFID_COMPLETED = "cima/rfid/completed"
PDF_OUTPUT_DIR             = "/tmp"
