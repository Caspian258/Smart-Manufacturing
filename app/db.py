"""Capa de acceso a datos — InfluxDB (métricas) y SQLite (usuarios/audit)."""

import json
import os
import sqlite3
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from config import (
    RPi_IP, INFLUXDB_BUCKET, INFLUXDB_ORG, ENERGY_MEASUREMENT,
    TARIFA_KWH_MXN, BASELINE_FACTOR,
    MQTT_BROKER, MQTT_PORT_LOCAL, MQTT_APP_USER, MQTT_APP_PASS,
    MQTT_TOPIC_CELDA,
)

log = logging.getLogger(__name__)

# Cargar .env: primero producción, luego raíz del proyecto como fallback
_ENV_PATH   = Path("/opt/smart-manufacturing/.env")
_LOCAL_ENV  = Path(__file__).parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
elif _LOCAL_ENV.exists():
    load_dotenv(_LOCAL_ENV)

DB_PATH = Path(__file__).parent / "smart_mfg.db"


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Inicializar esquema SQLite (idempotente)."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            pin_hash    TEXT    NOT NULL,
            rol         TEXT    NOT NULL,
            huella_id   INTEGER NOT NULL DEFAULT 0,
            activo      INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL DEFAULT (datetime('now')),
            username    TEXT    NOT NULL,
            accion      TEXT    NOT NULL,
            exitoso     INTEGER NOT NULL,
            ip          TEXT,
            detalle     TEXT
        );

        CREATE TABLE IF NOT EXISTS failed_attempts (
            username    TEXT PRIMARY KEY,
            count       INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT
        );
    """)
    conn.commit()
    conn.close()


def init_plc_tables() -> None:
    """Crear tablas de PLCs adicionales (idempotente)."""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS plcs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            ip          TEXT    NOT NULL UNIQUE,
            rack        INTEGER DEFAULT 0,
            slot        INTEGER DEFAULT 1,
            descripcion TEXT    DEFAULT '',
            activo      INTEGER DEFAULT 1,
            creado_en   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS plc_variables (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plc_id      INTEGER NOT NULL,
            nombre      TEXT    NOT NULL,
            direccion   TEXT    NOT NULL,
            tipo        TEXT    DEFAULT 'bool',
            descripcion TEXT    DEFAULT '',
            activo      INTEGER DEFAULT 1,
            FOREIGN KEY (plc_id) REFERENCES plcs(id)
        );
    ''')
    conn.commit()
    conn.close()


def get_plcs() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM plcs ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_plc(nombre: str, ip: str, rack: int, slot: int,
            descripcion: str) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO plcs (nombre, ip, rack, slot, descripcion) VALUES (?,?,?,?,?)",
        (nombre, ip, rack, slot, descripcion),
    )
    conn.commit()
    plc_id = cur.lastrowid
    conn.close()
    return plc_id


def remove_plc(plc_id: int) -> None:
    conn = get_db()
    conn.execute("DELETE FROM plc_variables WHERE plc_id = ?", (plc_id,))
    conn.execute("DELETE FROM plcs WHERE id = ?", (plc_id,))
    conn.commit()
    conn.close()


def update_plc(plc_id: int, nombre: str, descripcion: str,
               activo: int) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE plcs SET nombre=?, descripcion=?, activo=? WHERE id=?",
        (nombre, descripcion, int(activo), plc_id),
    )
    conn.commit()
    conn.close()


def get_plc_variables(plc_id: int) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM plc_variables WHERE plc_id = ? AND activo = 1 ORDER BY id",
        (plc_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_plc_variable(plc_id: int, nombre: str, direccion: str,
                     tipo: str, descripcion: str) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO plc_variables (plc_id, nombre, direccion, tipo, descripcion)"
        " VALUES (?,?,?,?,?)",
        (plc_id, nombre, direccion, tipo, descripcion),
    )
    conn.commit()
    var_id = cur.lastrowid
    conn.close()
    return var_id


def remove_plc_variable(variable_id: int) -> None:
    conn = get_db()
    conn.execute("DELETE FROM plc_variables WHERE id = ?", (variable_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Dashboards personalizados
# ---------------------------------------------------------------------------

def init_dashboard_tables() -> None:
    """Crear tablas de Dashboards Builder (idempotente)."""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dashboards (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre        TEXT    NOT NULL,
            descripcion   TEXT    DEFAULT '',
            creado_por    TEXT    DEFAULT '',
            creado_en     TEXT    DEFAULT (datetime('now')),
            modificado_en TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS dashboard_widgets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            dashboard_id  INTEGER NOT NULL,
            tipo          TEXT    NOT NULL,
            titulo        TEXT    DEFAULT '',
            fuente        TEXT    DEFAULT 'static',
            fuente_config TEXT    DEFAULT '{}',
            chart_config  TEXT    DEFAULT '{}',
            pos_x         INTEGER DEFAULT 0,
            pos_y         INTEGER DEFAULT 0,
            ancho         INTEGER DEFAULT 4,
            alto          INTEGER DEFAULT 3,
            FOREIGN KEY (dashboard_id) REFERENCES dashboards(id)
                ON DELETE CASCADE
        );
    ''')
    conn.commit()
    conn.close()


def count_dashboards() -> int:
    conn = get_db()
    n = conn.execute("SELECT COUNT(*) FROM dashboards").fetchone()[0]
    conn.close()
    return n


def get_dashboards() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM dashboards ORDER BY modificado_en DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_dashboard(nombre: str, descripcion: str,
                     creado_por: str = '') -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO dashboards (nombre, descripcion, creado_por) VALUES (?,?,?)",
        (nombre, descripcion, creado_por),
    )
    conn.commit()
    dash_id = cur.lastrowid
    conn.close()
    return dash_id


def update_dashboard(dashboard_id: int, nombre: str, descripcion: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE dashboards SET nombre=?, descripcion=?, modificado_en=datetime('now') WHERE id=?",
        (nombre, descripcion, dashboard_id),
    )
    conn.commit()
    conn.close()


def delete_dashboard(dashboard_id: int) -> None:
    conn = get_db()
    conn.execute("DELETE FROM dashboard_widgets WHERE dashboard_id = ?", (dashboard_id,))
    conn.execute("DELETE FROM dashboards WHERE id = ?", (dashboard_id,))
    conn.commit()
    conn.close()


def get_dashboard(dashboard_id: int) -> dict | None:
    conn = get_db()
    dash = conn.execute(
        "SELECT * FROM dashboards WHERE id = ?", (dashboard_id,)
    ).fetchone()
    if not dash:
        conn.close()
        return None
    widgets = conn.execute(
        "SELECT * FROM dashboard_widgets WHERE dashboard_id = ? ORDER BY pos_y, pos_x",
        (dashboard_id,),
    ).fetchall()
    conn.close()
    result = dict(dash)
    result['widgets'] = [dict(w) for w in widgets]
    return result


def add_widget(dashboard_id: int, tipo: str, titulo: str, fuente: str,
               fuente_config: str, chart_config: str,
               pos_x: int, pos_y: int, ancho: int, alto: int) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO dashboard_widgets "
        "(dashboard_id, tipo, titulo, fuente, fuente_config, chart_config, "
        " pos_x, pos_y, ancho, alto) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (dashboard_id, tipo, titulo, fuente, fuente_config, chart_config,
         pos_x, pos_y, ancho, alto),
    )
    conn.commit()
    widget_id = cur.lastrowid
    conn.close()
    return widget_id


def update_widget(widget_id: int, titulo: str, fuente_config: str,
                  chart_config: str, pos_x: int, pos_y: int,
                  ancho: int, alto: int) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE dashboard_widgets SET titulo=?, fuente_config=?, chart_config=?, "
        "pos_x=?, pos_y=?, ancho=?, alto=? WHERE id=?",
        (titulo, fuente_config, chart_config, pos_x, pos_y, ancho, alto, widget_id),
    )
    conn.commit()
    conn.close()


def delete_widget(widget_id: int) -> None:
    conn = get_db()
    conn.execute("DELETE FROM dashboard_widgets WHERE id = ?", (widget_id,))
    conn.commit()
    conn.close()


def get_widget(widget_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM dashboard_widgets WHERE id = ?", (widget_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_widget_positions(positions: list[dict]) -> None:
    conn = get_db()
    for p in positions:
        conn.execute(
            "UPDATE dashboard_widgets SET pos_x=?, pos_y=?, ancho=?, alto=? WHERE id=?",
            (int(p['pos_x']), int(p['pos_y']),
             int(p['ancho']), int(p['alto']), int(p['widget_id'])),
        )
    conn.commit()
    conn.close()


def seed_example_dashboards() -> None:
    """Inserta 2 dashboards de ejemplo si la tabla está vacía."""
    if count_dashboards() > 0:
        return
    import json as _json

    d1 = create_dashboard(
        "Monitoreo Energético CIMA",
        "Potencia, corriente y energía del torno CNC en tiempo real",
        "admin",
    )
    add_widget(d1, 'line', 'Potencia Torno — últimas 2h', 'influxdb',
               _json.dumps({"measurement": "sensor-data", "field": "power_w",
                            "machine_id": "torno", "range": "-2h",
                            "aggregation": "mean", "window": "5m"}),
               _json.dumps({"color": "#00d4aa"}), 0, 0, 8, 4)
    add_widget(d1, 'kpi', 'Corriente Actual (A)', 'influxdb',
               _json.dumps({"measurement": "sensor-data", "field": "irms_a",
                            "machine_id": "torno", "range": "-5m",
                            "aggregation": "mean", "window": "1m"}),
               _json.dumps({"color": "#ffa502"}), 8, 0, 4, 2)
    add_widget(d1, 'bar', 'Energía por Hora (kWh)', 'influxdb',
               _json.dumps({"measurement": "sensor-data", "field": "energy_kwh",
                            "machine_id": "torno", "range": "-8h",
                            "aggregation": "sum", "window": "1h"}),
               _json.dumps({"color": "#5352ed"}), 8, 2, 4, 4)

    d2 = create_dashboard(
        "Resumen Celda 3105",
        "OEE, calidad de piezas y últimos ciclos de la celda",
        "admin",
    )
    add_widget(d2, 'pie', 'Calidad de Piezas', 'static',
               _json.dumps({"labels": ["Aprobadas", "Rechazadas"],
                            "values": [0, 0]}),
               _json.dumps({"color": "#00d4aa"}), 0, 0, 4, 4)
    add_widget(d2, 'kpi', 'OEE Actual (%)', 'static',
               _json.dumps({"labels": ["OEE"], "values": [0]}),
               _json.dumps({"color": "#ffa502"}), 4, 0, 4, 2)
    add_widget(d2, 'table', 'Últimos Ciclos', 'static',
               _json.dumps({"labels": ["Ciclo", "Tipo", "Duración", "Resultado"],
                            "values": []}),
               _json.dumps({}), 4, 2, 8, 4)

    log.info("Dashboard Builder: 2 dashboards de ejemplo creados")


def log_audit(username: str, accion: str, exitoso: bool,
              ip: str = "127.0.0.1", detalle: str = "") -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (username, accion, exitoso, ip, detalle) VALUES (?,?,?,?,?)",
        (username, accion, int(exitoso), ip, detalle),
    )
    conn.commit()
    conn.close()


def get_audit_logs(limit: int = 100) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_users() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, rol, huella_id, activo, created_at FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(username: str) -> None:
    conn = get_db()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# InfluxDB
# ---------------------------------------------------------------------------

def _influx_client():
    """Retorna (client, write_api) o None si no se puede conectar."""
    try:
        from influxdb_client import InfluxDBClient  # type: ignore
        url   = os.getenv("INFLUXDB_URL",   f"http://{RPi_IP}:8086")
        token = os.getenv("INFLUXDB_TOKEN", "")
        client = InfluxDBClient(url=url, token=token, org=INFLUXDB_ORG, timeout=3000)
        return client
    except Exception as exc:
        log.warning("InfluxDB no disponible: %s", exc)
        return None


def query_energy_24h(machine_id: str | None = None) -> list[dict]:
    """
    Energía últimas 24 h desde InfluxDB.
    Retorna lista de dicts con: machine_id, power_w, irms_a, energy_kwh, time
    Si InfluxDB no responde → datos de demo.
    machine_id: filtrar por tag (ej. 'torno'); None = todas las máquinas.
    """
    client = _influx_client()
    if client is None:
        return _demo_energy()

    machine_filter = f'|> filter(fn: (r) => r.machine_id == "{machine_id}")' if machine_id else ""
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "{ENERGY_MEASUREMENT}")
      {machine_filter}
      |> filter(fn: (r) => r._field == "power_w" or r._field == "irms_a" or r._field == "energy_kwh")
      |> pivot(rowKey: ["_time", "machine_id"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: false)
    """
    try:
        query_api = client.query_api()
        tables = query_api.query(flux)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time":       record.get_time().isoformat(),
                    "machine_id": record.values.get("machine_id", "unknown"),
                    "power_w":    record.values.get("power_w", 0.0),
                    "irms_a":     record.values.get("irms_a", 0.0),
                    "energy_kwh": record.values.get("energy_kwh", 0.0),
                })
        client.close()
        return results if results else _demo_energy()
    except Exception as exc:
        log.warning("Query InfluxDB falló: %s", exc)
        client.close()
        return _demo_energy()


