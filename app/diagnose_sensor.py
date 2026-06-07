"""
Diagnóstico de conexión UART para sensor AS608 / JM-101B en RPi5.

Uso:
    python3 app/diagnose_sensor.py

Prueba todos los puertos UART disponibles y reporta cuál responde
con un header válido del sensor (0xEF 0x01).
"""

import os
import sys
import glob
import time

BAUD = 57600
TIMEOUT = 2.0

# Comando de verificación de password (contraseña por defecto 0x00000000)
CMD_VERIFY_PASSWORD = bytes([
    0xEF, 0x01,             # header
    0xFF, 0xFF, 0xFF, 0xFF, # address (broadcast)
    0x01,                   # package identifier (command)
    0x00, 0x07,             # length = 7
    0x13,                   # instruction: VfyPwd
    0x00, 0x00, 0x00, 0x00, # password
    0x00, 0x1B,             # checksum
])

PORTS_TO_TRY = [
    "/dev/ttyAMA10",
    "/dev/ttyAMA0",
    "/dev/ttyAMA1",
    "/dev/serial0",
    "/dev/serial1",
    "/dev/ttyS0",
]


def check_symlinks():
    print("── Symlinks UART ──────────────────────────────")
    for p in ["/dev/serial0", "/dev/serial1"]:
        if os.path.islink(p):
            target = os.readlink(p)
            print(f"  {p} → {target}")
        else:
            print(f"  {p} — no existe")
    print()


def list_available_ports():
    print("── Puertos UART disponibles ────────────────────")
    ports = sorted(glob.glob("/dev/ttyAMA*") + glob.glob("/dev/ttyS*"))
    if ports:
        for p in ports:
            print(f"  {p}")
    else:
        print("  (ninguno encontrado)")
    print()
    return ports


def test_port(port: str) -> bool:
    try:
        import serial
    except ImportError:
        print("  [ERROR] pyserial no instalado: pip install pyserial")
        return False

    if not os.path.exists(port):
        print(f"  [SKIP] {port} — no existe")
        return False

    try:
        ser = serial.Serial(port, BAUD, timeout=TIMEOUT)
    except Exception as e:
        print(f"  [ERROR] {port} — no se pudo abrir: {e}")
        return False

    print(f"  Probando {port} @ {BAUD}baud... ", end="", flush=True)
    ser.reset_input_buffer()
    ser.write(CMD_VERIFY_PASSWORD)
    ser.flush()

    deadline = time.monotonic() + TIMEOUT
    buf = b""
    while time.monotonic() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            buf += chunk
            if len(buf) >= 2:
                break

    ser.close()

    if len(buf) < 2:
        print("sin respuesta")
        return False

    if buf[0] == 0xEF and buf[1] == 0x01:
        print(f"OK — header válido (0xEF 0x01) recibido, {len(buf)} bytes")
        return True
    else:
        raw = " ".join(f"0x{b:02X}" for b in buf[:8])
        print(f"respuesta inválida: {raw}")
        print(f"  → Posible causa: TX/RX invertidos en este puerto")
        return False


def loopback_test(port: str):
    """Conecta TX con RX físicamente antes de correr este test."""
    try:
        import serial
    except ImportError:
        return

    if not os.path.exists(port):
        return

    print(f"\n── Loopback test en {port} ─────────────────────")
    print("  (Asegúrate de tener TX conectado a RX en el conector físico)")
    try:
        ser = serial.Serial(port, BAUD, timeout=1)
        test_bytes = b"\xDE\xAD\xBE\xEF"
        ser.reset_input_buffer()
        ser.write(test_bytes)
        ser.flush()
        time.sleep(0.1)
        received = ser.read(len(test_bytes))
        ser.close()
        if received == test_bytes:
            print(f"  ✅ UART funciona correctamente — loopback OK")
        elif received:
            print(f"  ⚠  Recibido parcial: {received.hex()} (esperado: {test_bytes.hex()})")
        else:
            print("  ❌ Sin respuesta — el UART no está disponible o TX/RX no conectados")
    except Exception as e:
        print(f"  ERROR: {e}")


def try_pyfingerprint(port: str):
    print(f"\n── pyfingerprint en {port} ──────────────────────")
    try:
        from pyfingerprint.pyfingerprint import PyFingerprint  # type: ignore
        sensor = PyFingerprint(port, BAUD, 0xFFFFFFFF, 0x00000000)
        if sensor.verifyPassword():
            print(f"  ✅ Sensor AS608 verificado correctamente en {port}")
        else:
            print(f"  ❌ verifyPassword() retornó False — contraseña o protocolo incorrecto")
    except ImportError:
        print("  pyfingerprint no instalado (normal si estás fuera del venv)")
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════╗")
    print("║  Diagnóstico UART — Sensor AS608 / JM-101B  ║")
    print("╚══════════════════════════════════════════════╝\n")

    check_symlinks()
    list_available_ports()

    print("── Prueba de comunicación ──────────────────────")
    found = None
    for port in PORTS_TO_TRY:
        if test_port(port):
            found = port
            break

    if found:
        print(f"\n✅ Sensor encontrado en: {found}")
        print(f"   Actualiza config.py → AS608_PORT = \"{found}\"")
        try_pyfingerprint(found)
    else:
        print("\n⚠  Ningún puerto respondió con header válido.")
        print("   Posibles causas:")
        print("   1. TX/RX invertidos — intercambia los cables amarillo y verde")
        print("   2. VCC insuficiente — verifica que VCC está en 3.3V (Pin 1)")
        print("   3. Puerto no habilitado — agrega 'enable_uart=1' en /boot/firmware/config.txt")
        print("   4. Bluetooth ocupando ttyAMA0 — agrega 'dtoverlay=disable-bt'")
        print()
        print("── Diagnóstico adicional ───────────────────────")
        print("   Corre en RPi5:")
        print("   ls -la /dev/ttyAMA* /dev/serial*")
        print("   dmesg | grep -i 'uart\\|serial\\|ttyAMA'")
        print("   cat /boot/firmware/config.txt | grep -i uart")
        loopback_test(PORTS_TO_TRY[0])
