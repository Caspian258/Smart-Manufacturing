#!/usr/bin/env python3
"""
Enrollamiento de huellas dactilares — AS608 / JM-101B
Uso: python3 scripts/enroll_fingerprint.py

Ejecutar desde la raíz del proyecto o desde el directorio app/.
Requiere que el venv tenga pyfingerprint y pyserial instalados.
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from config import AS608_PORT, AS608_BAUD, AS608_TIMEOUT_S

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'app', 'smart_mfg.db')


def get_users() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, username, rol, huella_id FROM users WHERE activo = 1").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_huella_id(username: str, huella_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET huella_id = ? WHERE username = ?", (huella_id, username))
    conn.commit()
    conn.close()


def enroll(username: str, huella_id: int) -> tuple[bool, str]:
    try:
        from pyfingerprint.pyfingerprint import PyFingerprint
    except ImportError:
        return False, "pyfingerprint no instalado — ejecuta: pip install pyfingerprint"

    try:
        sensor = PyFingerprint(AS608_PORT, AS608_BAUD, 0xFFFFFFFF, 0x00000000)
        if not sensor.verifyPassword():
            return False, f"Sensor en {AS608_PORT} no responde — revisa la conexión"
    except Exception as exc:
        return False, f"No se pudo abrir {AS608_PORT}: {exc}"

    # Verificar que la posición no esté ocupada
    try:
        if sensor.loadTemplate(huella_id - 1, 0x01):
            resp = input(f"  Posición {huella_id - 1} ya tiene una huella. ¿Sobrescribir? [s/N] ").strip().lower()
            if resp != 's':
                return False, "Enrollamiento cancelado"
    except Exception:
        pass

    print(f"\n  → Coloca el dedo en el sensor...")
    try:
        while not sensor.readImage():
            pass
        sensor.convertImage(0x01)
    except Exception as exc:
        return False, f"Error leyendo imagen 1: {exc}"

    print("  → Levanta el dedo...")
    try:
        while sensor.readImage():
            pass
    except Exception:
        pass

    print("  → Coloca el mismo dedo de nuevo...")
    try:
        while not sensor.readImage():
            pass
        sensor.convertImage(0x02)
    except Exception as exc:
        return False, f"Error leyendo imagen 2: {exc}"

    try:
        score = sensor.compareCharacteristics()
        if score == 0:
            return False, "Las dos lecturas no coinciden — intenta de nuevo"
        sensor.createTemplate()
        position = sensor.storeTemplate(huella_id - 1)
        return True, f"Huella guardada en posición {position} (puntuación={score})"
    except Exception as exc:
        return False, f"Error al guardar: {exc}"


def main():
    print("=" * 50)
    print("  Enrollamiento de huellas — AS608 / JM-101B")
    print(f"  Puerto: {AS608_PORT}  Baud: {AS608_BAUD}")
    print("=" * 50)

    users = get_users()
    if not users:
        print("No hay usuarios en la base de datos. Ejecuta la app primero.")
        sys.exit(1)

    print("\nUsuarios registrados:")
    for u in users:
        fp_status = f"huella_id={u['huella_id']}" if u['huella_id'] else "sin huella"
        print(f"  [{u['id']}] {u['username']} ({u['rol']}) — {fp_status}")

    print()
    username = input("Usuario a enrollar: ").strip().lower()
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        print(f"Usuario '{username}' no encontrado.")
        sys.exit(1)

    # Asignar huella_id: si ya tiene uno, usarlo; si no, asignar el siguiente libre
    existing_ids = {u['huella_id'] for u in users if u['huella_id']}
    suggested_id = user['huella_id'] or next(i for i in range(1, 200) if i not in existing_ids)

    id_input = input(f"  Posición en sensor (1-199) [{suggested_id}]: ").strip()
    huella_id = int(id_input) if id_input else suggested_id
    if not 1 <= huella_id <= 199:
        print("Posición fuera de rango (1-199).")
        sys.exit(1)

    print(f"\nEnrollando huella de '{username}' en posición {huella_id - 1}...")
    ok, msg = enroll(username, huella_id)

    if ok:
        update_huella_id(username, huella_id)
        print(f"\n  ✓ {msg}")
        print(f"  ✓ BD actualizada: {username}.huella_id = {huella_id}")
    else:
        print(f"\n  ✗ {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