def query_energy_cost_admin() -> dict:
    """
    KPIs monetarios para el rol admin.
    Retorna: total_kwh, costo_mxn, ahorro_estimado_mxn, roi_pct
    """
    data = query_energy_24h()
    total_kwh = sum(d["energy_kwh"] for d in data)
    costo_mxn = total_kwh * TARIFA_KWH_MXN
    baseline_kwh  = total_kwh * BASELINE_FACTOR
    ahorro_mxn    = (baseline_kwh - total_kwh) * TARIFA_KWH_MXN
    # ROI simplificado: ahorro anualizado vs inversión estimada del proyecto
    inversion_mxn = float(os.getenv("INVERSION_PROYECTO_MXN", "450000"))
    ahorro_anual  = ahorro_mxn * 365
    roi_pct = (ahorro_anual / inversion_mxn * 100) if inversion_mxn else 0.0
    return {
        "total_kwh":          round(total_kwh, 2),
        "costo_mxn":          round(costo_mxn, 2),
        "ahorro_estimado_mxn": round(ahorro_mxn, 2),
        "roi_pct":            round(roi_pct, 1),
        "tarifa_kwh":         TARIFA_KWH_MXN,
    }


def _median_filter(values: list) -> float:
    """Mediana de una lista de números; devuelve 0.0 si vacía."""
    if not values:
        return 0.0
    return sorted(values)[len(values) // 2]


# CAPA 5 — límite superior para gauges de planta1 (torno max ~7.45A)
_SCT_MAX_DISPLAY_AMPS = 8.5


def query_latest_power(machine_id: str | None = None) -> dict:
    """Último valor de potencia para el gauge de planta1.
    Aplica mediana sobre los últimos 5 puntos y descarta lecturas > 8.5A.
    """
    data = query_energy_24h(machine_id=machine_id)
    if not data:
        return {"power_w": 0.0, "irms_a": 0.0}
    recent = [r for r in data[-5:] if r["irms_a"] <= _SCT_MAX_DISPLAY_AMPS]
    if not recent:
        return {"power_w": 0.0, "irms_a": 0.0}
    return {
        "power_w": _median_filter([r["power_w"] for r in recent]),
        "irms_a":  _median_filter([r["irms_a"]  for r in recent]),
    }


def query_celda3105_status() -> dict:
    """Estado actual de la Celda 3105 para planta2."""
    client = _influx_client()
    if client is None:
        return _demo_celda3105()

    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r._measurement == "celda3105_estado")
      |> last()
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """
    try:
        tables = client.query_api().query(flux)
        result = {}
        for table in tables:
            for record in table.records:
                result.update(record.values)
        client.close()
        return result if result else _demo_celda3105()
    except Exception as exc:
        log.warning("Query celda3105: %s", exc)
        client.close()
        return _demo_celda3105()


def query_energy_realtime(n: int = 60, machine_id: str | None = None) -> list[dict]:
    """Últimos n puntos de energía (~5 min a 5 s/punto) para gráficas en tiempo real.
    machine_id: filtrar por tag (ej. 'torno'); None = todas las máquinas.
    """
    client = _influx_client()
    if client is None:
        return _demo_energy()[-n:]
    machine_filter = f'|> filter(fn: (r) => r.machine_id == "{machine_id}")' if machine_id else ""
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -8m)
      |> filter(fn: (r) => r._measurement == "{ENERGY_MEASUREMENT}")
      {machine_filter}
      |> filter(fn: (r) => r._field == "power_w" or r._field == "irms_a" or r._field == "energy_kwh")
      |> pivot(rowKey: ["_time", "machine_id"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: false)
      |> tail(n: {n})
    """
    try:
        tables = client.query_api().query(flux)
        results = []
        for table in tables:
            for record in table.records:
                irms_a = float(record.values.get("irms_a", 0) or 0)
                if irms_a > _SCT_MAX_DISPLAY_AMPS:
                    continue  # descartar lecturas fuera del rango válido del torno
                results.append({
                    "time":       record.get_time().isoformat(),
                    "machine_id": record.values.get("machine_id", "unknown"),
                    "power_w":    float(record.values.get("power_w",    0) or 0),
                    "irms_a":     irms_a,
                    "energy_kwh": float(record.values.get("energy_kwh", 0) or 0),
                })
        client.close()
        return results if results else _demo_energy()[-n:]
    except Exception as exc:
        log.warning("query_energy_realtime: %s", exc)
        try: client.close()
        except Exception: pass
        return _demo_energy()[-n:]


