#!/bin/bash
# =============================================================================
# setup_rpi5.sh — Script Maestro de Configuración
# Smart Manufacturing: CIMA + Celda 3105
# Ejecutar en Raspberry Pi 5 con Raspberry Pi OS (64-bit)
# Uso: bash setup_rpi5.sh
# =============================================================================

set -e  # Detener si hay error

# ─── Colores para output ───────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()     { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
section() { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }

# ─── Verificaciones previas ────────────────────────────────────────────────
section "Verificando sistema"

[[ $(id -u) -ne 0 ]] && error "Ejecutar con sudo: sudo bash setup_rpi5.sh"
[[ $(uname -m) != "aarch64" ]] && warn "No es ARM64 — continuar con precaución"

log "Sistema: $(uname -a)"
log "Memoria: $(free -h | awk '/^Mem:/{print $2}')"
log "Disco libre: $(df -h / | awk 'NR==2{print $4}')"

# ─── Variables de configuración ────────────────────────────────────────────
REPO_URL="${REPO_URL:-https://github.com/TU_USUARIO/TU_REPO.git}"
PROJECT_DIR="/opt/smart-manufacturing"
DATA_DIR="/var/smart-manufacturing"
MQTT_PORT=1883
INFLUX_PORT=8086
NODERED_PORT=1880
N8N_PORT=5678
GRAFANA_PORT=3001

# ─── 1. Actualizar sistema ─────────────────────────────────────────────────
section "1. Actualizando sistema"
apt-get update -qq && apt-get upgrade -y -qq
log "Sistema actualizado"

# ─── 2. Instalar dependencias base ────────────────────────────────────────
section "2. Instalando dependencias base"
apt-get install -y -qq \
    git curl wget vim htop \
    python3 python3-pip python3-venv \
    mosquitto mosquitto-clients \
    sqlite3 \
    jq \
    docker.io docker-compose \
    avahi-daemon \
    2>/dev/null

systemctl enable docker
systemctl start docker
log "Dependencias base instaladas"

# ─── 3. Configurar MQTT Broker (Mosquitto) ────────────────────────────────
section "3. Configurando MQTT Broker"

cat > /etc/mosquitto/conf.d/smart-mfg.conf << 'EOF'
# Smart Manufacturing MQTT Config
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd

# WebSocket para dashboard
listener 9001
protocol websockets

# Logging
log_dest file /var/log/mosquitto/mosquitto.log
log_type all
EOF

# Crear usuario MQTT (cambiar password en producción)
touch /etc/mosquitto/passwd
mosquitto_passwd -b /etc/mosquitto/passwd smfg_user "SmartMfg2024!"
mosquitto_passwd -b /etc/mosquitto/passwd esp32_cima "Esp32Cima!"
mosquitto_passwd -b /etc/mosquitto/passwd nodered_agent "NodeRed!"

systemctl enable mosquitto
systemctl restart mosquitto
log "MQTT Broker configurado en puerto $MQTT_PORT"

# ─── 4. Instalar Node.js + Node-RED ───────────────────────────────────────
section "4. Instalando Node.js + Node-RED"

curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

npm install -g --unsafe-perm node-red

# Instalar paletas útiles para manufactura
npm install -g \
    node-red-dashboard \
    node-red-contrib-mqtt-broker \
    node-red-contrib-influxdb \
    node-red-node-sqlite

# Configurar Node-RED como servicio
cat > /etc/systemd/system/nodered.service << EOF
[Unit]
Description=Node-RED Smart Manufacturing Dashboard
After=network.target mosquitto.service

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/node-red --max-old-space-size=512
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl enable nodered
systemctl start nodered
log "Node-RED instalado en puerto $NODERED_PORT"

# ─── 5. Instalar InfluxDB ─────────────────────────────────────────────────
section "5. Instalando InfluxDB (Time-Series DB)"

wget -q https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.1-arm64.deb
dpkg -i influxdb2-2.7.1-arm64.deb
rm influxdb2-2.7.1-arm64.deb

systemctl enable influxdb
systemctl start influxdb
sleep 3

