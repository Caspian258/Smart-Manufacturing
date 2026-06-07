"""
UNIX&Co. — Smart Manufacturing CIMA + Celda 3105
Entry point — PyWebView + HTML/CSS/JS interface.

Ejecutar desde raíz del proyecto: python3 app/main.py
"""

import json
import os
import sys
import time
from pathlib import Path

# Deben ir ANTES de importar webview — GTK y WebKit2GTK los leen al inicializar.
# Corrigen corrupción visual en RPi5 VideoCore VII con WebKit2GTK 2.52+:
#   - DMABUF renderer causa artefactos gráficos en VideoCore cuando la GPU
#     no tiene soporte completo de DMA-BUF (DRM prime) en kernel 6.x
#   - COMPOSITING_MODE puede dejar capas sin sincronizar en pantallas pequeñas
#   - GDK_SCALE fuerza factor 1:1 y evita que GTK aplique auto-DPI (1.333×)
os.environ.setdefault('WEBKIT_DISABLE_DMABUF_RENDERER', '1')
os.environ.setdefault('WEBKIT_DISABLE_COMPOSITING_MODE', '1')
os.environ.setdefault('GDK_SCALE', '1')
os.environ.setdefault('GDK_DPI_SCALE', '1')

sys.path.insert(0, str(Path(__file__).parent))

import logging
import threading

import paho.mqtt.client as mqtt_lib
import webview

from config import (
    MACHINE_ID_PLANTA1, SCREEN_WIDTH, SCREEN_HEIGHT,
    MQTT_BROKER, MQTT_PORT_LOCAL, MQTT_APP_USER, MQTT_APP_PASS,
)
from auth import authenticate, bootstrap_users, add_user as _auth_add_user
from db import (
    query_latest_power,
    query_energy_24h,
    query_energy_realtime,
    query_rfid_history,
    query_rfid_cycles,
    query_rfid_pieza_detalle,
    query_turno_promedios,
    query_energy_cost_admin,
    query_celda3105_latest,
    query_celda3105_kpis,
    query_celda3105_operaciones,
    get_all_users,
    delete_user as _db_delete_user,
    get_audit_logs as _db_get_audit_logs,
)
from health_check import HealthChecker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