def query_rfid_cycles(limit: int = 20) -> list[dict]:
    """
    Últimos N ciclos RFID completos (measurement cima_rfid_cycles).
    Retorna: part_id, ts_start, ts_end, machine_id, uid, duration_s, energy_wh, cost_mxn
    """
    client = _influx_client()
    if client is None:
        return _demo_rfid_cycles()

    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -30d)
      |> filter(fn: (r) => r._measurement == "cima_rfid_cycles")
      |> pivot(rowKey: ["_time", "machine_id", "uid", "part_id"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit})
    """
    try:
        tables = client.query_api().query(flux)
        results = []
        for table in tables:
            for record in table.records:
                ts_end    = record.get_time()
                dur_s     = float(record.values.get("duration_s", 0) or 0)
                energy_wh = float(record.values.get("energy_wh",  0) or 0)
                ts_start  = (ts_end - timedelta(seconds=dur_s)).isoformat()
                results.append({
                    "part_id":    str(record.values.get("part_id",    "?") or "?"),
                    "ts_end":     ts_end.isoformat(),
                    "ts_start":   ts_start,
                    "machine_id": str(record.values.get("machine_id", "?") or "?"),
                    "uid":        str(record.values.get("uid",        "?") or "?"),
                    "duration_s": round(dur_s),
                    "energy_wh":  round(energy_wh, 2),
                    "cost_mxn":   round(energy_wh / 1000.0 * TARIFA_KWH_MXN, 4),
                })
        client.close()
        return results  # lista vacía si no hay datos reales — sin fallback demo
    except Exception as exc:
        log.warning("query_rfid_cycles: %s", exc)
        try: client.close()
        except Exception: pass
        return []  # error de query → lista vacía, no demo


def query_rfid_history(n: int = 10) -> list[dict]:
    """Últimos n scans RFID (solo entradas con uid no vacío)."""
    client = _influx_client()
    if client is None:
        return []
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "rfid_status"
                        and r._field == "uid"
                        and r._value != "")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {n})
    """
    try:
        tables = client.query_api().query(flux)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time":       record.get_time().isoformat(),
                    "uid":        str(record.get_value() or "?"),
                    "machine_id": record.values.get("machine_id", "?"),
                })
        client.close()
        return results
    except Exception as exc:
        log.warning("query_rfid_history: %s", exc)
        try: client.close()
        except Exception: pass
        return []


