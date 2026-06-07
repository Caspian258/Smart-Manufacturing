#!/usr/bin/env python3
"""
rfid_to_influxdb.py — Agente de trazabilidad RFID
Escucha cima/rfid/scan, guarda ciclos completos en InfluxDB y
publica resumen en cima/rfid/completed.

Uso:
  source /opt/smart-manufacturing/venv/bin/activate
  python3 agentes/rfid_to_influxdb.py

O como daemon en background:
  nohup python3 agentes/rfid_to_influxdb.py >> /tmp/rfid_agent.log 2>&1 &
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt_lib

# ── Config ────────────────────────────────────────────────────────────────────

ENV_PATH = Path("/opt/smart-manufacturing/.env")
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

INFLUX_URL   = os.getenv("INFLUXDB_URL",   "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
INFLUX_ORG   = "smart-manufacturing"
INFLUX_BUCKET = "sensor-data"
TARIFA_KWH_MXN = 2.80

MQTT_BROKER = os.getenv("MQTT_BROKER_LOCAL", "127.0.0.1")
MQTT_PORT   = int(os.getenv("MQTT_PORT_LOCAL", "1883"))
MQTT_USER   = os.getenv("MQTT_APP_USER", "")
MQTT_PASS   = os.getenv("MQTT_APP_PASS", "")

TOPIC_RFID_SCAN      = "cima/rfid/scan"
TOPIC_RFID_COMPLETED = "cima/rfid/completed"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RFID-AGENT] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── InfluxDB write ────────────────────────────────────────────────────────────

def _influx_write(line: str) -> bool:
    try:
        import urllib.request
        url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ms"
        req = urllib.request.Request(
            url, data=line.encode(), method="POST",
            headers={
                "Authorization": f"Token {INFLUX_TOKEN}",
                "Content-Type":  "text/plain; charset=utf-8",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 204
    except Exception as exc:
        log.error("InfluxDB write error: %s", exc)
        return False


def _safe_tag(s: str) -> str:
    return str(s).replace(":", "-").replace(",", "_").replace(" ", "_").replace("=", "_")


def _write_cycle(payload: dict) -> bool:
    uid       = str(payload.get("uid", "unknown"))
    machine   = str(payload.get("machine_id", "unknown"))
    part_id   = str(payload.get("part_id",   "unknown"))
    dur_s     = float(payload.get("duration_s", 0) or 0)
    ewh       = float(payload.get("energy_wh",  0) or 0)
    ts_end    = str(payload.get("ts", datetime.now(timezone.utc).isoformat()))
    cost      = round(ewh / 1000.0 * TARIFA_KWH_MXN, 4)

    # Calcular ts_start
    try:
        ts_end_dt  = datetime.fromisoformat(ts_end.replace("Z", "+00:00"))
        ts_end_ms  = int(ts_end_dt.timestamp() * 1000)
        ts_start_ms = ts_end_ms - int(dur_s * 1000)
        ts_start   = datetime.fromtimestamp(ts_start_ms / 1000, tz=timezone.utc).isoformat()
    except Exception:
        ts_end_ms   = int(time.time() * 1000)
        ts_start_ms = ts_end_ms - int(dur_s * 1000)
        ts_start    = datetime.fromtimestamp(ts_start_ms / 1000, tz=timezone.utc).isoformat()

    # InfluxDB line protocol — tags no llevan espacios ni comas sin escapar
    m_tag   = _safe_tag(machine)
    u_tag   = _safe_tag(uid)
    pid_tag = _safe_tag(part_id)

    line = (
        f"cima_rfid_cycles,machine_id={m_tag},uid={u_tag},part_id={pid_tag}"
        f" duration_s={dur_s:.1f},energy_wh={ewh:.3f},cost_mxn={cost}"
        f",ts_start=\"{ts_start}\",ts_end=\"{ts_end}\""
        f" {ts_end_ms}"
    )

    log.info("Escribiendo InfluxDB: %s", line)
    ok = _influx_write(line)
    if ok:
        log.info("InfluxDB OK — part_id=%s dur=%.0fs ewh=%.3f cost=$%.4f", part_id, dur_s, ewh, cost)
    else:
        log.error("InfluxDB FALLO para part_id=%s", part_id)
    return ok


# ── MQTT callbacks ────────────────────────────────────────────────────────────

_mqtt_client = None  # referencia global para publish desde callback


def on_connect_v2(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(TOPIC_RFID_SCAN)
        log.info("MQTT conectado — suscrito a %s", TOPIC_RFID_SCAN)
    else:
        log.error("MQTT conexión falló: reason_code=%s", reason_code)


def on_connect_v1(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC_RFID_SCAN)
        log.info("MQTT conectado — suscrito a %s", TOPIC_RFID_SCAN)
    else:
        log.error("MQTT conexión falló: rc=%d", rc)


def on_message(client, userdata, msg):
    global _mqtt_client
    try:
        payload = json.loads(msg.payload.decode())
        event   = payload.get("event", "")
        uid     = payload.get("uid", "?")
        log.info("Recibido: event=%s uid=%s part=%s", event, uid, payload.get("part_id", "?"))

        if event != "stop":
            return  # solo procesar ciclos completos

        ok = _write_cycle(payload)

        if ok:
            completed = {
                "part_id":    payload.get("part_id", "?"),
                "uid":        uid,
                "machine_id": payload.get("machine_id", "?"),
                "duration_s": float(payload.get("duration_s", 0) or 0),
                "energy_wh":  float(payload.get("energy_wh", 0) or 0),
                "cost_mxn":   round(float(payload.get("energy_wh", 0) or 0) / 1000.0 * TARIFA_KWH_MXN, 4),
                "ts_end":     payload.get("ts", ""),
            }
            client.publish(TOPIC_RFID_COMPLETED, json.dumps(completed))
            log.info("Publicado en %s", TOPIC_RFID_COMPLETED)

    except Exception as exc:
        log.error("on_message error: %s", exc)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global _mqtt_client
    log.info("=== Agente RFID → InfluxDB arrancando ===")
    log.info("Broker: %s:%d  |  InfluxDB: %s", MQTT_BROKER, MQTT_PORT, INFLUX_URL)
    if not INFLUX_TOKEN:
        log.error("INFLUXDB_TOKEN no configurado — revisar .env")
        sys.exit(1)

    try:
        client = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect_v2
    except AttributeError:
        client = mqtt_lib.Client()
        client.on_connect = on_connect_v1

    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_message = on_message
    _mqtt_client = client

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    log.info("Escuchando ciclos RFID... (Ctrl+C para salir)")
    client.loop_forever()


if __name__ == "__main__":
    main()
