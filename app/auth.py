"""
Módulo de autenticación 2FA — huella dactilar AS608 + PIN bcrypt.

FINGERPRINT_ENABLED = False → solo pide PIN.
FINGERPRINT_ENABLED = True  → primero verifica huella, luego PIN.
"""

import logging
import time
from datetime import datetime, timedelta

import bcrypt

from config import (
    FINGERPRINT_ENABLED,
    AS608_PORT, AS608_BAUD, AS608_TIMEOUT_S,
    MAX_LOGIN_ATTEMPTS, LOCKOUT_MINUTES,
)
from db import get_db, init_db, log_audit

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Inicialización de base de datos y usuarios por defecto
# ---------------------------------------------------------------------------

_DEFAULT_USERS = [
    ("admin",     "1234", "admin",  1),
    ("operador1", "2222", "planta1", 2),
    ("operador2", "3333", "planta1", 3),
    ("operador3", "4444", "planta2", 4),
    ("operador4", "5555", "planta2", 5),
]


def bootstrap_users() -> None:
    """Crea los usuarios por defecto si la tabla está vacía."""
    init_db()
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        for username, pin, rol, huella_id in _DEFAULT_USERS:
            pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username, pin_hash, rol, huella_id) VALUES (?,?,?,?)",
                (username, pin_hash, rol, huella_id),
            )
        conn.commit()
        log.info("Usuarios por defecto creados en SQLite.")
    conn.close()


# ---------------------------------------------------------------------------
# Gestión de intentos fallidos y bloqueo
# ---------------------------------------------------------------------------