def query_rfid_pieza_detalle(part_id: str) -> dict | None:
    """Detalle completo de una pieza específica desde InfluxDB."""
    client = _influx_client()
    if client is None:
        return None
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -30d)
      |> filter(fn: (r) => r._measurement == "cima_rfid_cycles")
      |> filter(fn: (r) => r.part_id == "{part_id}")
      |> pivot(rowKey: ["_time", "machine_id", "uid", "part_id"], columnKey: ["_field"], valueColumn: "_value")
      |> limit(n: 1)
    """
    try:
        tables = client.query_api().query(flux)
        for table in tables:
            for record in table.records:
                dur_s     = float(record.values.get("duration_s", 0) or 0)
                energy_wh = float(record.values.get("energy_wh",  0) or 0)
                ts_end    = record.get_time()
                ts_start_str = str(record.values.get("ts_start", "") or "")
                if not ts_start_str:
                    ts_start_str = (ts_end - timedelta(seconds=dur_s)).isoformat()
                client.close()
                return {
                    "part_id":    str(record.values.get("part_id",    "?") or "?"),
                    "ts_end":     ts_end.isoformat(),
                    "ts_start":   ts_start_str,
                    "machine_id": str(record.values.get("machine_id", "?") or "?"),
                    "uid":        str(record.values.get("uid",        "?") or "?"),
                    "duration_s": round(dur_s),
                    "energy_wh":  round(energy_wh, 3),
                    "cost_mxn":   round(energy_wh / 1000.0 * TARIFA_KWH_MXN, 4),
                }
        client.close()
        return None
    except Exception as exc:
        log.warning("query_rfid_pieza_detalle: %s", exc)
        try: client.close()
        except Exception: pass
        return None


def query_turno_promedios(horas: int = 8) -> dict:
    """Promedios del turno actual (últimas N horas) para comparativa individual."""
    client = _influx_client()
    if client is None:
        return {"avg_duration_s": 0.0, "avg_energy_wh": 0.0, "count": 0}
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -{horas}h)
      |> filter(fn: (r) => r._measurement == "cima_rfid_cycles")
      |> filter(fn: (r) => r._field == "duration_s" or r._field == "energy_wh")
      |> group(columns: ["_field"])
      |> mean()
    """
    try:
        tables = client.query_api().query(flux)
        result = {"avg_duration_s": 0.0, "avg_energy_wh": 0.0, "count": 0}
        for table in tables:
            for record in table.records:
                if record.get_field() == "duration_s":
                    result["avg_duration_s"] = float(record.get_value() or 0)
                elif record.get_field() == "energy_wh":
                    result["avg_energy_wh"]  = float(record.get_value() or 0)
        client.close()
        return result
    except Exception as exc:
        log.warning("query_turno_promedios: %s", exc)
        try: client.close()
        except Exception: pass
        return {"avg_duration_s": 0.0, "avg_energy_wh": 0.0, "count": 0}


