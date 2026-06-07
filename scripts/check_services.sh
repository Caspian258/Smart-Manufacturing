#!/bin/bash
# check_services.sh — Verifica servicios al arranque y alerta via MQTT si alguno falla
# Uso: @reboot en crontab, o manualmente

set -euo pipefail

ENV_FILE="/opt/smart-manufacturing/.env"
LOG_DIR="/var/log/smart-manufacturing"
mkdir -p "$LOG_DIR"

# Cargar .env
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

BROKER="${MQTT_BROKER_LOCAL:-127.0.0.1}"
MQTT_PORT="${MQTT_PORT_LOCAL:-1883}"
MQTT_USER="${MQTT_APP_USER:-}"
MQTT_PASS="${MQTT_APP_PASS:-}"

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ALL_OK=true

echo "[$TS] === Health Check — Smart Manufacturing ==="

# ── Servicios systemd ─────────────────────────────────────────────────────────
SYSTEMD_SVCS=("mosquitto" "influxdb" "nodered" "grafana-server" "rfid-agent")

for svc in "${SYSTEMD_SVCS[@]}"; do
    status=$(systemctl is-active "$svc" 2>/dev/null || echo "unknown")
    if [[ "$status" == "active" ]]; then
        echo "  ✅ $svc: active"
    else
        echo "  ⚠️  $svc: $status"
        ALL_OK=false
        if command -v mosquitto_pub &>/dev/null && [[ -n "$MQTT_USER" ]]; then
            mosquitto_pub -h "$BROKER" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" \
                -t "cima/system/alert" \
                -m "{\"service\":\"$svc\",\"status\":\"$status\",\"ts\":\"$TS\"}" \
                2>/dev/null || true
        fi
    fi
done

# ── Docker / n8n ─────────────────────────────────────────────────────────────
if command -v docker &>/dev/null; then
    n8n_status=$(docker inspect --format '{{.State.Status}}' n8n 2>/dev/null || echo "not-found")
    if [[ "$n8n_status" == "running" ]]; then
        echo "  ✅ n8n (docker): running"
    else
        echo "  ⚠️  n8n (docker): $n8n_status"
        ALL_OK=false
        # Intentar arrancar automáticamente
        docker start n8n 2>/dev/null && echo "  🔄 n8n: restart intentado" || true
        if command -v mosquitto_pub &>/dev/null && [[ -n "$MQTT_USER" ]]; then
            mosquitto_pub -h "$BROKER" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" \
                -t "cima/system/alert" \
                -m "{\"service\":\"n8n\",\"status\":\"$n8n_status\",\"ts\":\"$TS\"}" \
                2>/dev/null || true
        fi
    fi
fi

# ── Resultado global ─────────────────────────────────────────────────────────
if $ALL_OK; then
    echo "[$TS] ✅ Todos los servicios operativos"
    if command -v mosquitto_pub &>/dev/null && [[ -n "$MQTT_USER" ]]; then
        mosquitto_pub -h "$BROKER" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" \
            -t "cima/system/heartbeat" \
            -m "{\"event\":\"startup_ok\",\"ts\":\"$TS\"}" \
            2>/dev/null || true
    fi
else
    echo "[$TS] ⚠️  Algunos servicios con problemas — ver log"
fi
