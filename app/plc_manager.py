"""
Gestión de PLCs S7 via python-snap7 — conexión directa desde la app.

NOTA: El PLC de Celda 3105 (IP 192.168.1.50) está manejado por Node-RED y
NO debe registrarse aquí. Esta clase gestiona PLCs ADICIONALES e independientes.
Mantener separación de responsabilidades entre ambas rutas.
"""

import re
import threading
import logging

import snap7
from snap7 import util as s7_util

logger = logging.getLogger(__name__)


class PLCManager:
    def __init__(self):
        self._clients = {}        # {plc_id: snap7.Client}
        self._lock = threading.Lock()
        self._values = {}         # {plc_id: {var_nombre: valor}}
        self._poll_threads = {}   # {plc_id: threading.Thread}
        self._polling_flags = {}  # {plc_id: threading.Event — set = detener}
        self._conn_status = {}    # {plc_id: 'connected'|'disconnected'|'error'}

    # ── Conexión ──────────────────────────────────────────────────────────────

    def connect(self, plc_id, ip, rack=0, slot=1):
        """Conectar a un PLC S7. Retorna {'ok': bool, 'error': str}"""
        try:
            with self._lock:
                if plc_id in self._clients:
                    try:
                        self._clients[plc_id].disconnect()
                    except Exception:
                        pass
                client = snap7.Client()
                client.connect(ip, rack, slot)
                self._clients[plc_id] = client
                self._conn_status[plc_id] = 'connected'
            logger.info("PLC %s conectado: %s rack=%d slot=%d", plc_id, ip, rack, slot)
            return {'ok': True, 'error': ''}
        except Exception as exc:
            self._conn_status[plc_id] = 'error'
            logger.warning("PLC %s conexión fallida (%s): %s", plc_id, ip, exc)
            return {'ok': False, 'error': str(exc)}

    def disconnect(self, plc_id):
        """Desconectar PLC y detener su polling"""
        self.stop_polling(plc_id)
        with self._lock:
            client = self._clients.pop(plc_id, None)
            if client:
                try:
                    client.disconnect()
                except Exception:
                    pass
            self._conn_status.pop(plc_id, None)
            self._values.pop(plc_id, None)
        logger.info("PLC %s desconectado", plc_id)

    def disconnect_all(self):
        """Desconectar todos los PLCs — llamar al cerrar la app"""
        for plc_id in list(self._clients.keys()):
            self.disconnect(plc_id)

    def test_connection(self, ip, rack=0, slot=1):
        """
        Probar conexión sin guardar en SQLite.
        Retorna {'ok': bool, 'error': str, 'cpu_info': str}
        """
        client = snap7.Client()
        try:
            client.connect(ip, rack, slot)
            cpu_info = 'Conectado'
            try:
                info = client.get_cpu_info()
                parts = []
                for attr in ('ModuleTypeName', 'ModuleName', 'SerialNumber'):
                    raw = getattr(info, attr, b'')
                    if isinstance(raw, (bytes, bytearray)):
                        val = raw.decode('utf-8', errors='replace').strip('\x00').strip()
                    else:
                        val = str(raw).strip()
                    if val:
                        parts.append(val)
                if parts:
                    cpu_info = ' / '.join(parts)
            except Exception:
                pass
            client.disconnect()
            return {'ok': True, 'error': '', 'cpu_info': cpu_info}
        except Exception as exc:
            try:
                client.disconnect()
            except Exception:
                pass
            return {'ok': False, 'error': str(exc), 'cpu_info': ''}

    # ── Lectura ───────────────────────────────────────────────────────────────

    def read_variable(self, plc_id, direccion, tipo):
        """
        Leer una variable del PLC. Retorna valor o None si falla.
        tipo: 'bool' | 'int' | 'real'
        """
        with self._lock:
            client = self._clients.get(plc_id)
        if client is None:
            return None
        try:
            return _read_s7(client, direccion, tipo)
        except Exception as exc:
            logger.debug("read_variable plc=%s dir=%s: %s", plc_id, direccion, exc)
            return None

    def read_all(self, plc_id, variables):
        """
        Leer todas las variables de un PLC en una sola llamada.
        variables: lista de dicts {'nombre', 'direccion', 'tipo'}
        Retorna dict {nombre: valor}
        """
        result = {}
        with self._lock:
            client = self._clients.get(plc_id)
        if client is None:
            return result
        for var in variables:
            try:
                result[var['nombre']] = _read_s7(client, var['direccion'], var['tipo'])
            except Exception as exc:
                logger.debug("read_all plc=%s var=%s: %s", plc_id, var['nombre'], exc)
                result[var['nombre']] = None
        return result

    # ── Polling ───────────────────────────────────────────────────────────────

    def start_polling(self, plc_id, variables, interval_ms=500):
        """Iniciar polling de variables en un hilo daemon."""
        self.stop_polling(plc_id)
        stop_event = threading.Event()
        self._polling_flags[plc_id] = stop_event

        def _poll():
            interval_s = interval_ms / 1000.0
            while not stop_event.is_set():
                with self._lock:
                    client = self._clients.get(plc_id)
                if client:
                    vals = {}
                    for var in variables:
                        try:
                            vals[var['nombre']] = _read_s7(
                                client, var['direccion'], var['tipo']
                            )
                        except Exception:
                            vals[var['nombre']] = None
                    self._values[plc_id] = vals
                stop_event.wait(interval_s)

        t = threading.Thread(
            target=_poll, daemon=True, name=f"plc-poll-{plc_id}"
        )
        self._poll_threads[plc_id] = t
        t.start()
        logger.info("Polling iniciado PLC %s cada %dms", plc_id, interval_ms)

    def stop_polling(self, plc_id):
        """Detener polling de un PLC"""
        evt = self._polling_flags.pop(plc_id, None)
        if evt:
            evt.set()
        self._poll_threads.pop(plc_id, None)

    def get_cached_values(self, plc_id):
        """Retorna últimos valores cacheados del polling"""
        return dict(self._values.get(plc_id, {}))

    # ── Estado ────────────────────────────────────────────────────────────────

    def get_status(self, plc_id):
        """Retorna estado de conexión: 'connected' | 'disconnected' | 'error'"""
        with self._lock:
            client = self._clients.get(plc_id)
        if client is None:
            return self._conn_status.get(plc_id, 'disconnected')
        try:
            return 'connected' if client.get_connected() else 'disconnected'
        except Exception:
            return 'error'