# ---------------------------------------------------------------------------
# Datos de demo (fallback cuando InfluxDB no responde)
# ---------------------------------------------------------------------------

def _demo_energy() -> list[dict]:
    import math, random
    now = datetime.now(timezone.utc)
    result = []
    for i in range(48):
        t = now - timedelta(minutes=30 * (47 - i))
        base = 1800 + 400 * math.sin(i / 8) + random.uniform(-50, 50)
        result.append({
            "time":       t.isoformat(),
            "machine_id": "CIMA-TORNO-01",
            "power_w":    round(base, 1),
            "irms_a":     round(base / 220, 2),
            "energy_kwh": round(base / 1000 * 0.5, 4),
        })
    return result


def _demo_rfid_cycles() -> list[dict]:
    """Datos de demostración para ciclos RFID completados."""
    import random
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(10):
        ts_end = now - timedelta(minutes=15 * i)
        dur    = random.randint(45, 180)
        ewh    = round(dur * 1400 / 3600000, 2)  # ~1400W promedio en Wh
        uid    = f"AA:BB:CC:0{i:X}"
        ts_s   = (ts_end - timedelta(seconds=dur)).isoformat()
        rows.append({
            "part_id":    f"PIEZA-{uid}-{ts_s}",
            "ts_end":     ts_end.isoformat(),
            "ts_start":   ts_s,
            "machine_id": "torno",
            "uid":        uid,
            "duration_s": dur,
            "energy_wh":  ewh,
            "cost_mxn":   round(ewh / 1000.0 * TARIFA_KWH_MXN, 4),
        })
    return rows


