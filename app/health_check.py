"""Verificador periódico de servicios del stack Smart Manufacturing."""

import socket
import threading
import logging
import subprocess
from urllib import request as urequest
from urllib.error import URLError

from config import RPi_IP, SERVICES, HEALTH_INTERVAL_S

log = logging.getLogger(__name__)

# Estados posibles
STATUS_OK   = "ok"       # verde
STATUS_WARN = "warn"     # amarillo — responde pero lento
STATUS_DOWN = "down"     # rojo — sin conexión

SYSTEMCTL_NAMES = {
    "mosquitto": "mosquitto",
    "influxdb":  "influxdb2",
    "nodered":   "nodered",
    "n8n":       "n8n",
    "grafana":   "grafana-server",
}


class HealthChecker:
    """
    Comprueba todos los servicios definidos en config.SERVICES cada
    HEALTH_INTERVAL_S segundos y notifica a los callbacks suscritos.
    """

    def __init__(self):
        self._statuses: dict[str, str] = {k: STATUS_WARN for k in SERVICES}
        self._callbacks: list = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def subscribe(self, callback) -> None:
        """callback(statuses: dict[str, str]) se llamará tras cada check."""
        self._callbacks.append(callback)

    def get_statuses(self) -> dict[str, str]:
        return dict(self._statuses)

    def start(self) -> None:
        """Lanza el hilo de verificación en segundo plano."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def check_now(self) -> dict[str, str]:
        """Verificación síncrona inmediata (bloquea hasta completar)."""
        results = {}
        for name, cfg in SERVICES.items():
            results[name] = self._check_one(name, cfg)
        self._statuses = results
        self._notify()
        return results

    def restart_service(self, service_key: str) -> tuple[bool, str]:
        """
        Intenta reiniciar el servicio via systemctl.
        Retorna (éxito, mensaje).
        """
        svc = SYSTEMCTL_NAMES.get(service_key)
        if not svc:
            return False, f"Servicio desconocido: {service_key}"
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "restart", svc],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                return True, f"{svc} reiniciado correctamente"
            return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado al reiniciar"
        except Exception as exc:
            return False, str(exc)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self.check_now()
            self._stop_event.wait(HEALTH_INTERVAL_S)

    def _check_one(self, name: str, cfg: dict) -> str:
        try:
            if cfg["type"] == "tcp":
                return self._tcp_check(cfg["port"])
            return self._http_check(cfg["port"], cfg.get("path", "/"))
        except Exception as exc:
            log.debug("Health check %s error: %s", name, exc)
            return STATUS_DOWN

    def _tcp_check(self, port: int, timeout: float = 2.0) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((RPi_IP, port))
            return STATUS_OK if result == 0 else STATUS_DOWN
        finally:
            sock.close()

    def _http_check(self, port: int, path: str, timeout: float = 3.0) -> str:
        url = f"http://{RPi_IP}:{port}{path}"
        try:
            req = urequest.Request(url)
            with urequest.urlopen(req, timeout=timeout) as resp:
                return STATUS_OK if resp.status < 400 else STATUS_WARN
        except URLError:
            return STATUS_DOWN

    def _notify(self) -> None:
        for cb in self._callbacks:
            try:
                cb(dict(self._statuses))
            except Exception as exc:
                log.warning("Health callback error: %s", exc)