# ── Funciones auxiliares ───────────────────────────────────────────────────────

def _read_s7(client, direccion, tipo):
    """Lee una variable S7 dado el cliente snap7 y la dirección."""
    area, db_num, byte_pos, bit_pos, size = _parse_address(direccion, tipo)

    if area == 'DB':
        data = client.db_read(db_num, byte_pos, size)
    elif area in ('M', 'MW', 'MD'):
        data = client.mb_read(byte_pos, size)
    elif area in ('I', 'IW'):
        data = client.eb_read(byte_pos, size)
    elif area in ('Q', 'QW'):
        data = client.ab_read(byte_pos, size)
    else:
        raise ValueError(f"Área desconocida: {area}")

    if tipo == 'bool':
        return bool(s7_util.get_bool(data, 0, bit_pos))
    elif tipo == 'int':
        return int(s7_util.get_int(data, 0))
    elif tipo == 'real':
        return float(s7_util.get_real(data, 0))
    return None


def _parse_address(direccion, tipo):
    """
    Parsea dirección S7. Retorna (area, db_num, byte_pos, bit_pos, size).

    Soportados:
      Bool:  DB1.DBX0.0  M0.0   I0.1   Q0.2
      Int:   DB1.DBW2    MW10   IW0    QW0
      Real:  DB1.DBD4    MD20
    """
    d = direccion.upper().strip()

    # DB1.DBX0.0 | DB1.DBW2 | DB1.DBD4
    m = re.match(r'^DB(\d+)\.(DBX(\d+)\.(\d+)|DBW(\d+)|DBD(\d+))$', d)
    if m:
        db_num = int(m.group(1))
        if m.group(3) is not None:      # DBX bit
            return 'DB', db_num, int(m.group(3)), int(m.group(4)), 1
        elif m.group(5) is not None:    # DBW int
            return 'DB', db_num, int(m.group(5)), None, 2
        else:                           # DBD real
            return 'DB', db_num, int(m.group(6)), None, 4

    # M0.0
    m = re.match(r'^M(\d+)\.(\d+)$', d)
    if m:
        return 'M', None, int(m.group(1)), int(m.group(2)), 1
    # MW10
    m = re.match(r'^MW(\d+)$', d)
    if m:
        return 'MW', None, int(m.group(1)), None, 2
    # MD20
    m = re.match(r'^MD(\d+)$', d)
    if m:
        return 'MD', None, int(m.group(1)), None, 4

    # I0.1
    m = re.match(r'^I(\d+)\.(\d+)$', d)
    if m:
        return 'I', None, int(m.group(1)), int(m.group(2)), 1
    # IW0
    m = re.match(r'^IW(\d+)$', d)
    if m:
        return 'IW', None, int(m.group(1)), None, 2

    # Q0.2
    m = re.match(r'^Q(\d+)\.(\d+)$', d)
    if m:
        return 'Q', None, int(m.group(1)), int(m.group(2)), 1
    # QW0
    m = re.match(r'^QW(\d+)$', d)
    if m:
        return 'QW', None, int(m.group(1)), None, 2

    raise ValueError(f"Dirección S7 no reconocida: '{direccion}'")