def _get_failed(conn, username: str) -> dict:
    row = conn.execute(
        "SELECT count, locked_until FROM failed_attempts WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        return {"count": 0, "locked_until": None}
    return {"count": row["count"], "locked_until": row["locked_until"]}


def _is_locked(username: str) -> tuple[bool, int]:
    """Retorna (bloqueado, segundos_restantes)."""
    conn = get_db()
    info = _get_failed(conn, username)
    conn.close()
    if info["locked_until"]:
        locked_dt = datetime.fromisoformat(info["locked_until"])
        remaining = (locked_dt - datetime.now()).total_seconds()
        if remaining > 0:
            return True, int(remaining)
        # Bloqueo expirado — limpiar
        _reset_failed(username)
    return False, 0


def _increment_failed(username: str) -> int:
    """Incrementa contador; bloquea si llega al máximo. Retorna conteo actual."""
    conn = get_db()
    info = _get_failed(conn, username)
    new_count = info["count"] + 1
    locked_until = None
    if new_count >= MAX_LOGIN_ATTEMPTS:
        locked_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
    conn.execute(
        """INSERT INTO failed_attempts (username, count, locked_until)
           VALUES (?, ?, ?)
           ON CONFLICT(username) DO UPDATE SET count=excluded.count,
                                               locked_until=excluded.locked_until""",
        (username, new_count, locked_until),
    )
    conn.commit()
    conn.close()
    return new_count


def _reset_failed(username: str) -> None:
    conn = get_db()
    conn.execute("DELETE FROM failed_attempts WHERE username = ?", (username,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Sensor AS608 — huella dactilar
# ---------------------------------------------------------------------------

def verify_fingerprint(expected_huella_id: int) -> tuple:
    """
    Verifica la huella en el sensor AS608.
    Retorna:
      (True,  msg)  — huella verificada correctamente
      (False, msg)  — huella rechazada (no coincide o no reconocida)
      (None,  msg)  — timeout o error de hardware → usar fallback PIN-only
    """
    try:
        from pyfingerprint.pyfingerprint import PyFingerprint  # type: ignore
        sensor = PyFingerprint(AS608_PORT, AS608_BAUD, 0xFFFFFFFF, 0x00000000)
        if not sensor.verifyPassword():
            return None, "Sensor AS608: sin respuesta válida (revisar TX/RX o puerto)"

        log.info("Esperando huella en AS608 (timeout=%ds)...", AS608_TIMEOUT_S)
        deadline = time.monotonic() + AS608_TIMEOUT_S
        while not sensor.readImage():
            if time.monotonic() >= deadline:
                return None, f"Sin dedo detectado en {AS608_TIMEOUT_S}s"
            time.sleep(0.05)

        sensor.convertImage(0x01)
        result = sensor.searchTemplate()
        position, accuracy = result[0], result[1]

        if position == -1:
            return False, "Huella no reconocida"
        if position + 1 != expected_huella_id:
            return False, f"Huella no corresponde al usuario (pos={position})"
        return True, f"Huella verificada (pos={position}, acc={accuracy})"

    except ImportError:
        log.error("pyfingerprint no instalado")
        return None, "pyfingerprint no disponible — fallback a PIN"
    except Exception as exc:
        log.error("Error sensor AS608: %s", exc)
        return None, f"Error sensor: {exc}"


def enroll_fingerprint(huella_id: int) -> tuple[bool, str]:
    """
    Registra una nueva huella en la posición huella_id-1 del sensor.
    """
    try:
        from pyfingerprint.pyfingerprint import PyFingerprint  # type: ignore
        sensor = PyFingerprint(AS608_PORT, AS608_BAUD, 0xFFFFFFFF, 0x00000000)
        if not sensor.verifyPassword():
            return False, "Sensor AS608: contraseña inválida"

        log.info("Coloca el dedo en el sensor (1er lectura)...")
        while not sensor.readImage():
            pass
        sensor.convertImage(0x01)

        log.info("Retira y vuelve a colocar el mismo dedo...")
        while sensor.readImage():
            pass
        while not sensor.readImage():
            pass
        sensor.convertImage(0x02)

        if sensor.compareCharacteristics() == 0:
            return False, "Huellas no coinciden — intenta de nuevo"

        sensor.createTemplate()
        position = sensor.storeTemplate(huella_id - 1)
        return True, f"Huella guardada en posición {position}"

    except Exception as exc:
        return False, f"Error al enrollar: {exc}"


# ---------------------------------------------------------------------------
# Autenticación por huella — sin username/PIN
# ---------------------------------------------------------------------------

def authenticate_by_fingerprint() -> "AuthResult":
    """
    Escanea el sensor, identifica la huella y retorna el usuario asociado.
    No requiere que el usuario ingrese nombre ni PIN.
    Retorna AuthResult con ok=True si encuentra un usuario registrado.
    """
    try:
        from pyfingerprint.pyfingerprint import PyFingerprint  # type: ignore
        sensor = PyFingerprint(AS608_PORT, AS608_BAUD, 0xFFFFFFFF, 0x00000000)
        if not sensor.verifyPassword():
            return AuthResult(False, message="Sensor AS608: sin respuesta válida")

        log.info("Esperando huella (timeout=%ds)...", AS608_TIMEOUT_S)
        deadline = time.monotonic() + AS608_TIMEOUT_S
        while not sensor.readImage():
            if time.monotonic() >= deadline:
                return AuthResult(False, message=f"Sin dedo detectado en {AS608_TIMEOUT_S}s")
            time.sleep(0.05)

        sensor.convertImage(0x01)
        result = sensor.searchTemplate()
        position, accuracy = result[0], result[1]

        if position == -1:
            return AuthResult(False, message="Huella no registrada")

        huella_id = position + 1
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE huella_id = ? AND activo = 1", (huella_id,)
        ).fetchone()
        conn.close()

        if row is None:
            return AuthResult(False, message=f"Huella en posición {position} sin usuario asociado")

        log_audit(row["username"], "LOGIN_HUELLA", True,
                  detalle=f"Autenticación por huella — pos={position}, acc={accuracy}")
        return AuthResult(True, row["username"], row["rol"], huella_id,
                         f"Acceso concedido (huella, precisión={accuracy})")

    except ImportError:
        return AuthResult(False, message="pyfingerprint no disponible")
    except Exception as exc:
        log.error("Error sensor AS608 en authenticate_by_fingerprint: %s", exc)
        return AuthResult(False, message=f"Error sensor: {exc}")


# ---------------------------------------------------------------------------
# Autenticación principal
# ---------------------------------------------------------------------------

class AuthResult:
    def __init__(self, ok: bool, username: str = "", rol: str = "",
                 huella_id: int = 0, message: str = ""):
        self.ok        = ok
        self.username  = username
        self.rol       = rol
        self.huella_id = huella_id
        self.message   = message

    def __bool__(self):
        return self.ok


def authenticate(username: str, pin: str) -> AuthResult:
    """
    Flujo 2FA completo:
      1. Verificar bloqueo por intentos fallidos.
      2. Si FINGERPRINT_ENABLED=True → verificar huella.
      3. Verificar PIN con bcrypt.
      4. Registrar en audit_log.
    """
    username = username.strip().lower()

    # 1) Bloqueo
    locked, secs = _is_locked(username)
    if locked:
        mins = secs // 60 + 1
        return AuthResult(False, username, message=f"Cuenta bloqueada. Intenta en {mins} min.")

    # 2) Buscar usuario en DB
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND activo = 1", (username,)
    ).fetchone()
    conn.close()

    if row is None:
        log_audit(username, "LOGIN", False, detalle="Usuario no encontrado")
        _increment_failed(username)
        return AuthResult(False, username, message="Usuario o PIN incorrecto")

    # 3) Huella — solo si está habilitada explícitamente
    if FINGERPRINT_ENABLED:
        fp_ok, fp_msg = verify_fingerprint(row["huella_id"])
        if fp_ok is None:
            # Timeout o error de hardware → continuar solo con PIN, registrar en audit
            log_audit(username, "LOGIN_HUELLA_TIMEOUT", False,
                      detalle=f"huella omitida por sensor — {fp_msg}")
            log.warning("AS608 no respondió — fallback a solo PIN para '%s'", username)
        elif not fp_ok:
            log_audit(username, "LOGIN_HUELLA", False, detalle=fp_msg)
            _increment_failed(username)
            return AuthResult(False, username, message=f"Huella inválida: {fp_msg}")

    # 4) PIN bcrypt
    pin_ok = bcrypt.checkpw(pin.encode(), row["pin_hash"].encode())
    if not pin_ok:
        count = _increment_failed(username)
        remaining = MAX_LOGIN_ATTEMPTS - count
        msg = (
            f"PIN incorrecto. Intentos restantes: {remaining}"
            if remaining > 0
            else f"Cuenta bloqueada por {LOCKOUT_MINUTES} minutos"
        )
        log_audit(username, "LOGIN", False, detalle="PIN incorrecto")
        return AuthResult(False, username, message=msg)

    # Éxito
    _reset_failed(username)
    log_audit(username, "LOGIN", True, detalle="2FA completado")
    return AuthResult(True, username, row["rol"], row["huella_id"], "Acceso concedido")


def add_user(username: str, pin: str, rol: str, huella_id: int) -> tuple[bool, str]:
    """Agrega un nuevo usuario (solo admin)."""
    if rol not in ("admin", "planta1", "planta2"):
        return False, f"Rol inválido: {rol}"
    pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, pin_hash, rol, huella_id) VALUES (?,?,?,?)",
            (username, pin_hash, rol, huella_id),
        )
        conn.commit()
        log_audit("system", "ADD_USER", True, detalle=f"nuevo: {username}/{rol}")
        return True, f"Usuario '{username}' creado"
    except Exception as exc:
        return False, str(exc)
    finally:
        conn.close()