# Setup inicial de InfluxDB
influx setup \
    --username admin \
    --password "SmartMfg2024!" \
    --org smart-manufacturing \
    --bucket sensor-data \
    --retention 30d \
    --force 2>/dev/null || warn "InfluxDB ya configurado"

log "InfluxDB instalado en puerto $INFLUX_PORT"

# ─── 6. Instalar n8n ──────────────────────────────────────────────────────
section "6. Instalando n8n (Middleware de flujos)"

npm install -g n8n

mkdir -p /home/pi/.n8n

cat > /etc/systemd/system/n8n.service << EOF
[Unit]
Description=n8n Smart Manufacturing Workflow Engine
After=network.target influxdb.service

[Service]
Type=simple
User=pi
Environment=N8N_PORT=$N8N_PORT
Environment=N8N_HOST=0.0.0.0
Environment=WEBHOOK_URL=http://localhost:$N8N_PORT/
Environment=N8N_BASIC_AUTH_ACTIVE=true
Environment=N8N_BASIC_AUTH_USER=admin
Environment=N8N_BASIC_AUTH_PASSWORD=SmartMfg2024!
ExecStart=/usr/bin/n8n start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl enable n8n
systemctl start n8n
log "n8n instalado en puerto $N8N_PORT"

# ─── 7. Instalar Grafana ──────────────────────────────────────────────────
section "7. Instalando Grafana (Visualización KPIs)"

wget -q https://dl.grafana.com/oss/release/grafana_10.2.0_arm64.deb
dpkg -i grafana_10.2.0_arm64.deb
# Configurar puerto 3001
sed -i 's/^;http_port = 3000/http_port = 3001/' /etc/grafana/grafana.ini
sed -i 's/^http_port = 3000/http_port = 3001/' /etc/grafana/grafana.ini
rm grafana_10.2.0_arm64.deb

systemctl enable grafana-server
systemctl start grafana-server
log "Grafana instalado en puerto $GRAFANA_PORT"

# ─── 8. Instalar Python deps (IA, sensores) ───────────────────────────────
section "8. Instalando Python para IA y sensores"

pip3 install --break-system-packages \
    paho-mqtt \
    influxdb-client \
    numpy \
    tflite-runtime \
    RPi.GPIO \
    spidev \
    mfrc522 \
    schedule \
    python-dotenv \
    fastapi \
    uvicorn

log "Python libs instaladas"

# ─── 9. Crear estructura de directorios del proyecto ─────────────────────
section "9. Creando estructura del proyecto"

mkdir -p $PROJECT_DIR
mkdir -p $DATA_DIR/{logs,data,models,backups}

# Crear usuario de servicio
useradd -r -s /bin/false smfg 2>/dev/null || true
chown -R smfg:smfg $DATA_DIR

log "Directorios creados en $PROJECT_DIR"

# ─── 10. Crear agente de bitácora ─────────────────────────────────────────
section "10. Configurando agente de bitácora automática"

cat > $PROJECT_DIR/bitacora_agent.sh << 'AGENT'
#!/bin/bash
# Agente que registra estado del sistema cada hora
LOGFILE="/var/smart-manufacturing/logs/bitacora_$(date +%Y%m).log"

{
echo "═══════════════════════════════════════"
echo "TIMESTAMP: $(date '+%Y-%m-%d %H:%M:%S')"
echo "UPTIME: $(uptime -p)"
echo ""
echo "SERVICIOS:"
for svc in mosquitto nodered n8n influxdb grafana-server; do
    STATUS=$(systemctl is-active $svc 2>/dev/null || echo "no instalado")
    echo "  $svc: $STATUS"
done
echo ""
echo "MQTT (últimos mensajes):"
timeout 3 mosquitto_sub -h localhost -u smfg_user -P "SmartMfg2024!" -t "#" -C 5 2>/dev/null || echo "  (sin mensajes)"
echo ""
echo "DISCO: $(df -h / | awk 'NR==2{print $3"/"$2" ("$5" usado)"}')"
echo "RAM:   $(free -h | awk '/^Mem:/{print $3"/"$2}')"
echo "CPU:   $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
} >> $LOGFILE

echo "Bitácora actualizada: $LOGFILE"
AGENT

chmod +x $PROJECT_DIR/bitacora_agent.sh

