"""
Vistas por rol — Smart Manufacturing CIMA + Celda 3105.
Cada clase DashboardXxx extiende CTkFrame y se monta en la ventana principal.
"""

# matplotlib.use("Agg") DEBE ir antes de cualquier otro import de matplotlib
import matplotlib
matplotlib.use("Agg")

import csv
import json
import logging
import queue
import socket
import tempfile
import threading
import time
from datetime import datetime, timedelta

import customtkinter as ctk

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

import paho.mqtt.client as mqtt_lib

from config import (
    COLOR_BG, COLOR_BG2, COLOR_BG3, COLOR_ACCENT, COLOR_ALERT,
    COLOR_WARN, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_GREEN,
    RPi_IP, SERVICES, TARIFA_KWH_MXN,
    MQTT_BROKER, MQTT_PORT_LOCAL, MQTT_APP_USER, MQTT_APP_PASS,
    MACHINE_ID_PLANTA1, MQTT_TOPIC_CELDA,
    SCREEN_HEIGHT, UI_SCALE,
)

# True cuando la pantalla tiene menos de 650px de alto (e.g. LCD 7" 1024×600)
_COMPACT = SCREEN_HEIGHT < 650

def _scale(size: int) -> int:
    """Escala tamaño de fuente proporcionalmente en pantallas pequeñas."""
    return max(8, round(size * 0.82)) if _COMPACT else size
from db import (
    query_energy_24h, query_energy_cost_admin, query_latest_power,
    query_energy_realtime, query_rfid_history, query_rfid_cycles,
    query_rfid_pieza_detalle, query_turno_promedios,
    query_celda3105_status, query_celda3105_latest,
    query_celda3105_kpis, query_celda3105_operaciones,
    get_audit_logs, get_all_users, delete_user,
)
from auth import add_user, enroll_fingerprint
from health_check import HealthChecker

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Widget helpers reutilizables
# ---------------------------------------------------------------------------

def _label(parent, text, size=13, bold=False, color=COLOR_TEXT, **kw):
    weight = "bold" if bold else "normal"
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(family="Inter", size=_scale(size), weight=weight),
        text_color=color, **kw,
    )


def _kpi_card(parent, title: str, value: str, unit: str = "",
              color: str = COLOR_ACCENT) -> ctk.CTkFrame:
    card = ctk.CTkFrame(parent, fg_color=COLOR_BG2, corner_radius=12)
    pad_v = (6, 0) if _COMPACT else (12, 0)
    pad_b = (0, 6) if _COMPACT else (0, 12)
    _label(card, title, size=11, color=COLOR_TEXT_DIM).pack(pady=pad_v)
    _label(card, value, size=22 if _COMPACT else 28, bold=True, color=color).pack()
    _label(card, unit, size=11, color=COLOR_TEXT_DIM).pack(pady=pad_b)
    return card


def _section_title(parent, text: str):
    _label(parent, text, size=14, bold=True, color=COLOR_ACCENT).pack(
        anchor="w", padx=16, pady=(16, 4)
    )
    ctk.CTkFrame(parent, height=1, fg_color=COLOR_BG3).pack(fill="x", padx=16)


def _make_tabview(parent) -> ctk.CTkTabview:
    return ctk.CTkTabview(
        parent,
        fg_color=COLOR_BG2,
        segmented_button_fg_color=COLOR_BG3,
        segmented_button_selected_color=COLOR_ACCENT,
        segmented_button_selected_hover_color=COLOR_ACCENT,
        text_color=COLOR_TEXT,
    )


# ---------------------------------------------------------------------------
# Gráfica de línea en tiempo real (matplotlib embebido)
# ---------------------------------------------------------------------------