def query_celda3105_latest() -> dict:
    """Último estado completo del PLC desde InfluxDB (measurement celda3105_estado)."""
    client = _influx_client()
    if client is None:
        return _demo_celda3105_latest()
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -2m)
      |> filter(fn: (r) => r._measurement == "celda3105_estado")
      |> last()
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """
    try:
        tables = client.query_api().query(flux)
        result = {}
        for table in tables:
            for record in table.records:
                result.update({k: v for k, v in record.values.items()
                                if not k.startswith("_") and k not in ("result", "table")})
        client.close()
        return result if result else _demo_celda3105_latest()
    except Exception as exc:
        log.warning("query_celda3105_latest: %s", exc)
        try: client.close()
        except Exception: pass
        return _demo_celda3105_latest()


def query_celda3105_kpis() -> dict:
    """KPIs del turno actual (últimas 8h) para Celda 3105."""
    client = _influx_client()
    if client is None:
        return _demo_celda3105_kpis()
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -8h)
      |> filter(fn: (r) => r._measurement == "celda3105_estado")
      |> filter(fn: (r) => r._field == "piezas_procesadas" or r._field == "piezas_aprobadas"
                        or r._field == "piezas_rechazadas" or r._field == "oee"
                        or r._field == "tiempo_ciclo_promedio_s")
      |> last()
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """
    try:
        tables = client.query_api().query(flux)
        result = {}
        for table in tables:
            for record in table.records:
                result.update({k: v for k, v in record.values.items()
                                if not k.startswith("_") and k not in ("result", "table")})
        client.close()
        return result if result else _demo_celda3105_kpis()
    except Exception as exc:
        log.warning("query_celda3105_kpis: %s", exc)
        try: client.close()
        except Exception: pass
        return _demo_celda3105_kpis()