# Cron cada hora
(crontab -l 2>/dev/null; echo "0 * * * * $PROJECT_DIR/bitacora_agent.sh") | crontab -
log "Agente de bitácora configurado (cada hora)"

# ─── 11. Crear .env template ──────────────────────────────────────────────
section "11. Creando archivo de configuración"

cat > $PROJECT_DIR/.env.template << 'EOF'
# ── Smart Manufacturing — Variables de entorno ──
# Copiar a .env y completar con tus valores reales

# MQTT
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USER=smfg_user
MQTT_PASSWORD=CAMBIAR_ESTO

# InfluxDB
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=OBTENER_CON_influx_auth_list
INFLUX_ORG=smart-manufacturing
INFLUX_BUCKET=sensor-data

# GitHub (para auto-push)
GITHUB_TOKEN=OBTENER_DE_GITHUB_SETTINGS
GITHUB_REPO=TU_USUARIO/TU_REPO

# ESP32 topics MQTT
TOPIC_CIMA_ENERGY=cima/machines/+/energy
TOPIC_CIMA_CYCLE=cima/machines/+/cycle
TOPIC_CELDA_VISION=celda3105/vision/result
TOPIC_CELDA_RFID=celda3105/rfid/scan
TOPIC_CELDA_COBOT=celda3105/cobot/status
EOF

cp $PROJECT_DIR/.env.template $PROJECT_DIR/.env
log ".env creado — IMPORTANTE: editar con tus valores reales"

# ─── 12. Script de auto-push a GitHub ────────────────────────────────────
section "12. Configurando auto-push a GitHub"

cat > $PROJECT_DIR/github_sync.sh << 'SYNC'
#!/bin/bash
# Auto-push a GitHub — ejecutar después de cambios importantes
source /opt/smart-manufacturing/.env

REPO_DIR="/opt/smart-manufacturing"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

cd $REPO_DIR 2>/dev/null || exit 1

# Copiar bitácora más reciente al repo
cp /var/smart-manufacturing/logs/bitacora_$(date +%Y%m).log ./bitacora/ 2>/dev/null

git add -A
git diff --staged --quiet && echo "Sin cambios para subir" && exit 0
git commit -m "auto: sync $TIMESTAMP [RPi5]"
git push origin main

echo "✓ Sincronizado con GitHub: $TIMESTAMP"
SYNC

chmod +x $PROJECT_DIR/github_sync.sh

# Cron diario a medianoche
(crontab -l 2>/dev/null; echo "0 0 * * * $PROJECT_DIR/github_sync.sh >> /var/smart-manufacturing/logs/github_sync.log 2>&1") | crontab -
log "Auto-push a GitHub configurado (diario, medianoche)"

# ─── Resumen final ────────────────────────────────────────────────────────
section "✅ INSTALACIÓN COMPLETA"

RPi_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}Servicios disponibles en http://$RPi_IP${NC}"
echo ""
echo "  📡  MQTT Broker    → $RPi_IP:$MQTT_PORT"
echo "  🔴  Node-RED       → http://$RPi_IP:$NODERED_PORT"
echo "  📊  Grafana  → http://$RPi_IP:$GRAFANA_PORT  (admin/SmartMfg2024!) ⚠️ puerto 3001"
echo "  🔄  n8n            → http://$RPi_IP:$N8N_PORT      (admin/SmartMfg2024!)"
echo "  🗄️  InfluxDB       → http://$RPi_IP:$INFLUX_PORT"
echo ""
echo -e "${YELLOW}PRÓXIMOS PASOS:${NC}"
echo "  1. Editar /opt/smart-manufacturing/.env con tus tokens reales"
echo "  2. Flashear firmware al ESP32-S3 (ver /firmware/esp32-s3/)"
echo "  3. Importar flujos n8n desde /flows/n8n/"
echo "  4. Importar dashboard Node-RED desde /flows/nodered/"
echo "  5. Configurar GitHub remote: git remote set-url origin TU_REPO"
echo ""
echo -e "${YELLOW}CAMBIAR PASSWORDS:${NC} Los defaults son solo para desarrollo."
echo ""
log "Setup completo — $(date)"