class Api:
    """API Python expuesta al JS vía window.pywebview.api.*"""

    def __init__(self):
        self._session: dict | None = None
        self._hc = HealthChecker()
        self._hc.start()
        self._active_cycle: dict | None = None
        self._rfid_mqtt: mqtt_lib.Client | None = None
        self._connect_rfid_mqtt()
        self._celda_latest: dict = {}
        self._celda_ts: float | None = None
        self._celda_signals: dict = {}
        self._celda_signals_ts: float | None = None
        self._celda_kpis: dict = {}
        self._celda_kpis_ts: float | None = None
        self._celda_mqtt: mqtt_lib.Client | None = None
        self._connect_celda_mqtt()
        self._rfid_sim_active: bool = False
        self._rfid_sim_part: str | None = None
        self._rfid_sim_start: float = 0.0

    def _connect_rfid_mqtt(self):
        try:
            try:
                client = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2)
                client.on_connect = lambda c, u, f, rc, p: c.subscribe("cima/rfid/scan") if rc == 0 else None
            except AttributeError:
                client = mqtt_lib.Client()
                client.on_connect = lambda c, u, f, rc: c.subscribe("cima/rfid/scan") if rc == 0 else None
            client.username_pw_set(MQTT_APP_USER, MQTT_APP_PASS)
            client.on_message = self._on_rfid_message
            client.connect_async(MQTT_BROKER, MQTT_PORT_LOCAL, 60)
            client.loop_start()
            self._rfid_mqtt = client
        except Exception as exc:
            log.warning("Api RFID MQTT: %s", exc)

    def _on_rfid_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            event   = payload.get("event", "")
            if event == "start":
                self._active_cycle = {**payload, "_epoch": time.time()}
            elif event == "stop":
                self._active_cycle = None
        except Exception:
            pass

    def _connect_celda_mqtt(self):
        try:
            def _on_connect_v2(c, u, f, rc, p):
                if rc == 0:
                    c.message_callback_add("celda3105/plc/fast", self._on_celda_fast)
                    c.message_callback_add("celda3105/plc/kpis", self._on_celda_kpis)
                    c.subscribe([("celda3105/plc/fast", 1), ("celda3105/plc/kpis", 1), ("celda3105/plc", 1)])

            def _on_connect_v1(c, u, f, rc):
                if rc == 0:
                    c.message_callback_add("celda3105/plc/fast", self._on_celda_fast)
                    c.message_callback_add("celda3105/plc/kpis", self._on_celda_kpis)
                    c.subscribe([("celda3105/plc/fast", 1), ("celda3105/plc/kpis", 1), ("celda3105/plc", 1)])

            try:
                client = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2)
                client.on_connect = _on_connect_v2
            except AttributeError:
                client = mqtt_lib.Client()
                client.on_connect = _on_connect_v1
            client.username_pw_set(MQTT_APP_USER, MQTT_APP_PASS)
            client.on_message = self._on_celda_message
            client.connect_async(MQTT_BROKER, MQTT_PORT_LOCAL, 60)
            client.loop_start()
            self._celda_mqtt = client
        except Exception as exc:
            log.warning("Api Celda MQTT: %s", exc)

    def _on_celda_message(self, client, userdata, msg):
        try:
            self._celda_latest = json.loads(msg.payload.decode())
            self._celda_ts = time.time()
        except Exception:
            pass

    def _on_celda_fast(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            self._celda_signals = data
            self._celda_signals_ts = time.time()
            self._celda_latest = data   # compat con get_celda3105_status()
            self._celda_ts = time.time()
        except Exception:
            pass

    def _on_celda_kpis(self, client, userdata, msg):
        try:
            self._celda_kpis = json.loads(msg.payload.decode())
            self._celda_kpis_ts = time.time()
        except Exception:
            pass

    # ── Auth ──────────────────────────────────────────────────────────────

    def login(self, username: str, pin: str) -> dict:
        result = authenticate(str(username).strip(), str(pin).strip())
        if result.ok:
            self._session = {"username": result.username, "rol": result.rol}
            log.info("Login: %s (%s)", result.username, result.rol)
            return {"success": True, "role": result.rol, "username": result.username}
        return {"success": False, "message": result.message}

    def logout(self) -> dict:
        if self._session:
            log.info("Logout: %s", self._session["username"])
        self._session = None
        return {"success": True}

    def get_session(self) -> dict:
        if self._session:
            return {"logged_in": True, **self._session}
        return {"logged_in": False}

    # ── Energy ────────────────────────────────────────────────────────────

    def get_current_power(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        if self._session.get("rol") not in ("planta1", "admin"):
            return {"error": "forbidden"}
        _ZERO = {"power_w": 0.0, "irms_a": 0.0, "energy_kwh": 0.0}
        data = query_energy_24h(machine_id=MACHINE_ID_PLANTA1)
        if not data:
            return _ZERO
        latest     = data[-1]
        # Si el último dato de InfluxDB tiene más de 10 segundos, el ESP32
        # está desconectado o apagado — devolver ceros en lugar de dato obsoleto.
        try:
            from datetime import datetime, timezone
            ts_str = latest.get("time", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_s = (datetime.now(timezone.utc) - ts).total_seconds()
                if age_s > 10:
                    return _ZERO
        except Exception:
            pass
        energy_kwh = round(sum(d["energy_kwh"] for d in data), 3)
        return {
            "power_w":    latest["power_w"],
            "irms_a":     latest["irms_a"],
            "energy_kwh": energy_kwh,
        }

    def get_energy_realtime(self) -> list:
        if not self._session:
            return []
        rol = self._session.get("rol", "")
        if rol not in ("planta1", "admin"):
            return []
        data = query_energy_realtime(n=60, machine_id=MACHINE_ID_PLANTA1)
        return [
            {
                "time":       d["time"],
                "power_w":    d["power_w"],
                "irms_a":     d["irms_a"],
                "energy_kwh": d["energy_kwh"],
            }
            for d in data
        ]

    def get_cost_data(self) -> dict:
        if not self._session or self._session.get("rol") != "admin":
            return {"error": "forbidden"}
        return query_energy_cost_admin()

    # ── System status ──────────────────────────────────────────────────────

    def get_system_status(self) -> dict:
        return self._hc.get_statuses()

    # ── RFID ──────────────────────────────────────────────────────────────

    def get_rfid_history(self, n: int = 10) -> list:
        if not self._session:
            return []
        if self._session.get("rol") not in ("planta1", "admin"):
            return []
        return query_rfid_history(n=min(int(n), 50))

    # ── Energy 24h series ─────────────────────────────────────────────────

    def get_energy_24h(self) -> list:
        """Serie completa de 24h para la gráfica de Energía (48 puntos, 30min)."""
        if not self._session:
            return []
        if self._session.get("rol") not in ("planta1", "admin"):
            return []
        data = query_energy_24h(machine_id=MACHINE_ID_PLANTA1)
        return [
            {"time": d["time"], "power_w": d["power_w"], "energy_kwh": d["energy_kwh"]}
            for d in data
        ]

    # ── Users (admin) ─────────────────────────────────────────────────────

    def get_users(self) -> list:
        if not self._session or self._session.get("rol") != "admin":
            return []
        return get_all_users()

    def add_user(self, username: str, pin: str, rol: str) -> dict:
        if not self._session or self._session.get("rol") != "admin":
            return {"success": False, "message": "Sin permisos"}
        ok, msg = _auth_add_user(
            str(username).strip(), str(pin).strip(), str(rol).strip(), 0
        )
        return {"success": ok, "message": msg}

    def delete_user(self, username: str) -> dict:
        if not self._session or self._session.get("rol") != "admin":
            return {"success": False, "message": "Sin permisos"}
        if str(username) in ("admin", self._session.get("username", "")):
            return {"success": False, "message": "No se puede eliminar esta cuenta"}
        _db_delete_user(str(username))
        return {"success": True, "message": f"Usuario '{username}' eliminado"}

    # ── Audit log (admin) ─────────────────────────────────────────────────

    def get_audit_logs(self) -> list:
        if not self._session or self._session.get("rol") != "admin":
            return []
        return _db_get_audit_logs(limit=500)

    # ── Config ────────────────────────────────────────────────────────────

    def get_config(self) -> dict:
        return {}

    # ── RFID Trazabilidad ─────────────────────────────────────────────────

    def get_active_cycle(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        if self._session.get("rol") not in ("planta1", "admin"):
            return {"error": "forbidden"}
        if self._active_cycle is None:
            return {"active": False}
        elapsed = int(time.time() - self._active_cycle.get("_epoch", time.time()))
        return {
            "active":     True,
            "part_id":    self._active_cycle.get("part_id", ""),
            "uid":        self._active_cycle.get("uid", ""),
            "machine_id": self._active_cycle.get("machine_id", ""),
            "ts":         self._active_cycle.get("ts", ""),
            "elapsed_s":  elapsed,
        }

    def get_rfid_cycles(self, limit: int = 50, filtro: str = "today") -> list:
        if not self._session:
            return []
        if self._session.get("rol") not in ("planta1", "admin"):
            return []
        from datetime import datetime as _dt, timedelta as _td
        data = query_rfid_cycles(limit=min(int(limit) * 4, 400))
        now = _dt.now()
        if filtro == "today":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif filtro == "week":
            cutoff = (now - _td(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0)
        else:
            cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        filtered = []
        for row in data:
            try:
                ts = row.get("ts_end", "")
                naive = _dt.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                if naive >= cutoff:
                    filtered.append(row)
            except Exception:
                pass
        result = filtered[:int(limit)]
        if self._session.get("rol") != "admin":
            for row in result:
                row.pop("cost_mxn", None)
        return result

    def get_rfid_pieza_detalle(self, part_id: str) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        if self._session.get("rol") not in ("planta1", "admin"):
            return {"error": "forbidden"}
        detalle   = query_rfid_pieza_detalle(str(part_id))
        promedios = query_turno_promedios()
        if detalle and self._session.get("rol") != "admin":
            detalle.pop("cost_mxn", None)
        return {"detalle": detalle, "promedios": promedios}

    def export_rfid_csv(self, filtro: str = "today") -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        if self._session.get("rol") not in ("planta1", "admin"):
            return {"error": "forbidden"}
        data = self.get_rfid_cycles(limit=500, filtro=filtro)
        try:
            import csv, io, datetime as _dt, subprocess
            buf = io.StringIO()
            w   = csv.writer(buf)
            show_cost = self._session.get("rol") == "admin"
            headers = ["Part ID", "Inicio", "Fin", "Duración (s)", "Energía (Wh)", "Máquina"]
            if show_cost:
                headers.append("Costo (MXN)")
            w.writerow(headers)
            for r in data:
                row = [r.get("part_id",""), r.get("ts_start",""), r.get("ts_end",""),
                       r.get("duration_s",""), r.get("energy_wh",""), r.get("machine_id","")]
                if show_cost:
                    row.append(r.get("cost_mxn",""))
                w.writerow(row)
            fname = f"trazabilidad_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            path  = f"/tmp/{fname}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(buf.getvalue())
            try:
                subprocess.Popen(["xdg-open", path])
            except Exception:
                pass
            return {"ok": True, "path": path}
        except Exception as exc:
            log.error("export_rfid_csv: %s", exc)
            return {"error": str(exc)}

    def get_celda3105_status(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        connected = bool(self._celda_ts and time.time() - self._celda_ts < 15)
        ops = query_celda3105_operaciones(limit=10)
        return {
            "connected": connected,
            "latest": self._celda_latest,
            "kpis": self._celda_kpis.get("kpis", {}) if self._celda_kpis else self._celda_latest.get("kpis", {}),
            "operaciones": ops,
        }

    def get_celda_signals(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        connected = bool(self._celda_signals_ts and time.time() - self._celda_signals_ts < 5)
        return {"connected": connected, "signals": self._celda_signals}

    def get_celda_kpis(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        connected = bool(self._celda_kpis_ts and time.time() - self._celda_kpis_ts < 30)
        kpis = self._celda_kpis.get("kpis", {}) if self._celda_kpis else {}
        ops = query_celda3105_operaciones(limit=10)
        return {"connected": connected, "kpis": kpis, "operaciones": ops}

    def get_quality_gate(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        connected = bool(self._celda_ts and time.time() - self._celda_ts < 15)
        if not connected:
            return {"connected": False}
        kpis   = self._celda_latest.get("kpis", {})
        cognex = self._celda_latest.get("cognex", {})
        return {
            "connected": True,
            "inspeccionadas":   kpis.get("piezas_procesadas", 0),
            "aprobadas":        kpis.get("piezas_aprobadas",  0),
            "rechazadas":       kpis.get("piezas_rechazadas", 0),
            "oee":              kpis.get("oee", 0),
            "cognex_activa":    cognex.get("foto",      False),
            "ultima_aprobada":  cognex.get("aprobada",  False),
            "ultima_rechazada": cognex.get("rechazada", False),
        }

    def get_rfid_stats(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        if self._session.get("rol") not in ("planta1", "admin"):
            return {"error": "forbidden"}
        data = query_rfid_cycles(limit=100)
        if not data:
            return {"total": 0, "avg_duration_s": 0.0, "avg_energy_wh": 0.0}
        n      = len(data)
        avg_s  = sum(d["duration_s"] for d in data) / n
        avg_e  = sum(d["energy_wh"]  for d in data) / n
        result = {"total": n, "avg_duration_s": round(avg_s, 1), "avg_energy_wh": round(avg_e, 2)}
        if self._session.get("rol") == "admin":
            result["total_cost_mxn"] = round(sum(d["cost_mxn"] for d in data), 2)
        return result

    def simulate_rfid_scan(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        sim_uid = "SIM:00:00:01"
        if not self._rfid_sim_active:
            part_id = f"PIEZA-SIM-{int(time.time())}"
            self._rfid_sim_active = True
            self._rfid_sim_part = part_id
            self._rfid_sim_start = time.time()
            payload = {"uid": sim_uid, "event": "start", "part_id": part_id,
                       "machine_id": "torno", "ts": ts}
        else:
            part_id = self._rfid_sim_part
            duration = round(time.time() - self._rfid_sim_start, 1)
            self._rfid_sim_active = False
            self._rfid_sim_part = None
            payload = {"uid": sim_uid, "event": "stop", "part_id": part_id,
                       "machine_id": "torno", "duration_s": duration,
                       "energy_wh": round(duration * 0.3 / 3600, 4), "ts": ts}
        try:
            pub = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2,
                                  client_id="rfid-sim-key")
        except AttributeError:
            pub = mqtt_lib.Client(client_id="rfid-sim-key")
        pub.username_pw_set(MQTT_APP_USER, MQTT_APP_PASS)
        pub.connect("127.0.0.1", MQTT_PORT_LOCAL)
        pub.publish("cima/rfid/scan", json.dumps(payload))
        pub.disconnect()
        log.info("RFID SIM: %s part_id=%s", payload["event"], part_id)
        return payload

    # ── Export PDF ────────────────────────────────────────────────────────

    def export_rfid_pdf(self) -> dict:
        if not self._session:
            return {"error": "not_authenticated"}
        if self._session.get("rol") not in ("planta1", "admin"):
            return {"error": "forbidden"}
        show_cost = self._session.get("rol") == "admin"
        data = query_rfid_cycles(limit=100)
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
            )
            from reportlab.lib.styles import getSampleStyleSheet
            import datetime as _dt, subprocess
            fname = f"trazabilidad_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            path  = f"/tmp/{fname}"
            doc   = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()
            story  = []
            story.append(Paragraph(
                "Reporte de Trazabilidad RFID — Smart Manufacturing CIMA",
                styles["Title"],
            ))
            story.append(Paragraph(
                f"Generado: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                styles["Normal"],
            ))
            story.append(Spacer(1, 12))
            headers = ["Part ID", "Inicio", "Fin", "Duración", "Energía (Wh)"]
            if show_cost:
                headers.append("Costo (MXN)")
            rows = [headers]
            if data:
                for d in data:
                    dur_s = int(d.get("duration_s", 0))
                    mm, ss = divmod(dur_s, 60)
                    row = [
                        str(d.get("part_id", "?")),
                        str(d.get("ts_start", "?"))[:19].replace("T", " "),
                        str(d.get("ts_end",   "?"))[:19].replace("T", " "),
                        f"{mm:02d}:{ss:02d}",
                        f"{d.get('energy_wh', 0):.2f}",
                    ]
                    if show_cost:
                        row.append(f"${d.get('cost_mxn', 0):.4f}")
                    rows.append(row)
            else:
                rows.append(["Sin piezas registradas"] + ["—"] * (len(headers) - 1))
            t = Table(rows, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#0F6E56")),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTSIZE",      (0, 0), (-1, 0), 9),
                ("FONTSIZE",      (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#f0f0f0")]),
                ("GRID",          (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))
            n     = len(data)
            avg_s = sum(d.get("duration_s", 0) for d in data) / n if n else 0
            avg_e = sum(d.get("energy_wh",  0) for d in data) / n if n else 0
            mm2, ss2 = divmod(int(avg_s), 60)
            story.append(Paragraph(
                f"Total piezas: {n}  |  Duración promedio: {mm2:02d}:{ss2:02d}"
                f"  |  Energía promedio: {avg_e:.2f} Wh",
                styles["Normal"],
            ))
            if show_cost:
                total_cost = sum(d.get("cost_mxn", 0) for d in data)
                story.append(Paragraph(f"Costo total: ${total_cost:.4f} MXN", styles["Normal"]))
            doc.build(story)
            try:
                subprocess.Popen(["xdg-open", path])
            except Exception:
                pass
            return {"ok": True, "path": path}
        except Exception as exc:
            log.error("export_rfid_pdf: %s", exc)
            return {"error": str(exc)}

    # ── Cleanup ───────────────────────────────────────────────────────────

    def stop(self) -> None:
        self._hc.stop()
        if self._rfid_mqtt:
            try:
                self._rfid_mqtt.loop_stop()
                self._rfid_mqtt.disconnect()
            except Exception:
                pass


def _detect_screen() -> tuple[int, int]:
    """Detecta resolución real con tkinter sin mostrar ventana."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        log.info("Resolución detectada: %dx%d", w, h)
        return w, h
    except Exception:
        log.warning("No se pudo detectar resolución, usando fallback %dx%d", SCREEN_WIDTH, SCREEN_HEIGHT)
        return SCREEN_WIDTH, SCREEN_HEIGHT


def main():
    bootstrap_users()
    api = Api()

    sw, sh = _detect_screen()
    template_url = (Path(__file__).parent / "templates" / "index.html").as_uri()

    window = webview.create_window(
        title="UNIX&Co. — Smart Manufacturing",
        url=template_url,
        js_api=api,
        width=sw,
        height=sh,
        x=0,
        y=0,
        min_size=(800, 400),
        resizable=True,
        background_color="#F4F4F2",
    )

    window.events.closed += lambda: api.stop()
    webview.start(debug=False, http_server=True)


if __name__ == "__main__":
    main()