def query_celda3105_operaciones(limit: int = 10) -> list[dict]:
    """Últimas N operaciones Celda 3105 desde InfluxDB (measurement celda3105_operacion)."""
    client = _influx_client()
    if client is None:
        return _demo_celda3105_operaciones()
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -8h)
      |> filter(fn: (r) => r._measurement == "celda3105_operacion")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit})
    """
    try:
        tables = client.query_api().query(flux)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "num":      int(record.values.get("num", 0) or 0),
                    "tiempo_s": float(record.values.get("tiempo_ciclo_s", 0) or 0),
                    "aprobada": bool(record.values.get("aprobada", False)),
                    "hora":     record.get_time().strftime("%H:%M:%S"),
                })
        client.close()
        return results if results else _demo_celda3105_operaciones()
    except Exception as exc:
        log.warning("query_celda3105_operaciones: %s", exc)
        try: client.close()
        except Exception: pass
        return _demo_celda3105_operaciones()


def _demo_celda3105_ciclos_activos() -> list[dict]:
    import time
    now = time.time()
    return [
        {"ciclo_id": "CIC-0042", "tipo": "Torneado", "start_ts": now - 47},
        {"ciclo_id": "CIC-0043", "tipo": "Fresado",  "start_ts": now - 112},
    ]


def _demo_celda3105_ciclos_historial() -> list[dict]:
    return [
        {"ciclo_id": "CIC-0041", "tipo": "Torneado", "duracion_s": 87.3,  "resultado": "aprobado",  "hora": "09:42:15"},
        {"ciclo_id": "CIC-0040", "tipo": "Fresado",  "duracion_s": 103.1, "resultado": "rechazado", "hora": "09:38:02"},
        {"ciclo_id": "CIC-0039", "tipo": "Torneado", "duracion_s": 91.5,  "resultado": "aprobado",  "hora": "09:33:47"},
    ]


def query_celda3105_ciclos_activos() -> list[dict]:
    """Ciclos activos en Celda 3105 (measurement celda3105_ciclos, resultado=en_progreso)."""
    client = _influx_client()
    if client is None:
        return _demo_celda3105_ciclos_activos()
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -8h)
      |> filter(fn: (r) => r._measurement == "celda3105_ciclos")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> filter(fn: (r) => r.resultado == "en_progreso")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 2)
    """
    try:
        tables = client.query_api().query(flux)
        results = []
        for table in tables:
            for record in table.records:
                v = record.values
                results.append({
                    "ciclo_id": str(v.get("ciclo_id", "—")),
                    "tipo":     str(v.get("tipo", "—")),
                    "start_ts": float(v.get("start_ts", 0) or 0),
                })
        client.close()
        return results
    except Exception as exc:
        log.warning("query_celda3105_ciclos_activos: %s", exc)
        try: client.close()
        except Exception: pass
        return []