class RealtimeEnergyChart(ctk.CTkFrame):
    """
    Gráfica de línea auto-refrescante (cada 5 s) que consulta InfluxDB.
    field: 'power_w' | 'irms_a' | 'energy_kwh'
    """

    def __init__(self, master, field: str, ylabel: str,
                 line_color: str, max_pts: int = 60,
                 machine_id: str | None = None, **kw):
        super().__init__(master, fg_color=COLOR_BG2, corner_radius=10, **kw)
        self._field      = field
        self._max_pts    = max_pts
        self._line_color = line_color
        self._machine_id = machine_id

        if not HAS_MPL:
            _label(self, "matplotlib no disponible", color=COLOR_ALERT).pack(pady=20)
            return

        _label(self, ylabel, size=10, color=COLOR_TEXT_DIM).pack(anchor="w", padx=10, pady=(6, 0))

        fig = Figure(figsize=(9, 1.2 if _COMPACT else 1.9), dpi=80, facecolor=COLOR_BG2)
        self._ax = fig.add_subplot(111)
        self._style_ax()
        fig.subplots_adjust(left=0.05, right=0.99, top=0.90, bottom=0.30)

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.get_tk_widget().configure(bg=COLOR_BG2)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self._canvas = canvas

        self.after(200, self._refresh)

    def _style_ax(self):
        ax = self._ax
        ax.set_facecolor(COLOR_BG)
        for spine in ax.spines.values():
            spine.set_edgecolor(COLOR_BG3)
        ax.tick_params(colors=COLOR_TEXT_DIM, labelsize=7, length=2)

    def _refresh(self):
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        data  = query_energy_realtime(self._max_pts, machine_id=self._machine_id)
        times = [d["time"][11:19] for d in data]
        vals  = [float(d.get(self._field, 0) or 0) for d in data]
        try:
            self.after(0, self._render, times, vals)
        except Exception:
            pass

    def _render(self, times: list, vals: list):
        if not self.winfo_exists():
            return
        ax = self._ax
        ax.cla()
        self._style_ax()

        if vals:
            xs = list(range(len(vals)))
            ax.plot(xs, vals, color=self._line_color, linewidth=1.5)
            ax.fill_between(xs, vals, alpha=0.12, color=self._line_color)
            ax.set_ylim(bottom=0, top=max(vals) * 1.2 or 1)
            step = max(1, len(times) // 6)
            ticks = list(range(0, len(times), step))
            ax.set_xticks(ticks)
            ax.set_xticklabels([times[i] for i in ticks], fontsize=7)
        else:
            ax.text(0.5, 0.5, "Sin datos — verificar pipeline ESP32 → n8n → InfluxDB",
                    ha="center", va="center", color=COLOR_TEXT_DIM, fontsize=8,
                    transform=ax.transAxes)

        self._canvas.draw_idle()
        self.after(5000, self._refresh)



# ---------------------------------------------------------------------------
# Panel RFID con suscripción MQTT en tiempo real
# ---------------------------------------------------------------------------

class RFIDPanel(ctk.CTkFrame):
    """Muestra el último scan RFID y el historial de los 10 últimos."""

    def __init__(self, master, **kw):
        super().__init__(master, fg_color=COLOR_BG2, corner_radius=10, **kw)
        self._history: list[dict] = []
        self._q: queue.Queue = queue.Queue()
        self._mqtt_client = None
        self._build_ui()
        threading.Thread(target=self._load_history, daemon=True).start()
        self._connect_mqtt()
        self._poll_queue()

    # ---- UI ----

    def _build_ui(self):
        _section_title(self, "RFID — Escaneos en Tiempo Real")

        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.pack(fill="x", padx=16, pady=8)
        for col, (attr, title) in enumerate([
            ("_lbl_uid",  "Último UID"),
            ("_lbl_ts",   "Timestamp"),
            ("_lbl_mac",  "Máquina"),
        ]):
            card = ctk.CTkFrame(info_row, fg_color=COLOR_BG3, corner_radius=8)
            card.grid(row=0, column=col, padx=8, sticky="nsew")
            info_row.columnconfigure(col, weight=1)
            _label(card, title, size=10, color=COLOR_TEXT_DIM).pack(pady=(6, 0))
            lbl = _label(card, "---", size=15, bold=True, color=COLOR_ACCENT)
            lbl.pack(pady=(0, 6))
            setattr(self, attr, lbl)

        _label(self, "Historial (últimos 10 scans)",
               size=11, color=COLOR_TEXT_DIM).pack(anchor="w", padx=16, pady=(8, 2))
        self._table = ctk.CTkScrollableFrame(self, fg_color=COLOR_BG, height=180)
        self._table.pack(fill="x", padx=16, pady=(0, 8))
        self._render_table([])

    # ---- Carga histórica desde InfluxDB ----

    def _load_history(self):
        data = query_rfid_history(10)
        self._history = data
        try:
            self.after(0, self._render_table, data)
        except Exception:
            pass

    # ---- MQTT en tiempo real (hilo de red → queue → hilo UI) ----

    def _connect_mqtt(self):
        try:
            try:
                client = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2)
                client.on_connect = self._on_connect_v2
            except AttributeError:
                client = mqtt_lib.Client()
                client.on_connect = self._on_connect_v1
            client.username_pw_set(MQTT_APP_USER, MQTT_APP_PASS)
            client.on_message = self._on_message
            client.connect_async(MQTT_BROKER, MQTT_PORT_LOCAL, 60)
            client.loop_start()
            self._mqtt_client = client
        except Exception as exc:
            log.warning("RFIDPanel MQTT: %s", exc)

    def _on_connect_v2(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe("cima/rfid/scan")

    def _on_connect_v1(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("cima/rfid/scan")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            uid     = payload.get("uid", "?")
            machine = payload.get("machine_id", "?")
            if not uid or uid == "?":
                return
            entry = {
                "time":       datetime.now().isoformat(timespec="seconds"),
                "uid":        uid,
                "machine_id": machine,
            }
            self._q.put_nowait(entry)
        except Exception as exc:
            log.warning("RFIDPanel msg parse: %s", exc)

    def _poll_queue(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                entry = self._q.get_nowait()
                self._history.insert(0, entry)
                self._history = self._history[:10]
                self._on_new_scan(entry)
        except queue.Empty:
            pass
        self.after(500, self._poll_queue)

    # ---- Actualizaciones de UI (siempre en hilo principal) ----

    def _on_new_scan(self, entry: dict):
        if not self.winfo_exists():
            return
        self._lbl_uid.configure(text=entry["uid"])
        self._lbl_ts.configure(text=entry["time"][11:19])
        self._lbl_mac.configure(text=entry["machine_id"])
        self._render_table(self._history)

    def _render_table(self, data: list[dict]):
        if not self.winfo_exists():
            return
        for w in self._table.winfo_children():
            w.destroy()
        for col, h in enumerate(["Hora", "UID", "Máquina"]):
            _label(self._table, h, size=10, bold=True,
                   color=COLOR_ACCENT).grid(row=0, column=col, padx=10, pady=2, sticky="w")
        if not data:
            _label(self._table, "Sin scans recientes",
                   size=11, color=COLOR_TEXT_DIM).grid(row=1, column=0, columnspan=3,
                                                        padx=10, pady=8)
            return
        for row_i, entry in enumerate(data, start=1):
            vals = [
                entry.get("time", "?")[11:19],
                entry.get("uid",  "?"),
                entry.get("machine_id", "?"),
            ]
            for col, v in enumerate(vals):
                _label(self._table, v, size=10, color=COLOR_TEXT).grid(
                    row=row_i, column=col, padx=10, pady=1, sticky="w"
                )

    def destroy(self):
        if self._mqtt_client:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception:
                pass
        super().destroy()


# ---------------------------------------------------------------------------
# Panel de salud de servicios (reutilizable en todos los dashboards)
# ---------------------------------------------------------------------------

class _SaludTab(ctk.CTkFrame):
    """Pestaña de salud simple: verifica TCP/HTTP de los servicios del stack."""

    def __init__(self, master, health_checker: HealthChecker | None = None, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._hc = health_checker
        self._svc_labels: dict[str, ctk.CTkLabel] = {}
        self._build()
        if health_checker:
            health_checker.subscribe(self._on_health_update)
        else:
            self.after(300, self._check_once)

    def _build(self):
        _section_title(self, "Estado de Servicios del Stack")
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=16, pady=8)
        for i, (key, cfg) in enumerate(SERVICES.items()):
            row, col = i // 3, i % 3
            card = ctk.CTkFrame(grid, fg_color=COLOR_BG2, corner_radius=10, width=160 if _COMPACT else 200)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            grid.columnconfigure(col, weight=1)
            _label(card, cfg["label"], size=14, bold=True).pack(pady=(10, 2))
            _label(card, f":{cfg['port']}", size=11, color=COLOR_TEXT_DIM).pack()
            lbl = _label(card, "●  Verificando...", size=13, color=COLOR_WARN)
            lbl.pack(pady=(4, 10))
            self._svc_labels[key] = lbl
        ctk.CTkButton(
            self, text="Verificar ahora",
            fg_color=COLOR_ACCENT, hover_color=COLOR_BG3, text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._manual_check,
        ).pack(pady=8)

    def _manual_check(self):
        if self._hc:
            threading.Thread(target=self._hc.check_now, daemon=True).start()
        else:
            self.after(0, self._check_once)

    def _check_once(self):
        threading.Thread(target=self._run_check, daemon=True).start()

    def _run_check(self):
        result = {}
        for key, cfg in SERVICES.items():
            try:
                with socket.create_connection((RPi_IP, cfg["port"]), timeout=2):
                    result[key] = "ok"
            except Exception:
                result[key] = "down"
        try:
            self.after(0, self._on_health_update, result)
        except Exception:
            pass

    def _on_health_update(self, statuses: dict):
        color_map = {"ok": COLOR_GREEN, "warn": COLOR_WARN, "down": COLOR_ALERT}
        text_map  = {"ok": "●  Operativo", "warn": "●  Lento", "down": "●  Caído"}
        for key, status in statuses.items():
            lbl = self._svc_labels.get(key)
            if lbl:
                try:
                    lbl.configure(text=text_map.get(status, "●  ?"),
                                  text_color=color_map.get(status, COLOR_WARN))
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Panel de Trazabilidad RFID
# ---------------------------------------------------------------------------

class TrazabilidadPanel(ctk.CTkFrame):
    """
    Historial de ciclos RFID con banner de ciclo activo en tiempo real.
    rol: 'planta1' oculta columna de costo; 'admin' la muestra.
    """

    def __init__(self, master, rol: str, **kw):
        super().__init__(master, fg_color=COLOR_BG, **kw)
        self._rol       = rol
        self._show_cost = (rol == "admin")
        self._active: dict | None = None
        self._banner_energy_wh = 0.0
        self._start_epoch = 0.0
        self._q: queue.Queue = queue.Queue()
        self._mqtt_client = None
        self._all_cycles: list[dict] = []
        self._filter = "today"

        self._build_banner()
        self._build_stats_row()    # KPIs compactos arriba
        self._build_filter_row()   # filtros + CSV + PDF — siempre visible
        self._build_table_section()  # ocupa el resto del espacio

        threading.Thread(target=self._load_data, daemon=True).start()
        self._connect_mqtt()
        self._poll_queue()
        self._tick()

    # ── Banner de ciclo activo ────────────────────────────────────────────

    def _build_banner(self):
        self._banner = ctk.CTkLabel(
            self,
            text="⚪ Sin ciclo activo — Acerque tarjeta RFID para iniciar",
            font=ctk.CTkFont(family="Inter", size=_scale(12), weight="bold"),
            text_color=COLOR_TEXT_DIM,
            fg_color=COLOR_BG2,
            corner_radius=8,
            anchor="center",
        )
        self._banner.pack(fill="x", padx=16, pady=(4, 2), ipady=5)

    def _tick(self):
        if not self.winfo_exists():
            return
        if self._active:
            elapsed = int(time.time() - self._start_epoch)
            mm, ss  = divmod(elapsed, 60)
            pid     = self._active.get("part_id", "?")
            ewh     = self._banner_energy_wh
            self._banner.configure(
                text=f"🟢 CICLO ACTIVO — {pid} — {mm:02d}:{ss:02d} — {ewh:.1f} Wh",
                text_color=COLOR_GREEN,
                fg_color="#1a3a2e",
            )
        else:
            self._banner.configure(
                text="⚪ Sin ciclo activo — Acerque tarjeta RFID para iniciar",
                text_color=COLOR_TEXT_DIM,
                fg_color=COLOR_BG2,
            )
        self.after(1000, self._tick)

    # ── Filtros de fecha ─────────────────────────────────────────────────

    def _build_filter_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(2, 4))
        _label(row, "Período:", size=11, color=COLOR_TEXT_DIM).pack(side="left", padx=(0, 6))
        for label, key in [("Hoy", "today"), ("Esta semana", "week"), ("Este mes", "month")]:
            ctk.CTkButton(
                row, text=label, width=85, height=26,
                fg_color=COLOR_BG3, hover_color=COLOR_ACCENT, text_color=COLOR_TEXT,
                font=ctk.CTkFont(size=_scale(11)),
                command=lambda k=key: self._apply_filter(k),
            ).pack(side="left", padx=3)
        ctk.CTkButton(
            row, text="CSV", width=46, height=26,
            fg_color=COLOR_BG3, hover_color=COLOR_ACCENT, text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=_scale(11)),
            command=self._export_csv,
        ).pack(side="left", padx=3)
        self._export_msg = _label(row, "", size=10, color=COLOR_GREEN)
        self._export_msg.pack(side="left", padx=3)
        # PDF y Refrescar alineados a la derecha — siempre visibles
        ctk.CTkButton(
            row, text="📄 Exportar PDF", height=26,
            fg_color=COLOR_ACCENT, hover_color="#00b090", text_color=COLOR_BG,
            font=ctk.CTkFont(size=_scale(11), weight="bold"),
            command=self._export_pdf,
        ).pack(side="right", padx=3)
        ctk.CTkButton(
            row, text="↺", width=30, height=26,
            fg_color=COLOR_BG2, hover_color=COLOR_BG3, text_color=COLOR_ACCENT,
            font=ctk.CTkFont(size=_scale(12)),
            command=lambda: threading.Thread(target=self._load_data, daemon=True).start(),
        ).pack(side="right", padx=3)

    def _apply_filter(self, key: str):
        self._filter = key
        filtered = self._filtered_data()
        self._render_table(filtered)
        self._update_stats(filtered)

    def _filtered_data(self) -> list[dict]:
        now = datetime.now()
        if self._filter == "today":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif self._filter == "week":
            cutoff = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = []
        for d in self._all_cycles:
            try:
                ts = d.get("ts_end", "")
                if ts:
                    naive = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                    if naive >= cutoff:
                        result.append(d)
                else:
                    result.append(d)
            except Exception:
                result.append(d)
        return result

    # ── Tabla de historial ───────────────────────────────────────────────

    def _build_table_section(self):
        _label(self, "Historial por Pieza", size=11, bold=True,
               color=COLOR_TEXT_DIM).pack(anchor="w", padx=16, pady=(0, 2))
        self._table_frame = ctk.CTkScrollableFrame(self, fg_color=COLOR_BG2)
        self._table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 6))

    def _render_table(self, data: list[dict]):
        if not self.winfo_exists():
            return
        for w in self._table_frame.winfo_children():
            w.destroy()

        headers = ["Part ID", "Inicio", "Fin", "Duración", "Energía (Wh)"]
        if self._show_cost:
            headers.append("Costo (MXN)")

        for col, h in enumerate(headers):
            _label(self._table_frame, h, size=10, bold=True,
                   color=COLOR_ACCENT).grid(row=0, column=col, padx=8, pady=4, sticky="w")

        if not data:
            _label(self._table_frame, "Sin piezas en el período seleccionado",
                   size=11, color=COLOR_TEXT_DIM).grid(
                row=1, column=0, columnspan=len(headers), padx=10, pady=8
            )
            return

        for row_i, d in enumerate(data[:50], start=1):
            dur_s = int(d.get("duration_s", 0))
            mm, ss = divmod(dur_s, 60)
            ts_end   = d.get("ts_end",   "?")[:19].replace("T", " ")
            ts_start = d.get("ts_start", "?")[:19].replace("T", " ")
            vals = [
                d.get("part_id", "?"),
                ts_start,
                ts_end,
                f"{mm:02d}:{ss:02d}",
                f"{d.get('energy_wh', 0):.2f}",
            ]
            if self._show_cost:
                vals.append(f"${d.get('cost_mxn', 0):.4f}")

            row_color = COLOR_BG3 if row_i % 2 == 0 else COLOR_BG2
            for col, v in enumerate(vals):
                btn = ctk.CTkButton(
                    self._table_frame, text=v, width=0,
                    fg_color=row_color, hover_color=COLOR_BG3,
                    text_color=COLOR_TEXT, anchor="w",
                    font=ctk.CTkFont(family="Inter", size=_scale(10)),
                    command=lambda piece=d: self._show_detail(piece),
                )
                btn.grid(row=row_i, column=col, padx=4, pady=1, sticky="ew")

    def _show_detail(self, piece: dict):
        """Abre modal con detalle de una pieza individual."""
        win = ctk.CTkToplevel(self)
        win.title(f"Detalle — {piece.get('part_id', '?')}")
        win.geometry("520x380")
        win.configure(fg_color=COLOR_BG)
        win.grab_set()

        _label(win, piece.get("part_id", "?"), size=13, bold=True,
               color=COLOR_ACCENT).pack(pady=(16, 4), padx=20, anchor="w")
        ctk.CTkFrame(win, height=1, fg_color=COLOR_BG3).pack(fill="x", padx=20)

        info_frame = ctk.CTkFrame(win, fg_color=COLOR_BG2, corner_radius=10)
        info_frame.pack(fill="x", padx=20, pady=12)

        dur_s = int(piece.get("duration_s", 0))
        mm, ss = divmod(dur_s, 60)
        ewh = float(piece.get("energy_wh", 0))
        ts_start = piece.get("ts_start", "?")[:19].replace("T", " ")
        ts_end   = piece.get("ts_end",   "?")[:19].replace("T", " ")

        rows = [
            ("Máquina:",    piece.get("machine_id", "?")),
            ("UID tarjeta:", piece.get("uid", "?")),
            ("Inicio:",     ts_start),
            ("Fin:",        ts_end),
            ("Duración:",   f"{mm:02d}:{ss:02d}  ({dur_s} s)"),
            ("Energía:",    f"{ewh:.3f} Wh"),
        ]
        if self._show_cost:
            rows.append(("Costo:", f"${piece.get('cost_mxn', 0):.4f} MXN"))

        for i, (label, val) in enumerate(rows):
            r = ctk.CTkFrame(info_frame, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=3)
            _label(r, label, size=12, color=COLOR_TEXT_DIM).pack(side="left")
            _label(r, val,   size=12, bold=True, color=COLOR_TEXT).pack(side="right")

        # Comparativa vs turno
        _label(win, "vs. Promedio del turno", size=12, bold=True,
               color=COLOR_ACCENT).pack(anchor="w", padx=20, pady=(4, 2))

        def _load_promedios():
            try:
                promedios = query_turno_promedios()
                avg_dur = promedios.get("avg_duration_s", 0)
                avg_ewh = promedios.get("avg_energy_wh", 0)
                diff_dur = dur_s - avg_dur
                diff_ewh = ewh - avg_ewh
                dur_txt = f"+{diff_dur:.0f}s sobre promedio" if diff_dur > 0 else f"{diff_dur:.0f}s bajo promedio"
                ewh_txt = f"+{diff_ewh:.2f}Wh sobre promedio" if diff_ewh > 0 else f"{diff_ewh:.2f}Wh bajo promedio"
                dur_color = COLOR_ALERT if diff_dur > 0 else COLOR_GREEN
                ewh_color = COLOR_ALERT if diff_ewh > 0 else COLOR_GREEN
                try:
                    win.after(0, lambda: _label(win, f"Duración: {dur_txt}", size=11,
                                                color=dur_color).pack(anchor="w", padx=28))
                    win.after(0, lambda: _label(win, f"Energía:  {ewh_txt}", size=11,
                                                color=ewh_color).pack(anchor="w", padx=28))
                except Exception:
                    pass
            except Exception:
                pass

        threading.Thread(target=_load_promedios, daemon=True).start()

        ctk.CTkButton(
            win, text="Cerrar",
            fg_color=COLOR_BG3, text_color=COLOR_TEXT,
            command=win.destroy,
        ).pack(pady=12)

    # ── Estadísticas del turno ───────────────────────────────────────────

    def _build_stats_row(self):
        self._stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._stats_frame.pack(fill="x", padx=16, pady=(4, 2))
        self._stat_lbl: dict[str, ctk.CTkLabel] = {}
        specs = [
            ("total",    "Piezas Completadas", ""),
            ("avg_dur",  "Tiempo Promedio",    "mm:ss"),
            ("avg_ewh",  "Energía Promedio",   "Wh"),
        ]
        if self._show_cost:
            specs.append(("cost",  "Costo Total Turno", "MXN"))
        for c in range(len(specs)):
            self._stats_frame.columnconfigure(c, weight=1)
        for col, (key, title, unit) in enumerate(specs):
            card = _kpi_card(self._stats_frame, title, "---", unit, COLOR_ACCENT)
            card.grid(row=0, column=col, padx=8, sticky="nsew")
            self._stat_lbl[key] = card.winfo_children()[1]

    def _update_stats(self, data: list[dict]):
        if not self.winfo_exists():
            return
        n = len(data)
        if n == 0:
            for lbl in self._stat_lbl.values():
                try: lbl.configure(text="---")
                except Exception: pass
            return
        avg_s = sum(d.get("duration_s", 0) for d in data) / n
        avg_e = sum(d.get("energy_wh",  0) for d in data) / n
        mm, ss = divmod(int(avg_s), 60)
        self._stat_lbl["total"].configure(text=str(n))
        self._stat_lbl["avg_dur"].configure(text=f"{mm:02d}:{ss:02d}")
        self._stat_lbl["avg_ewh"].configure(text=f"{avg_e:.1f}")
        if self._show_cost and "cost" in self._stat_lbl:
            tc = sum(d.get("cost_mxn", 0) for d in data)
            self._stat_lbl["cost"].configure(text=f"${tc:.2f}")

    # ── Export CSV / PDF ─────────────────────────────────────────────────

    def _export_csv(self):
        data = self._filtered_data()
        if not data:
            self._export_msg.configure(text="Sin datos para exportar", text_color=COLOR_ALERT)
            return
        fname = f"rfid_cycles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path  = tempfile.gettempdir() + "/" + fname
        fields = ["part_id", "ts_start", "ts_end", "duration_s", "energy_wh"]
        if self._show_cost:
            fields.append("cost_mxn")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)
        self._export_msg.configure(text=f"Guardado: {path}", text_color=COLOR_GREEN)

    def _export_pdf(self):
        data = self._filtered_data()
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            import subprocess, os
        except ImportError:
            self._export_msg.configure(text="reportlab no instalado — ejecute: pip install reportlab",
                                       text_color=COLOR_ALERT)
            return

        import datetime
        fname = f"trazabilidad_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path  = f"/tmp/{fname}"
        doc   = SimpleDocTemplate(path, pagesize=A4)
        styles = getSampleStyleSheet()
        story  = []

        story.append(Paragraph("Reporte de Trazabilidad RFID — Smart Manufacturing CIMA", styles["Title"]))
        story.append(Paragraph(f"Generado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Período: {self._filter}", styles["Normal"]))
        story.append(Spacer(1, 12))

        headers = ["Part ID", "Inicio", "Fin", "Duración", "Energía (Wh)"]
        if self._show_cost:
            headers.append("Costo (MXN)")
        rows = [headers]
        if data:
            for d in data[:100]:
                dur_s = int(d.get("duration_s", 0))
                mm, ss = divmod(dur_s, 60)
                row = [
                    d.get("part_id", "?"),
                    d.get("ts_start", "?")[:19].replace("T", " "),
                    d.get("ts_end",   "?")[:19].replace("T", " "),
                    f"{mm:02d}:{ss:02d}",
                    f"{d.get('energy_wh', 0):.2f}",
                ]
                if self._show_cost:
                    row.append(f"${d.get('cost_mxn', 0):.4f}")
                rows.append(row)
        else:
            rows.append(["Sin piezas en el período"] + ["---"] * (len(headers) - 1))

        t = Table(rows, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTSIZE",   (0, 0), (-1, 0), 9),
            ("FONTSIZE",   (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ("GRID",       (0, 0), (-1, -1), 0.25, colors.grey),
            ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

        n = len(data)
        avg_s = sum(d.get("duration_s", 0) for d in data) / n if n else 0
        avg_e = sum(d.get("energy_wh", 0)  for d in data) / n if n else 0
        mm2, ss2 = divmod(int(avg_s), 60)
        story.append(Paragraph(f"Total piezas: {n}  |  Duración promedio: {mm2:02d}:{ss2:02d}  |  Energía promedio: {avg_e:.2f} Wh", styles["Normal"]))
        if self._show_cost:
            total_cost = sum(d.get("cost_mxn", 0) for d in data)
            story.append(Paragraph(f"Costo total: ${total_cost:.4f} MXN", styles["Normal"]))

        doc.build(story)
        self._export_msg.configure(text=f"PDF guardado: {path}", text_color=COLOR_GREEN)
        try:
            subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    # ── MQTT ─────────────────────────────────────────────────────────────

    def _connect_mqtt(self):
        try:
            try:
                client = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2)
                client.on_connect = self._on_connect_v2
            except AttributeError:
                client = mqtt_lib.Client()
                client.on_connect = self._on_connect_v1
            client.username_pw_set(MQTT_APP_USER, MQTT_APP_PASS)
            client.on_message = self._on_message
            client.connect_async(MQTT_BROKER, MQTT_PORT_LOCAL, 60)
            client.loop_start()
            self._mqtt_client = client
        except Exception as exc:
            log.warning("TrazabilidadPanel MQTT: %s", exc)

    def _on_connect_v2(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe("cima/rfid/scan")
            client.subscribe("cima/machines/+/energy")

    def _on_connect_v1(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("cima/rfid/scan")
            client.subscribe("cima/machines/+/energy")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = getattr(msg, 'topic', '') or ''
            if 'energy' in topic:
                # Acumular energía durante ciclo activo
                if self._active:
                    ewh = float(payload.get('energy_kwh', 0) or 0) * 1000
                    self._banner_energy_wh += ewh
                return
            if payload.get("uid"):
                self._q.put_nowait(payload)
        except Exception as exc:
            log.warning("TrazabilidadPanel msg: %s", exc)

    def _set_banner_active(self, payload: dict):
        """Actualiza el banner a estado ACTIVO — debe llamarse desde hilo principal."""
        if not self.winfo_exists():
            return
        pid = payload.get("part_id", "?")
        self._banner.configure(
            text=f"🟢 CICLO ACTIVO — {pid} — 00:00 — 0.0 Wh",
            text_color=COLOR_GREEN,
            fg_color="#1a3a2e",
        )

    def _set_banner_idle(self):
        """Actualiza el banner a estado INACTIVO — debe llamarse desde hilo principal."""
        if not self.winfo_exists():
            return
        self._banner.configure(
            text="⚪ Sin ciclo activo — Acerque tarjeta RFID para iniciar",
            text_color=COLOR_TEXT_DIM,
            fg_color=COLOR_BG2,
        )

    def _poll_queue(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                payload = self._q.get_nowait()
                event   = payload.get("event", "")
                if event == "start":
                    self._active           = payload
                    self._start_epoch      = time.time()
                    self._banner_energy_wh = 0.0
                    self._set_banner_active(payload)  # actualización inmediata
                elif event == "stop":
                    self._active = None
                    self._set_banner_idle()           # actualización inmediata
                    threading.Thread(target=self._load_data, daemon=True).start()
        except queue.Empty:
            pass
        self.after(500, self._poll_queue)

    # ── Carga de datos ───────────────────────────────────────────────────

    def _load_data(self):
        data     = query_rfid_cycles(limit=50)
        self._all_cycles = data
        filtered = self._filtered_data()
        try:
            self.after(0, self._render_table, filtered)
            self.after(0, self._update_stats,  filtered)
        except Exception:
            pass

    def destroy(self):
        if self._mqtt_client:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception:
                pass
        super().destroy()


# ---------------------------------------------------------------------------
# Dashboard Admin
# ---------------------------------------------------------------------------

class DashboardAdmin(ctk.CTkFrame):
    """Panel completo de administrador: Salud | CIMA | Celda 3105 | Costos MXN | Usuarios | Auditoría."""

    def __init__(self, master, health_checker: HealthChecker, **kw):
        super().__init__(master, fg_color=COLOR_BG, **kw)
        self._hc = health_checker

        self._tabs = _make_tabview(self)
        self._tabs.pack(fill="both", expand=True, padx=8, pady=8)

        for tab in ("Salud", "CIMA", "Celda 3105", "Costos MXN", "Trazabilidad", "Usuarios", "Auditoría"):
            self._tabs.add(tab)

        self._build_salud_tab()
        self._build_cima_tab()
        self._build_celda_tab()
        self._build_costos_tab()
        self._build_trazabilidad_tab()
        self._build_users_tab()
        self._build_audit_tab()

        threading.Thread(target=self._load_kpis, daemon=True).start()

    # ---- Salud ----

    def _build_salud_tab(self):
        tab = self._tabs.tab("Salud")
        _SaludTab(tab, health_checker=self._hc).pack(fill="both", expand=True)

    # ---- CIMA — gráficas energía planta 1 ----

    def _build_cima_tab(self):
        tab = self._tabs.tab("CIMA")
        _section_title(tab, "Energía en Tiempo Real — Planta 1 (CIMA / Torno)")

        kpi_row = ctk.CTkFrame(tab, fg_color="transparent")
        kpi_row.pack(fill="x", padx=16, pady=8)
        for c in range(3):
            kpi_row.columnconfigure(c, weight=1)
        self._cima_kpi: dict[str, ctk.CTkLabel] = {}
        for col, (key, title, unit, color) in enumerate([
            ("power",  "Potencia Actual", "W",   COLOR_ACCENT),
            ("irms",   "Corriente RMS",   "A",   COLOR_WARN),
            ("kwh",    "Energía Turno",   "kWh", COLOR_GREEN),
        ]):
            card = _kpi_card(kpi_row, title, "---", unit, color)
            card.grid(row=0, column=col, padx=8, sticky="nsew")
            self._cima_kpi[key] = card.winfo_children()[1]

        chart_frame = ctk.CTkFrame(tab, fg_color="transparent")
        chart_frame.pack(fill="both", expand=True, padx=16, pady=4)
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        chart_frame.rowconfigure(1, weight=1)
        RealtimeEnergyChart(
            chart_frame, field="power_w", ylabel="Potencia (W)", line_color=COLOR_ACCENT,
            machine_id=MACHINE_ID_PLANTA1,
        ).grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        RealtimeEnergyChart(
            chart_frame, field="irms_a", ylabel="Corriente Irms (A)", line_color=COLOR_WARN,
            machine_id=MACHINE_ID_PLANTA1,
        ).grid(row=1, column=0, sticky="nsew")

        self._start_cima_kpi_refresh()

    def _start_cima_kpi_refresh(self):
        threading.Thread(target=self._load_cima_kpis, daemon=True).start()

    def _load_cima_kpis(self):
        latest = query_latest_power(machine_id=MACHINE_ID_PLANTA1)
        data   = query_energy_realtime(1, machine_id=MACHINE_ID_PLANTA1)
        kwh    = data[-1]["energy_kwh"] if data else 0.0
        try:
            self.after(0, self._update_cima_kpis, latest, kwh)
        except Exception:
            pass

    def _update_cima_kpis(self, latest: dict, kwh: float):
        if not self.winfo_exists():
            return
        pw = latest.get("power_w", 0)
        ir = latest.get("irms_a", 0)
        self._cima_kpi["power"].configure(text=f"{pw:.0f}")
        self._cima_kpi["irms"].configure(text=f"{ir:.3f}")
        self._cima_kpi["kwh"].configure(text=f"{kwh:.4f}")
        self.after(5000, self._start_cima_kpi_refresh)

    # ---- Celda 3105 ----

    def _build_celda_tab(self):
        tab = self._tabs.tab("Celda 3105")
        Celda3105Panel(tab).pack(fill="both", expand=True)

    # ---- Costos MXN ----

    def _build_costos_tab(self):
        tab = self._tabs.tab("Costos MXN")
        _section_title(tab, f"KPIs Monetarios — Últimas 24h  (tarifa: ${TARIFA_KWH_MXN:.2f} MXN/kWh CFE DAC)")

        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=16)
        for c in range(4):
            grid.columnconfigure(c, weight=1)
        self._kpi_vals: dict[str, ctk.CTkLabel] = {}
        for col, (key, title, unit, color) in enumerate([
            ("kwh",    "Consumo Total",      "kWh", COLOR_ACCENT),
            ("costo",  "Costo Energético",   "MXN", COLOR_WARN),
            ("ahorro", "Ahorro vs Baseline", "MXN", COLOR_GREEN),
            ("roi",    "ROI Estimado",       "%",   COLOR_ACCENT),
        ]):
            card = _kpi_card(grid, title, "---", unit, color)
            card.grid(row=0, column=col, padx=8, sticky="nsew")
            self._kpi_vals[key] = card.winfo_children()[1]

        cfg_row = ctk.CTkFrame(tab, fg_color="transparent")
        cfg_row.pack(fill="x", padx=16, pady=8)
        _label(cfg_row, "Tarifa (MXN/kWh):", size=13).pack(side="left", padx=8)
        self._tarifa_entry = ctk.CTkEntry(cfg_row, width=80)
        self._tarifa_entry.insert(0, str(TARIFA_KWH_MXN))
        self._tarifa_entry.pack(side="left")
        ctk.CTkButton(
            cfg_row, text="Recalcular",
            fg_color=COLOR_ACCENT, text_color="#000000",
            command=lambda: threading.Thread(target=self._load_kpis, daemon=True).start(),
        ).pack(side="left", padx=8)

        _section_title(tab, "Registro de Consumo 24h")
        info = _label(tab, "Cargando datos de InfluxDB...", size=13, color=COLOR_TEXT_DIM)
        info.pack(pady=4)
        ctk.CTkButton(
            tab, text="Refrescar tabla",
            fg_color=COLOR_BG3,
            command=lambda: threading.Thread(
                target=self._load_energy_table, args=(tab, info), daemon=True
            ).start(),
        ).pack(pady=2)
        threading.Thread(
            target=self._load_energy_table, args=(tab, info), daemon=True
        ).start()

    def _load_kpis(self):
        try:
            data = query_energy_cost_admin()
            self.after(0, self._update_kpis, data)
        except Exception as exc:
            log.warning("KPI load: %s", exc)

    def _update_kpis(self, data: dict):
        if not self.winfo_exists():
            return
        try:
            self._kpi_vals["kwh"].configure(text=f"{data['total_kwh']:,.3f}")
            self._kpi_vals["costo"].configure(text=f"${data['costo_mxn']:,.2f}")
            self._kpi_vals["ahorro"].configure(text=f"${data['ahorro_estimado_mxn']:,.2f}")
            self._kpi_vals["roi"].configure(text=f"{data['roi_pct']:.1f}")
        except Exception as exc:
            log.warning("KPI update: %s", exc)

    def _load_energy_table(self, tab, info_label):
        data = query_energy_24h()
        self.after(0, self._render_energy_table, tab, info_label, data)

    def _render_energy_table(self, tab, info_label, data: list[dict]):
        if not self.winfo_exists():
            return
        info_label.configure(
            text=f"{len(data)} registros — último: {data[-1]['time'][:19] if data else 'N/A'}"
        )
        frame = ctk.CTkScrollableFrame(tab, fg_color=COLOR_BG2, height=260)
        frame.pack(fill="both", expand=True, padx=16, pady=4)
        headers = ["Tiempo", "Máquina", "Potencia (W)", "Corriente (A)", "Energía (kWh)"]
        for col, h in enumerate(headers):
            _label(frame, h, size=11, bold=True, color=COLOR_ACCENT).grid(
                row=0, column=col, padx=8, pady=4, sticky="w"
            )
        for row_i, rec in enumerate(data[-50:], start=1):
            vals = [
                rec["time"][11:19], rec["machine_id"],
                f"{rec['power_w']:.1f}", f"{rec['irms_a']:.3f}", f"{rec['energy_kwh']:.4f}",
            ]
            for col, v in enumerate(vals):
                _label(frame, v, size=11, color=COLOR_TEXT).grid(
                    row=row_i, column=col, padx=8, pady=2, sticky="w"
                )

    # ---- Trazabilidad (admin ve columna de costo) ----

    def _build_trazabilidad_tab(self):
        tab = self._tabs.tab("Trazabilidad")
        TrazabilidadPanel(tab, rol="admin").pack(fill="both", expand=True)

    # ---- Usuarios ----

    def _build_users_tab(self):
        tab = self._tabs.tab("Usuarios")
        _section_title(tab, "Gestión de Usuarios")
        self._user_frame = ctk.CTkScrollableFrame(tab, fg_color=COLOR_BG2, height=240)
        self._user_frame.pack(fill="x", padx=16, pady=8)
        self._refresh_user_table()

        _section_title(tab, "Agregar Usuario")
        form = ctk.CTkFrame(tab, fg_color=COLOR_BG2, corner_radius=10)
        form.pack(fill="x", padx=16, pady=8)
        ff = ctk.CTkFrame(form, fg_color="transparent")
        ff.pack(fill="x", padx=12, pady=12)

        _label(ff, "Usuario:", size=12).grid(row=0, column=0, padx=6, sticky="e")
        self._new_user = ctk.CTkEntry(ff, width=120)
        self._new_user.grid(row=0, column=1, padx=6)

        _label(ff, "PIN:", size=12).grid(row=0, column=2, padx=6, sticky="e")
        self._new_pin = ctk.CTkEntry(ff, width=80, show="*")
        self._new_pin.grid(row=0, column=3, padx=6)

        _label(ff, "Rol:", size=12).grid(row=0, column=4, padx=6, sticky="e")
        self._new_rol = ctk.CTkOptionMenu(
            ff, values=["planta1", "planta2", "admin"],
            fg_color=COLOR_BG3, button_color=COLOR_ACCENT, text_color=COLOR_TEXT,
        )
        self._new_rol.grid(row=0, column=5, padx=6)

        _label(ff, "Huella ID:", size=12).grid(row=0, column=6, padx=6, sticky="e")
        self._new_hid = ctk.CTkEntry(ff, width=60)
        self._new_hid.insert(0, "6")
        self._new_hid.grid(row=0, column=7, padx=6)

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(pady=8)
        ctk.CTkButton(
            btn_row, text="Crear Usuario",
            fg_color=COLOR_ACCENT, text_color="#000000",
            command=self._create_user,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_row, text="Enrollar Huella (JM-101B)",
            fg_color=COLOR_BG3,
            command=self._enroll_fingerprint_dialog,
        ).pack(side="left", padx=8)

        self._user_msg = _label(tab, "", size=12, color=COLOR_ACCENT)
        self._user_msg.pack()

    def _refresh_user_table(self):
        for w in self._user_frame.winfo_children():
            w.destroy()
        for col, h in enumerate(["ID", "Usuario", "Rol", "Huella ID", "Activo", "Acción"]):
            _label(self._user_frame, h, size=11, bold=True,
                   color=COLOR_ACCENT).grid(row=0, column=col, padx=8, pady=4, sticky="w")
        for row_i, u in enumerate(get_all_users(), start=1):
            for col, v in enumerate([str(u["id"]), u["username"], u["rol"],
                                      str(u["huella_id"]), "Sí" if u["activo"] else "No"]):
                _label(self._user_frame, v, size=11).grid(
                    row=row_i, column=col, padx=8, pady=2, sticky="w"
                )
            ctk.CTkButton(
                self._user_frame, text="Eliminar", width=70,
                fg_color=COLOR_ALERT, text_color="#ffffff",
                command=lambda uname=u["username"]: self._delete_user(uname),
            ).grid(row=row_i, column=5, padx=8, pady=2)

    def _create_user(self):
        try:
            hid = int(self._new_hid.get())
        except ValueError:
            self._user_msg.configure(text="Huella ID debe ser número", text_color=COLOR_ALERT)
            return
        ok, msg = add_user(self._new_user.get(), self._new_pin.get(), self._new_rol.get(), hid)
        self._user_msg.configure(text=msg, text_color=COLOR_ACCENT if ok else COLOR_ALERT)
        if ok:
            self._refresh_user_table()

    def _delete_user(self, username: str):
        delete_user(username)
        self._user_msg.configure(text=f"'{username}' eliminado", text_color=COLOR_WARN)
        self._refresh_user_table()

    def _enroll_fingerprint_dialog(self):
        try:
            hid = int(self._new_hid.get())
        except ValueError:
            self._user_msg.configure(text="Ingresa un Huella ID numérico primero",
                                     text_color=COLOR_ALERT)
            return
        self._user_msg.configure(text="Enrollando — coloca el dedo...", text_color=COLOR_WARN)
        def _run():
            ok, msg = enroll_fingerprint(hid)
            self.after(0, lambda: self._user_msg.configure(
                text=msg, text_color=COLOR_ACCENT if ok else COLOR_ALERT
            ))
        threading.Thread(target=_run, daemon=True).start()

    # ---- Auditoría ----

    def _build_audit_tab(self):
        tab = self._tabs.tab("Auditoría")
        _section_title(tab, "Registro de Accesos")
        frame = ctk.CTkScrollableFrame(tab, fg_color=COLOR_BG2, height=460)
        frame.pack(fill="both", expand=True, padx=16, pady=8)
        for col, h in enumerate(["Timestamp", "Usuario", "Acción", "Éxito", "IP", "Detalle"]):
            _label(frame, h, size=11, bold=True,
                   color=COLOR_ACCENT).grid(row=0, column=col, padx=8, pady=4, sticky="w")
        for row_i, entry in enumerate(get_audit_logs(80), start=1):
            color = COLOR_GREEN if entry["exitoso"] else COLOR_ALERT
            vals = [
                entry["timestamp"][:19], entry["username"], entry["accion"],
                "✓" if entry["exitoso"] else "✗",
                entry.get("ip", ""), entry.get("detalle", ""),
            ]
            for col, v in enumerate(vals):
                _label(frame, str(v), size=10,
                       color=color if col == 3 else COLOR_TEXT).grid(
                    row=row_i, column=col, padx=8, pady=1, sticky="w"
                )
        ctk.CTkButton(
            tab, text="Refrescar logs", fg_color=COLOR_BG3,
            command=self._build_audit_tab,
        ).pack(pady=4)


# ---------------------------------------------------------------------------
# Dashboard Planta 1 — Torno / Fresadora
# ---------------------------------------------------------------------------

class DashboardPlanta1(ctk.CTkFrame):
    """Vista con tabs: CIMA (energía tiempo real) | Trazabilidad | Salud."""

    def __init__(self, master, health_checker: HealthChecker | None = None, **kw):
        super().__init__(master, fg_color=COLOR_BG, **kw)
        self._hc = health_checker

        self._tabs = _make_tabview(self)
        self._tabs.pack(fill="both", expand=True, padx=8, pady=8)

        for tab in ("CIMA", "Trazabilidad", "Salud"):
            self._tabs.add(tab)

        self._build_cima_tab()
        self._build_trazabilidad_tab()
        self._build_salud_tab()

    # ---- CIMA ----

    def _build_cima_tab(self):
        tab = self._tabs.tab("CIMA")
        _section_title(tab, "Energía en Tiempo Real — Planta 1 (CIMA / Torno)")

        kpi_row = ctk.CTkFrame(tab, fg_color="transparent")
        kpi_row.pack(fill="x", padx=16, pady=8)
        for c in range(4):
            kpi_row.columnconfigure(c, weight=1)

        self._kpi_labels: dict[str, ctk.CTkLabel] = {}
        for col, (key, title, unit, color) in enumerate([
            ("power",  "Potencia Actual", "W",   COLOR_ACCENT),
            ("irms",   "Corriente RMS",   "A",   COLOR_WARN),
            ("kwh",    "Energía Turno",   "kWh", COLOR_GREEN),
            ("estado", "Estado Ciclo",    "",    COLOR_TEXT),
        ]):
            card = _kpi_card(kpi_row, title, "---", unit, color)
            card.grid(row=0, column=col, padx=8, sticky="nsew")
            self._kpi_labels[key] = card.winfo_children()[1]

        chart_frame = ctk.CTkFrame(tab, fg_color="transparent")
        chart_frame.pack(fill="both", expand=True, padx=16, pady=4)
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        chart_frame.rowconfigure(1, weight=1)

        RealtimeEnergyChart(
            chart_frame, field="power_w",
            ylabel="Potencia (W)", line_color=COLOR_ACCENT,
            machine_id=MACHINE_ID_PLANTA1,
        ).grid(row=0, column=0, sticky="nsew", pady=(0, 4))

        RealtimeEnergyChart(
            chart_frame, field="irms_a",
            ylabel="Corriente Irms (A)", line_color=COLOR_WARN,
            machine_id=MACHINE_ID_PLANTA1,
        ).grid(row=1, column=0, sticky="nsew")

        threading.Thread(target=self._load_kpis, daemon=True).start()

    def _load_kpis(self):
        latest = query_latest_power(machine_id=MACHINE_ID_PLANTA1)
        data   = query_energy_realtime(1, machine_id=MACHINE_ID_PLANTA1)
        kwh    = data[-1]["energy_kwh"] if data else 0.0
        try:
            self.after(0, self._update_kpis, latest, kwh)
        except Exception:
            pass

    def _update_kpis(self, latest: dict, kwh: float):
        if not self.winfo_exists():
            return
        pw = latest.get("power_w", 0)
        ir = latest.get("irms_a", 0)
        self._kpi_labels["power"].configure(text=f"{pw:.0f}")
        self._kpi_labels["irms"].configure(text=f"{ir:.3f}")
        self._kpi_labels["kwh"].configure(text=f"{kwh:.4f}")
        self._kpi_labels["estado"].configure(
            text="ACTIVO" if pw > 50 else "INACTIVO",
            text_color=COLOR_GREEN if pw > 50 else COLOR_ALERT,
        )
        self.after(5000, lambda: threading.Thread(
            target=self._load_kpis, daemon=True
        ).start())

    # ---- Trazabilidad (planta1: sin columna de costo) ----

    def _build_trazabilidad_tab(self):
        tab = self._tabs.tab("Trazabilidad")
        TrazabilidadPanel(tab, rol="planta1").pack(fill="both", expand=True)

    # ---- Salud ----

    def _build_salud_tab(self):
        tab = self._tabs.tab("Salud")
        _SaludTab(tab, health_checker=self._hc).pack(fill="both", expand=True)


# ---------------------------------------------------------------------------
# Celda3105Panel — panel PLC S7-1200 tiempo real (MQTT + InfluxDB)
# ---------------------------------------------------------------------------

class Celda3105Panel(ctk.CTkFrame):
    """
    Dashboard Celda 3105 con datos en tiempo real del PLC S7-1200
    vía MQTT (topic celda3105/plc). Funciona sin PLC — muestra banner
    amarillo si sin datos >10 s; banner rojo parpadeante si killswitch activo.
    """

    def __init__(self, master, **kw):
        super().__init__(master, fg_color=COLOR_BG, **kw)
        self._data: dict        = {}
        self._last_ts: float    = 0.0
        self._blink: bool       = False
        self._prev_piezas: int  = 0
        self._ops: list[dict]   = []
        self._q: queue.Queue    = queue.Queue()
        self._mqtt_client       = None
        self._build_ui()
        self._connect_mqtt()
        self._poll()

    # ── UI BUILD ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Status bar ──
        topbar = ctk.CTkFrame(self, fg_color=COLOR_BG3, height=28, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self._lbl_live = _label(topbar, "● Sin datos reales", size=11, color=COLOR_WARN)
        self._lbl_live.pack(side="right", padx=12, pady=4)

        # ── Banners container (always present, size = sum of visible banners) ──
        self._banners = ctk.CTkFrame(self, fg_color="transparent")
        self._banners.pack(fill="x")

        self._banner_warn = ctk.CTkFrame(self._banners, fg_color="#3a2a00", corner_radius=0, height=30)
        self._lbl_bwarn = _label(self._banner_warn, "", size=11, bold=True, color=COLOR_WARN)
        self._lbl_bwarn.pack(pady=5)

        self._banner_emer = ctk.CTkFrame(self._banners, fg_color=COLOR_ALERT, corner_radius=0, height=30)
        self._lbl_bemer = _label(self._banner_emer,
                                 "EMERGENCIA ACTIVA — KILLSWITCH PRESIONADO",
                                 size=11, bold=True, color="#ffffff")
        self._lbl_bemer.pack(pady=5)

        # ── ROW 1: 4 KPI cards ──
        kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        kpi_row.pack(fill="x", padx=8, pady=(8, 4))
        for c in range(4):
            kpi_row.columnconfigure(c, weight=1)

        self._kpi: dict[str, ctk.CTkLabel] = {}
        for col, (key, title, unit, color) in enumerate([
            ("estado",  "Estado PLC",        "",    COLOR_GREEN),
            ("piezas",  "Piezas procesadas", "uds", COLOR_ACCENT),
            ("ciclo",   "Tiempo de ciclo",   "s",   COLOR_WARN),
            ("oee",     "OEE",               "%",   COLOR_GREEN),
        ]):
            card = _kpi_card(kpi_row, title, "—", unit, color)
            card.grid(row=0, column=col, padx=5, sticky="nsew")
            self._kpi[key] = card.winfo_children()[1]

        # ── ROW 2: 3 columns ──
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=4)
        row2.columnconfigure(0, weight=2)
        row2.columnconfigure(1, weight=5)
        row2.columnconfigure(2, weight=3)

        # Left — señales PLC
        left = ctk.CTkFrame(row2, fg_color=COLOR_BG2, corner_radius=10)
        left.grid(row=0, column=0, padx=(0, 4), sticky="nsew")
        _label(left, "Señales PLC", size=11, bold=True, color=COLOR_ACCENT).pack(
            anchor="w", padx=10, pady=(8, 4))
        self._sigs: dict[str, ctk.CTkLabel] = {}
        for key, label in [
            ("emergencia", "Emergencia"),
            ("modo_auto",  "Modo automático"),
            ("cobot",      "Cobot activo"),
            ("cognex",     "Sensor entrada"),
            ("semaforo",   "Semáforo celda"),
        ]:
            r = ctk.CTkFrame(left, fg_color="transparent")
            r.pack(fill="x", padx=10, pady=1)
            _label(r, label, size=10, color=COLOR_TEXT_DIM).pack(side="left")
            ind = _label(r, "● —", size=10, color=COLOR_TEXT_DIM)
            ind.pack(side="right")
            self._sigs[key] = ind

        # Center — flujo producción
        center = ctk.CTkFrame(row2, fg_color=COLOR_BG2, corner_radius=10)
        center.grid(row=0, column=1, padx=4, sticky="nsew")
        _label(center, "Línea de producción", size=11, bold=True, color=COLOR_ACCENT).pack(
            anchor="w", padx=10, pady=(8, 4))
        self._fnodes: dict[str, ctk.CTkLabel] = {}

        rowA = ctk.CTkFrame(center, fg_color="transparent")
        rowA.pack(fill="x", padx=6, pady=(0, 2))
        for key, txt in [("entrada","ENTRADA"),("banda1","BANDA1"),
                          ("taladro1","TALADRO1"),("banda2","BANDA2"),("martillo1","MARTLLO1")]:
            self._mk_fnode(rowA, key, txt)

        rowB = ctk.CTkFrame(center, fg_color="transparent")
        rowB.pack(fill="x", padx=6, pady=2)
        for key, txt in [("banda3","BANDA3"),("taladro2","TALADRO2"),
                          ("banda4","BANDA4"),("martillo2","MARTLLO2"),("estampado","ESTAMPADO")]:
            self._mk_fnode(rowB, key, txt)

        rowC = ctk.CTkFrame(center, fg_color="transparent")
        rowC.pack(fill="x", padx=6, pady=(2, 8))
        for key, txt in [("cognex_cam","COGNEX"), ("salida","SALIDA")]:
            self._mk_fnode(rowC, key, txt)

        # Right — últimas operaciones
        right = ctk.CTkFrame(row2, fg_color=COLOR_BG2, corner_radius=10)
        right.grid(row=0, column=2, padx=(4, 0), sticky="nsew")
        _label(right, "Últimas operaciones", size=11, bold=True, color=COLOR_ACCENT).pack(
            anchor="w", padx=10, pady=(8, 4))
        self._ops_frame = ctk.CTkScrollableFrame(right, fg_color=COLOR_BG, height=150)
        self._ops_frame.pack(fill="x", padx=8, pady=(0, 8))
        self._render_ops([])

        # ── ROW 3: Quality Gate ──
        qg = ctk.CTkFrame(self, fg_color=COLOR_BG2, corner_radius=10)
        qg.pack(fill="x", padx=8, pady=(4, 8))
        _label(qg, "Quality Gate", size=11, bold=True, color=COLOR_ACCENT).pack(
            anchor="w", padx=10, pady=(8, 2))
        g = ctk.CTkFrame(qg, fg_color="transparent")
        g.pack(fill="x", padx=10, pady=(0, 10))
        g.columnconfigure(1, weight=1)

        _label(g, "Aprobadas", size=10, color=COLOR_GREEN).grid(
            row=0, column=0, sticky="w", padx=(0, 8))
        self._bar_ok = ctk.CTkProgressBar(g, fg_color=COLOR_BG3, progress_color=COLOR_GREEN, height=14)
        self._bar_ok.set(0)
        self._bar_ok.grid(row=0, column=1, sticky="ew")
        self._lbl_ok = _label(g, "0  (0%)", size=10, color=COLOR_GREEN)
        self._lbl_ok.grid(row=0, column=2, padx=(8, 0))

        _label(g, "Rechazadas", size=10, color=COLOR_ALERT).grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self._bar_nok = ctk.CTkProgressBar(g, fg_color=COLOR_BG3, progress_color=COLOR_ALERT, height=14)
        self._bar_nok.set(0)
        self._bar_nok.grid(row=1, column=1, sticky="ew", pady=(4, 0))
        self._lbl_nok = _label(g, "0  (0%)", size=10, color=COLOR_ALERT)
        self._lbl_nok.grid(row=1, column=2, padx=(8, 0), pady=(4, 0))

    def _mk_fnode(self, parent, key: str, text: str):
        box = ctk.CTkFrame(parent, fg_color=COLOR_BG3, corner_radius=6, width=74, height=32)
        box.pack(side="left", padx=2, pady=2)
        box.pack_propagate(False)
        lbl = _label(box, text, size=8, bold=True, color=COLOR_TEXT_DIM)
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        self._fnodes[key] = lbl

    # ── MQTT ─────────────────────────────────────────────────────────────────

    def _connect_mqtt(self):
        try:
            try:
                client = mqtt_lib.Client(mqtt_lib.CallbackAPIVersion.VERSION2)
                client.on_connect = self._on_connect_v2
            except AttributeError:
                client = mqtt_lib.Client()
                client.on_connect = self._on_connect_v1
            client.username_pw_set(MQTT_APP_USER, MQTT_APP_PASS)
            client.on_message = self._on_message
            client.connect_async(MQTT_BROKER, MQTT_PORT_LOCAL, 60)
            client.loop_start()
            self._mqtt_client = client
        except Exception as exc:
            log.warning("Celda3105Panel MQTT: %s", exc)

    def _on_connect_v2(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(MQTT_TOPIC_CELDA)

    def _on_connect_v1(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC_CELDA)

    def _on_message(self, client, userdata, msg):
        try:
            self._q.put_nowait(json.loads(msg.payload.decode()))
        except Exception as exc:
            log.warning("Celda3105Panel msg: %s", exc)

    # ── POLL LOOP ────────────────────────────────────────────────────────────

    def _poll(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                data = self._q.get_nowait()
                new_piezas = data.get("kpis", {}).get("piezas_procesadas", 0)
                if new_piezas > self._prev_piezas:
                    op = {
                        "num":      new_piezas,
                        "tiempo_s": data.get("kpis", {}).get("tiempo_ciclo_s", 0),
                        "aprobada": data.get("cognex", {}).get("aprobada", False),
                        "hora":     datetime.now().strftime("%H:%M:%S"),
                    }
                    self._ops.insert(0, op)
                    self._ops = self._ops[:10]
                    self.after(0, self._render_ops, list(self._ops))
                self._prev_piezas = new_piezas
                self._data = data
                self._last_ts = time.time()
        except queue.Empty:
            pass
        self._update_ui()
        self.after(500, self._poll)

    # ── UI UPDATE ─────────────────────────────────────────────────────────────

    def _update_ui(self):
        if not self.winfo_exists():
            return
        now = time.time()
        has_data = bool(self._data) and (now - self._last_ts) < 60

        # Live indicator
        if not self._data:
            self._lbl_live.configure(text="● Sin datos reales", text_color=COLOR_WARN)
        elif now - self._last_ts > 10:
            self._lbl_live.configure(text="● Sin conexión", text_color=COLOR_ALERT)
        else:
            self._lbl_live.configure(text="● En vivo", text_color=COLOR_GREEN)

        # No-data banner
        if self._data and now - self._last_ts > 10:
            ts_str = datetime.fromtimestamp(self._last_ts).strftime("%H:%M:%S") if self._last_ts else "—"
            self._lbl_bwarn.configure(
                text=f"⚠  Sin conexión con PLC — Último dato: {ts_str}")
            if not self._banner_warn.winfo_ismapped():
                self._banner_warn.pack(fill="x")
        else:
            self._banner_warn.pack_forget()

        # Emergency banner (blink)
        if self._data.get("killswitch"):
            self._blink = not self._blink
            self._banner_emer.configure(fg_color=COLOR_ALERT if self._blink else "#aa0000")
            if not self._banner_emer.winfo_ismapped():
                self._banner_emer.pack(fill="x")
        else:
            self._banner_emer.pack_forget()

        if not has_data:
            self._set_no_data()
            return

        d = self._data
        k = d.get("kpis", {})

        # ── KPI cards ──
        auto = d.get("modo_auto", False)
        emer = d.get("emergencia", False)
        estado_txt   = "AUTOMÁTICO" if auto else ("EMERGENCIA" if emer else "MANUAL")
        estado_color = COLOR_GREEN if auto else COLOR_ALERT
        self._kpi["estado"].configure(text=estado_txt, text_color=estado_color)
        self._kpi["piezas"].configure(text=str(k.get("piezas_procesadas", 0)))
        self._kpi["ciclo"].configure(
            text=f"{k.get('tiempo_ciclo_promedio_s', 0):.1f}")
        oee = k.get("oee", 0)
        self._kpi["oee"].configure(
            text=f"{oee:.1f}",
            text_color=COLOR_GREEN if oee >= 85 else (COLOR_WARN if oee >= 70 else COLOR_ALERT))

        # ── Signals ──
        def _sig(val, on_t, off_t, on_c, off_c):
            return (on_t, on_c) if val else (off_t, off_c)

        kill = d.get("killswitch", False)
        self._sigs["emergencia"].configure(*_sig(kill, "● ACTIVA", "● OK", COLOR_ALERT, COLOR_GREEN))
        self._sigs["modo_auto"].configure(
            *_sig(auto, "● Automático", "● Manual/Paro", COLOR_GREEN, COLOR_WARN))
        self._sigs["cobot"].configure(
            *_sig(d.get("cobot_activo"), "● Activo", "● Inactivo", COLOR_GREEN, COLOR_TEXT_DIM))
        self._sigs["cognex"].configure(
            *_sig(d.get("cognex", {}).get("foto"), "● Disparando", "● Espera", COLOR_ACCENT, COLOR_TEXT_DIM))
        sem = d.get("semaforo", {})
        sem_icon = "🟢" if sem.get("verde") else ("🔴" if sem.get("rojo") else ("🔵" if sem.get("azul") else "⚪"))
        self._sigs["semaforo"].configure(text=sem_icon, text_color=COLOR_TEXT)

        # ── Flow nodes ──
        b = d.get("bandas", {})
        e = d.get("estaciones", {})
        cog = d.get("cognex", {})
        self._fn("entrada",    auto and any(b.values()))
        self._fn("banda1",     b.get("banda1"))
        self._fn("taladro1",   e.get("taladro1"))
        self._fn("banda2",     b.get("banda2"))
        self._fn("martillo1",  e.get("martillo1"))
        self._fn("banda3",     b.get("banda3"))
        self._fn("taladro2",   e.get("taladro2"))
        self._fn("banda4",     b.get("banda4"))
        self._fn("martillo2",  e.get("martillo2"))
        stamp_txt = "ESTAMP ↓" if d.get("estampado_down") else (
                    "ESTAMP ↑" if d.get("estampado_up") else "ESTAMPADO")
        self._fn("estampado",  d.get("estampado_down") or d.get("estampado_up"), stamp_txt)
        self._fn("cognex_cam", cog.get("foto"))
        self._fn("salida",     cog.get("aprobada"))

        # ── Quality Gate ──
        ok  = k.get("piezas_aprobadas",  0)
        nok = k.get("piezas_rechazadas", 0)
        total = ok + nok
        ok_r  = ok  / total if total > 0 else 0
        nok_r = nok / total if total > 0 else 0
        self._bar_ok.set(ok_r)
        self._bar_nok.set(nok_r)
        self._lbl_ok.configure(text=f"{ok}  ({ok_r*100:.1f}%)")
        self._lbl_nok.configure(text=f"{nok}  ({nok_r*100:.1f}%)")

    def _set_no_data(self):
        for lbl in self._kpi.values():
            lbl.configure(text="—", text_color=COLOR_TEXT_DIM)
        for lbl in self._sigs.values():
            lbl.configure(text="● —", text_color=COLOR_TEXT_DIM)
        for key in list(self._fnodes):
            self._fn(key, False)

    def _fn(self, key: str, active: bool, text: str | None = None):
        lbl = self._fnodes.get(key)
        if lbl is None or not lbl.winfo_exists():
            return
        if text:
            lbl.configure(text=text)
        lbl.configure(text_color=COLOR_GREEN if active else COLOR_TEXT_DIM)
        try:
            lbl.master.configure(fg_color="#193219" if active else COLOR_BG3)
        except Exception:
            pass

    def _render_ops(self, ops: list[dict]):
        if not self.winfo_exists():
            return
        for w in self._ops_frame.winfo_children():
            w.destroy()
        # Header
        hdr = ctk.CTkFrame(self._ops_frame, fg_color="transparent")
        hdr.pack(fill="x")
        for col, txt in enumerate(["#", "Dur(s)", "Result", "Hora"]):
            hdr.columnconfigure(col, weight=1)
            _label(hdr, txt, size=9, bold=True, color=COLOR_TEXT_DIM).grid(
                row=0, column=col, padx=2, sticky="w")
        if not ops:
            _label(self._ops_frame, "Sin operaciones registradas",
                   size=10, color=COLOR_TEXT_DIM).pack(pady=8)
            return
        for op in ops:
            row = ctk.CTkFrame(self._ops_frame, fg_color="transparent")
            row.pack(fill="x")
            for col, w in enumerate([1, 1, 1, 1]):
                row.columnconfigure(col, weight=w)
            ok = op.get("aprobada", False)
            c  = COLOR_GREEN if ok else COLOR_ALERT
            for col, txt in enumerate([
                str(op.get("num", "?")),
                f"{op.get('tiempo_s', 0):.1f}",
                "✅" if ok else "❌",
                op.get("hora", "?"),
            ]):
                _label(row, txt, size=10,
                       color=c if col == 2 else COLOR_TEXT).grid(
                    row=0, column=col, padx=2, sticky="w")


# ---------------------------------------------------------------------------
# Dashboard Planta 2 — Celda 3105
# ---------------------------------------------------------------------------

class DashboardPlanta2(ctk.CTkFrame):
    """Vista con tabs: Celda 3105 (estado + RFID + calidad) | Salud."""

    def __init__(self, master, health_checker: HealthChecker | None = None, **kw):
        super().__init__(master, fg_color=COLOR_BG, **kw)
        self._hc = health_checker

        self._tabs = _make_tabview(self)
        self._tabs.pack(fill="both", expand=True, padx=8, pady=8)

        for tab in ("Celda 3105", "Salud"):
            self._tabs.add(tab)

        self._build_celda_tab()
        self._build_salud_tab()

    # ---- Celda 3105 ----

    def _build_celda_tab(self):
        tab = self._tabs.tab("Celda 3105")
        Celda3105Panel(tab).pack(fill="both", expand=True)

    # ---- Salud ----

    def _build_salud_tab(self):
        tab = self._tabs.tab("Salud")
        _SaludTab(tab, health_checker=self._hc).pack(fill="both", expand=True)


# ---------------------------------------------------------------------------
# Access denied frame
# ---------------------------------------------------------------------------

class _AccessDeniedFrame(ctk.CTkFrame):
    """Pantalla de acceso denegado para usuarios sin permisos."""

    def __init__(self, master, rol: str, required: str, **kw):
        super().__init__(master, fg_color=COLOR_BG, **kw)
        _label(
            self,
            "⛔  Acceso denegado",
            size=20, bold=True, color=COLOR_ALERT,
        ).pack(pady=(60, 12))
        _label(
            self,
            f"Tu rol '{rol}' no tiene acceso a esta sección (requiere '{required}').",
            size=13, color=COLOR_TEXT_DIM,
        ).pack()
        _label(
            self,
            "Contacta al administrador si crees que esto es un error.",
            size=12, color=COLOR_TEXT_DIM,
        ).pack(pady=(4, 0))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

# Vistas permitidas por rol — usadas para validación en build_dashboard
_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin":   {"admin", "planta1", "planta2"},
    "planta1": {"planta1"},
    "planta2": {"planta2"},
}


def build_dashboard(master, rol: str,
                    health_checker: HealthChecker | None = None) -> ctk.CTkFrame:
    """Instancia el dashboard correcto según el rol.

    Valida que el rol tenga permisos antes de construir el frame.
    """
    if rol not in _ROLE_PERMISSIONS:
        raise ValueError(f"Rol desconocido: {rol}")

    if rol == "admin":
        if health_checker is None:
            raise ValueError("DashboardAdmin requiere health_checker")
        return DashboardAdmin(master, health_checker)

    if rol == "planta1":
        return DashboardPlanta1(master, health_checker=health_checker)

    if rol == "planta2":
        return DashboardPlanta2(master, health_checker=health_checker)

    # Este punto es inalcanzable dado el guard de arriba, pero satisface el tipo
    return _AccessDeniedFrame(master, rol=rol, required="admin")