def query_celda3105_ciclos_historial(limit: int = 10) -> list[dict]:
    """Últimos N ciclos completados en Celda 3105 (measurement celda3105_ciclos)."""
    client = _influx_client()
    if client is None:
        return _demo_celda3105_ciclos_historial()
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: -8h)
      |> filter(fn: (r) => r._measurement == "celda3105_ciclos")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> filter(fn: (r) => r.resultado == "aprobado" or r.resultado == "rechazado")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit})
    """
    try:
        tables = client.query_api().query(flux)
        results = []
        for table in tables:
            for record in table.records:
                v = record.values
                results.append({
                    "ciclo_id":  str(v.get("ciclo_id", "—")),
                    "tipo":      str(v.get("tipo", "—")),
                    "duracion_s": float(v.get("duracion_s", 0) or 0),
                    "resultado": str(v.get("resultado", "—")),
                    "hora":      record.get_time().strftime("%H:%M:%S"),
                })
        client.close()
        return results
    except Exception as exc:
        log.warning("query_celda3105_ciclos_historial: %s", exc)
        try: client.close()
        except Exception: pass
        return _demo_celda3105_ciclos_historial()


def _query_widget_influx(measurement: str, field: str,
                         machine_id: str | None, range_str: str,
                         aggregation: str, window: str) -> list[dict]:
    """Query genérica para widgets del Dashboard Builder."""
    client = _influx_client()
    if client is None:
        return []
    machine_filter = (f'|> filter(fn: (r) => r.machine_id == "{machine_id}")'
                      if machine_id else "")
    flux = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {range_str})
      |> filter(fn: (r) => r._measurement == "{measurement}")
      {machine_filter}
      |> filter(fn: (r) => r._field == "{field}")
      |> aggregateWindow(every: {window}, fn: {aggregation}, createEmpty: false)
      |> sort(columns: ["_time"], desc: false)
    """
    try:
        tables = client.query_api().query(flux)
        results = []
        for table in tables:
            for record in table.records:
                val = record.get_value()
                results.append({
                    'time':  record.get_time().strftime('%H:%M'),
                    'value': round(float(val), 3) if val is not None else 0.0,
                })
        client.close()
        return results
    except Exception as exc:
        log.warning("_query_widget_influx: %s", exc)
        try: client.close()
        except Exception: pass
        return []


def subscribe_celda3105_mqtt(callback) -> None:
    """
    Suscribe a MQTT_TOPIC_CELDA en un hilo daemon.
    callback(payload: dict) se invoca por cada mensaje.
    """
    import paho.mqtt.client as mqtt_lib

    def _on_connect(client, userdata, flags, rc, *args):
        if rc == 0:
            client.subscribe(MQTT_TOPIC_CELDA)

    def _on_message(client, userdata, msg):
        try:
            callback(json.loads(msg.payload.decode()))
        except Exception as exc:
            log.warning("subscribe_celda3105_mqtt: %s", exc)

    def _run():
        try:
            try:
                client = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2)
            except AttributeError:
                client = mqtt_lib.Client()
            client.username_pw_set(MQTT_APP_USER, MQTT_APP_PASS)
            client.on_connect = _on_connect
            client.on_message = _on_message
            client.connect(MQTT_BROKER, MQTT_PORT_LOCAL, 60)
            client.loop_forever()
        except Exception as exc:
            log.warning("subscribe_celda3105_mqtt thread: %s", exc)

    threading.Thread(target=_run, daemon=True).start()


def _demo_celda3105() -> dict:
    return {
        "verde_celda":     1,
        "produciendo":     1,
        "disponible":      1,
        "bandas_activas":  3,
        "posicion_pieza":  4,
        "piezas_ok":       47,
        "piezas_nok":      3,
        "lead_time_avg_s": 38.4,
    }


def _demo_celda3105_latest() -> dict:
    return {
        "killswitch": 0, "modo_auto": 1, "emergencia": 0, "cobot_activo": 0,
        "estampado_up": 0, "estampado_down": 0,
        "banda1": 1, "banda2": 1, "banda3": 0, "banda4": 0,
        "banda_enfrente": 0, "bandas_atras": 0,
        "taladro1": 0, "taladro2": 0, "martillo1": 0, "martillo2": 0,
        "cognex_foto": 0, "cognex_aprobada": 0, "pieza_rechazada": 0,
        "semaforo_verde": 1, "semaforo_rojo": 0, "semaforo_azul": 0,
        "piezas_procesadas": 0, "piezas_aprobadas": 0, "piezas_rechazadas": 0,
        "tiempo_ciclo_s": 0.0, "tiempo_ciclo_promedio_s": 0.0, "oee": 0.0,
    }


def _demo_celda3105_kpis() -> dict:
    return {
        "piezas_procesadas": 0,
        "piezas_aprobadas":  0,
        "piezas_rechazadas": 0,
        "oee":               0.0,
        "tiempo_ciclo_promedio_s": 0.0,
    }


def _demo_celda3105_operaciones() -> list[dict]:
    return []
