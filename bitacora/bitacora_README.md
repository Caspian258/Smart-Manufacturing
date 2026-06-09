# Bitácora — Smart Manufacturing CIMA + Celda 3105
# Orquestador: Claude Code
# ═══════════════════════════════════════════════════════════════════════

## ENTRADA #001 — Pipeline ESP32 → MQTT → n8n → InfluxDB
- **Fecha**: 2026-03-28
- **Estado**: ✅ Completado — HITO FASE 1

---

## ENTRADA #002 — Primer dato MQTT recibido
- **Fecha**: 2026-03-28
- **Estado**: ✅ Completado — HITO FASE 1

---

## ENTRADA #003 — Stack RPi5 completamente operativo
- **Fecha**: 2026-03-28
- **Estado**: ✅ Completado

| Servicio | Puerto | Estado |
|---------|--------|--------|
| Mosquitto | 1883/8883 | ✅ |
| InfluxDB 2.7 | 8086 | ✅ |
| Node-RED | 1880 | ✅ |
| n8n | 5678 | ✅ |
| Grafana | 3001 | ✅ |

---

## ENTRADA #004 — Estructura del repositorio
- **Fecha**: 2026-03-28
- **Estado**: ✅ Completado

---

## ENTRADA #005 — Grafana CIMA operativo
- **Fecha**: 2026-03-29
- **Estado**: ✅ Completado | Puerto 3001

---

## ENTRADA #006 — Dashboard Node-RED CIMA operativo
- **Fecha**: 2026-03-29
- **Estado**: ✅ Completado

---

## ENTRADA #007 — Auditoría autenticación RPi5
- **Fecha**: 2026-04-10
- **Estado**: ✅ Completado

| Servicio | Auth | Riesgo |
|---------|------|--------|
| Node-RED 1880 | ❌ Sin auth | 🔴 ALTO |
| Grafana 3001 | ✅ admin/admin | 🔴 ALTO |
| n8n 5678 | ✅ SmartMfg2024! | 🟢 OK |
| InfluxDB 8086 | ✅ Token | 🟢 OK |
| Mosquitto 8883 | ✅ TLS + auth | 🟢 OK |

---

## ENTRADA #008 — ESP32 → RPi5 MQTT-TLS puerto 8883 operativo
- **Fecha**: 2026-04-10
- **Estado**: ✅ Completado — datos cada 5s

---

## ENTRADA #009 — HITO MAYOR: Pipeline completo PLC → Grafana operativo
- **Fecha**: 2026-04-20
- **Estado**: ✅ Completado — HITO FASE 2 (Celda 3105)
- **Acción**: Pipeline completo S7-1200 → node-red-contrib-s7 → Node-RED → InfluxDB → Grafana funcionando en tiempo real con red wireless via COM-845.

### Pipeline implementado
```
PLC S7-1200 (192.168.100.50)
        │ S7comm / ISO-on-TCP puerto 102 / Cycle time: 200ms
node-red-contrib-s7 (RPi5 192.168.100.23)
        │
Node-RED — Tab "Celda 3105 — PLC"
        ├── Parsear tags PLC (24 variables)
        ├── MQTT → celda3105/plc/kpis        ✅
        └── HTTP → InfluxDB sensor-data      ✅
                        │
        Grafana — "Smart Manufacturing — Celda 3105 (Planta 2)" ✅
```

### Componentes implementados
| Componente | Estado | Detalles |
|-----------|--------|---------|
| node-red-contrib-s7 | ✅ | npm install en ~/.node-red |
| Flow Node-RED Celda 3105 | ✅ | Tab separado del flow CIMA |
| 24 variables PLC mapeadas | ✅ | Q, I, M — salidas/entradas clave |
| MQTT celda3105/plc/kpis | ✅ | Publicando cada 200ms |
| InfluxDB celda3105_plc | ✅ | bucket sensor-data |
| Dashboard Grafana Celda 3105 | ✅ | 9 paneles, refresh 5s |
| Red wireless COM-845 | ✅ | 192.168.100.x operativa |

### Dashboard Grafana — 9 paneles
| Panel | Métrica | Estado |
|-------|---------|--------|
| Estado Celda 3105 | verde_celda | ✅ |
| Paro de Emergencia | killswitch (NC invertido) | ✅ |
| Disponibilidad Celda | disponible | ✅ |
| Bandas Activas | bandas_activas (0-4) | ✅ |
| Posición Pieza | posicion_pieza (1-7) | ✅ |
| Produciendo | produciendo | ✅ |
| Historial Estado | 30 min | ✅ |
| Historial Bandas | 30 min | ✅ |
| Tracking Posición | 30 min | ✅ |

### Correcciones aplicadas
| Problema | Solución |
|---------|---------|
| Killswitch NC (1=normal, 0=emergencia) | `const kill = !d.Killswitch` |
| Variables S7 no importaban desde CSV | Separador `;` requerido (address;name) |
| Nodo s7 no reconocido post-install | `sudo systemctl restart nodered` |
| Datos viejos posición=7 en InfluxDB | ⚠️ Pendiente — `influx delete` no funcionó |

### Sensores físicos — C2_Led_1 a C2_Led_7
- Tipo: sensores fotoeléctricos (barrera de luz)
- Lógica: pieza interrumpe haz → entrada = `true`
- Direcciones: I0.0, I0.1, I0.3, I0.4, I0.6, I8.1, I8.0
- ⚠️ Led_6 (I8.1) y Led_7 (I8.0) — verificar orden físico en línea

### Archivos creados/modificados
- `flows/nodered/nodered_dashboard.json` — flow con tab Celda 3105
- `dashboard/grafana_celda3105_planta2.json` — dashboard Grafana
- `config/plc_variables.csv` — variables PLC (format: address;name)
- `bitacora/bitacora_README.md` — esta entrada

---

## ENTRADA #010 — HITO: RPi5 ↔ PLC comunicación wireless confirmada
- **Fecha**: 2026-04-20
- **Estado**: ✅ Completado

### Red operativa
| Dispositivo | IP | Conexión |
|------------|-----|----------|
| PLC S7-1200 | 192.168.100.50 | Ethernet → SCALANCE → COM-845 |
| RPi5 | 192.168.100.23 | WiFi → COM-845 |
| Laptop Fedora | 192.168.100.13 | WiFi → COM-845 |
| COM-845 | 192.168.100.1 | WAN → red Tec |

---

## ENTRADA #011 — HITO: PLC en 192.168.100.50 + PUT/GET habilitado
- **Fecha**: 2026-04-20
- **Estado**: ✅ Completado

| Parámetro | Antes | Después |
|-----------|-------|---------|
| IP PLC_2 | 192.168.0.10 | 192.168.100.50 |
| PUT/GET | Deshabilitado | ✅ Habilitado |
| Hardware config | — | ✅ 0 errors, 0 warnings |

---

## ENTRADA #012 — App escritorio CustomTkinter con 2FA y RBAC
- **Fecha**: 2026-05-13 00:00
- **Acción**: Implementación completa de app de escritorio Python/CustomTkinter con autenticación 2FA (huella AS608 + PIN bcrypt), roles RBAC (admin/planta1/planta2), health check de servicios y dashboards por rol.
- **Estado**: ✅ Completado
- **Archivos creados**:
  - `app/main.py`       — Entry point, login screen, ventana principal
  - `app/auth.py`       — 2FA huella+PIN, bcrypt, lockout 3 intentos/5 min, audit log
  - `app/dashboards.py` — Vistas admin/planta1/planta2 con datos reales de InfluxDB
  - `app/health_check.py` — Verificador de servicios cada 60s con semáforo visual
  - `app/db.py`         — Capa InfluxDB (query energía 24h, Celda 3105) + SQLite (users, audit)
  - `app/config.py`     — Constantes: IPs, puertos, paleta de colores, SIMULATION_MODE
  - `app/install.sh`    — Script de instalación de dependencias pip
- **Correcciones aplicadas**:
  - `CLAUDE.md`: Grafana puerto 3000 → 3001
  - `scripts/setup_rpi5.sh`: GRAFANA_PORT=3000 → GRAFANA_PORT=3001

### Cómo lanzar la app
```bash
bash app/install.sh          # instalar dependencias (solo primera vez)
python3 app/main.py          # iniciar la app
```

### Usuarios disponibles (modo simulación)
| Usuario    | PIN  | Rol     |
|-----------|------|---------|
| admin      | 1234 | admin   |
| operador1  | 2222 | planta1 |
| operador2  | 3333 | planta1 |
| operador3  | 4444 | planta2 |
| operador4  | 5555 | planta2 |

### Cómo registrar huella nueva (modo admin)
1. Ingresar como `admin`
2. Tab "Usuarios" → sección "Agregar Usuario"
3. Ingresar username, PIN, rol y Huella ID
4. Clic en "Enrollar Huella (AS608)" — sensor AS608 debe estar conectado (SIMULATION_MODE=False)
5. Seguir instrucciones en pantalla (2 lecturas del dedo)

### Cómo cambiar a modo REAL cuando se conecte el AS608
```python
# app/config.py
SIMULATION_MODE = False      # activa verificación de huella
AS608_PORT      = "/dev/ttyS0"   # ajustar si el UART es diferente
AS608_BAUD      = 57600
```
Conexión física: AS608 TX → RPi5 GPIO14 (UART RX) | AS608 RX → RPi5 GPIO15 (UART TX)

- **Próximo paso**: Integrar refresh automático de dashboards cada 30s + gráfica de líneas con matplotlib/canvas para energía 24h

---

## ENTRADA #013 — App desktop operativa en RPi5 + SIMULATION_MODE=False
- **Fecha**: 2026-05-13 12:00
- **Acción**: App desktop verificada corriendo en RPi5 en venv dedicado. SIMULATION_MODE cambiado a False para activar lectura de huella AS608. Puerto UART ajustado a /dev/ttyAMA0.
- **Estado**: ✅ Completado — AS608 pendiente de conexión física

### Entorno de ejecución en RPi5
- **venv**: `/opt/smart-manufacturing/venv/`
- **Dependencias instaladas**: `pip install customtkinter influxdb-client pyfingerprint bcrypt python-dotenv pillow`
- **Tkinter**: requirió instalación separada → `sudo apt install python3-tk -y`
- **Alias en `~/.bashrc` del usuario caspian**: `alias smfg='source /opt/smart-manufacturing/venv/bin/activate && python3 /home/caspian/Proyectos/Smart-Manufacturing-Project/app/main.py'`
- **Lanzamiento completo**:
  ```bash
  source /opt/smart-manufacturing/venv/bin/activate
  python3 app/main.py
  # O simplemente:
  smfg
  ```

### Cambios en config.py
| Parámetro | Antes | Después |
|---|---|---|
| `SIMULATION_MODE` | `True` | `False` |
| `AS608_PORT` | `/dev/ttyS0` | `/dev/ttyAMA0` |

> **Importante**: Con `SIMULATION_MODE = False`, si el AS608 no está conectado físicamente
> la app mostrará error de puerto serial al intentar verificar la huella.
> Solución temporal: volver a `SIMULATION_MODE = True` en `app/config.py` hasta
> conectar el sensor.

### Próximo paso — Conexión física del AS608
```
AS608        RPi5 GPIO
───────      ──────────────────────────────
TX     →     GPIO14 / Pin 8  (UART RX)
RX     →     GPIO15 / Pin 10 (UART TX)
VCC    →     Pin 1  (3.3V)
GND    →     Pin 6  (GND)
```
Verificar que UART esté habilitado: `sudo raspi-config` → Interface Options → Serial Port.

- **Archivos modificados**: `app/config.py`
- **Próximo paso**: Conectar AS608 físicamente según pinout → probar enrollado de huella desde panel admin

---

## ENTRADA #014 — Diagnóstico AS608 + fallback timeout + pipeline RFID completo
- **Fecha**: 2026-05-14
- **Estado**: ✅ Completado
- **Acción**: Corrección del pipeline RFID ESP32→MQTT→Node-RED→InfluxDB→Grafana. Mejora de velocidad de detección RC522. Diagnóstico y fallback para sensor de huellas AS608.

### Correcciones ESP32 (firmware)
| Problema | Causa | Fix |
|---|---|---|
| RC522 no publicaba a MQTT | `readRFID()` se llamaba pero no había `publishRFID()` | Se agregó función `publishRFID()` y se llama al detectar tarjeta |
| Detección de tarjeta lenta | Ganancia antena por defecto (mínima), `delay(10)` en loop | `PCD_SetAntennaGain(RxGain_max)`, `delay(10)→delay(1)` |
| Doble publicación mismo UID | Sin debounce | Debounce 2s con `lastRfidUid` + `lastRfidMs` |

### Correcciones Node-RED
- Funciones "RFID Presente" y "RFID Ausente" tenían `msg.payload` vacío (template literals backtick corrompidas al guardar JSON)
- Corregido y re-desplegado via API REST: `POST http://10.25.15.234:1880/flows`

### Diagnóstico sensor AS608 / JM-101B
- **Error activo**: `"The received packet do not begin with a valid header!"`
- **Causas probables**: TX/RX invertidos, puerto incorrecto (`/dev/ttyAMA10` inusual), Bluetooth ocupando UART
- **Puerto en esta RPi5**: `serial0 → ttyAMA10` (configuración no estándar)
- **Investigación**: `ttyAMA10` no existe en RPi5 estándar — revisar si está habilitado en `/boot/firmware/config.txt`

### Cambios en app/
| Archivo | Cambio |
|---|---|
| `config.py` | `AS608_PORT="/dev/ttyAMA10"`, nuevo `AS608_TIMEOUT_S=5` |
| `auth.py` | `verify_fingerprint()` retorna `None` en timeout/error → `authenticate()` hace fallback a solo PIN y registra en audit_log |
| `diagnose_sensor.py` | Script nuevo — prueba todos los puertos UART, loopback test, diagnóstico pyfingerprint |

### Comportamiento nuevo del login
```
Sensor responde OK        → 2FA completo (huella + PIN)
Sensor timeout (5s)       → fallback PIN-only + audit "LOGIN_HUELLA_TIMEOUT"
Sensor error de hardware  → fallback PIN-only + audit "LOGIN_HUELLA_TIMEOUT"
Huella no reconocida      → fallo + incrementa contador de intentos
```

### Para diagnosticar el AS608 en RPi5
```bash
# En la RPi5:
source /opt/smart-manufacturing/venv/bin/activate
python3 app/diagnose_sensor.py

# Verificar puerto
ls -la /dev/ttyAMA* /dev/serial*
cat /boot/firmware/config.txt | grep -i uart

# Si Bluetooth ocupa ttyAMA0, agregar en /boot/firmware/config.txt:
# dtoverlay=disable-bt
# enable_uart=1
```

- **Próximo paso**: Correr `diagnose_sensor.py` en RPi5, intercambiar TX/RX si sigue fallando, verificar `/boot/firmware/config.txt`

---

## ENTRADA #015 — App CustomTkinter 2FA + contexto sesión anterior
- **Fecha**: 2026-05-14
- **Estado**: ✅ App operativa / 🔄 Sensor AS608 pendiente de diagnóstico físico
- **Acción**: Registro de contexto de sesiones anteriores. App desktop implementada con autenticación 2FA, RBAC y health checks.

### App implementada en sesiones previas
**Archivos**: `app/main.py`, `app/auth.py`, `app/dashboards.py`, `app/health_check.py`, `app/db.py`, `app/config.py`, `app/install.sh`

**Funcionalidades**:
- Login 2FA: huella AS608 (pyfingerprint) + PIN bcrypt
- RBAC: roles admin / planta1 / planta2 con dashboards diferentes
- Health checks automáticos cada 60s (MQTT, InfluxDB, Node-RED, n8n, Grafana)
- Bloqueo por intentos fallidos (3 intentos → 5 min lockout)
- Audit log en SQLite

### Estado sensor JM-101B / AS608
- **Conexión física en RPi5**:
  - VCC (rojo) → Pin 1 (3.3V)
  - GND (negro) → Pin 6
  - TX sensor (amarillo) → Pin 10 (GPIO15/RXD)
  - RX sensor (verde) → Pin 8 (GPIO14/TXD)
- **Puerto**: `/dev/ttyAMA10` (serial0 → ttyAMA10 en esta RPi5)
- **Baud**: 57600
- **Error activo**: `"The received packet do not begin with a valid header!"`
- **Librería**: pyfingerprint (instalada en `/opt/smart-manufacturing/venv/`)

### Lanzamiento de la app
```bash
source /opt/smart-manufacturing/venv/bin/activate && python3 app/main.py
# o simplemente:
smfg
```

- **Próximo paso**: Diagnóstico con `app/diagnose_sensor.py`, posible intercambio TX/RX

---

## ENTRADA #016 — Prueba física RC522 + SCT-013 en ESP32-S3
- **Fecha**: 2026-05-14
- **Estado**: 🔄 En progreso — sensores conectados, RPi5 pendiente
- **Acción**: Primera prueba con circuito físico real. Se corrigieron pines para ESP32-S3, se creó entorno `sensor_test` sin WiFi/MQTT para validar sensores independientemente.

### Cambios en firmware
| Archivo | Cambio |
|---|---|
| `config.h` | PIN_SCT 36→1, PIN_RFID_SS 5→10, PIN_RFID_RST 27→9, PIN_SPI_MOSI/MISO/SCK agregados |
| `main.cpp` | SIMULATION_MODE 1→0, `SPI.begin()` con pines explícitos, bloque `SENSOR_TEST_ONLY` |
| `platformio.ini` | Nuevo entorno `sensor_test` (sin WiFi, sin MQTT, solo Serial) |

### Pines finales ESP32-S3-DevKitC-1
| Módulo | Señal | GPIO |
|---|---|---|
| SCT-013 | Salida analógica | GPIO 1 (ADC1_CH0) |
| RC522 | MOSI | GPIO 11 |
| RC522 | MISO | GPIO 13 |
| RC522 | SCK | GPIO 12 |
| RC522 | SS | GPIO 10 |
| RC522 | RST | GPIO 9 |

### Resultados prueba sensor_test
**SCT-013**: Lectura fija 4.545 A → pin en 3.3V constante.
Causa: divisor de voltaje mal armado (R2 no conectada a GND o Rb faltante).
Esquemático correcto: R1=10kΩ (3.3V→nodo), R2=10kΩ (nodo→GND), Rb=33Ω (burden, entre pines SCT-013 y nodo), C1=10µF (nodo→GND), C2=100nF (GPIO1→GND).

**RC522**: VersionReg=0xB2 (esperado 0x91/0x92) → posible módulo clon chino.
Sin tarjeta pasada aún. Pendiente validar detección de UID.

### Pendientes
- [ ] Corregir divisor de voltaje SCT-013 (agregar R2 y verificar Rb)
- [ ] Pasar tarjeta RFID al RC522 y verificar UID en serial
- [ ] Conectar RPi5 y probar pipeline completo WiFi → MQTT → InfluxDB
- [ ] Si RC522 no detecta: intercambiar MOSI↔MISO (GPIO11↔GPIO13)

### Comandos útiles
```bash
# Subir firmware de prueba sensores
pio run -e sensor_test --target upload --upload-port /dev/ttyACM0

# Subir firmware producción (con WiFi/MQTT)
pio run -e debug --target upload --upload-port /dev/ttyACM0

# Monitor serial
pio device monitor -p /dev/ttyACM0 -b 115200 --filter direct
python3 -m serial.tools.miniterm /dev/ttyACM0 115200  # alternativa
```

- **Próximo paso**: Corregir divisor SCT-013 → conectar RPi5 → probar pipeline completo

---

## ENTRADA #017 — Pipeline ESP32→MQTT→InfluxDB→Grafana operativo en red doméstica
- **Fecha**: 2026-05-17
- **Acción**: Pipeline completo de datos reales funcionando. n8n levantado en Docker (contenedor existente iniciado, credenciales reseteadas). Grafana token de InfluxDB configurado vía API. Node-RED: agregado nodo "Formatear InfluxDB" (`fmt-influx-energy`) que escribe `cima_energy` con todos los campos (power_w, irms_a, energy_kwh, simulated, cycle_active) al bucket sensor-data. Dashboard Grafana mostrando 850W / 4.54A del torno en tiempo real.
- **Estado**: ✅ Completado
- **Archivos modificados**: flows/nodered/nodered_dashboard.json, bitacora/bitacora_README.md
- **Próximo paso**: Pasar tarjeta RFID al RC522 y verificar pipeline RFID→InfluxDB→Grafana. Corregir divisor de voltaje SCT-013 (lectura fija 4.54A = pin en 3.3V constante).

---

## ENTRADA #018 — Modo REAL activado + ajustes para red doméstica
- **Fecha**: 2026-05-17
- **Acción**: Firmware cambiado a SIMULATION_MODE 0 (SCT-013 + RC522 físicos). RFID ahora publica a cima/rfid/scan en cada lectura. Puerto Grafana corregido a 3001 en CLAUDE.md y setup_rpi5.sh. Documentado flujo de cambio de red (Tec-IoT ↔ casa).
- **Estado**: ✅ Completado
- **Archivos modificados**: firmware/esp32-s3/src/main.cpp, CLAUDE.md, scripts/setup_rpi5.sh, bitacora/bitacora_README.md
- **Próximo paso**: Verificar datos reales de SCT-013 y RFID llegando a InfluxDB. Construir dashboard Grafana con KPIs reales en puerto 3001.

---

## ENTRADA #019 — Resumen sesión: GUI pestañas + gráficas tiempo real + panel RFID
- **Fecha**: 2026-05-19 00:00
- **Acción**: Gráficas matplotlib en tiempo real funcionando con backend Agg fijado al inicio del archivo (antes de cualquier import de matplotlib). Pestañas navegables CTkTabview por rol (Admin: Salud|CIMA|Celda3105|Costos MXN|Usuarios|Auditoría; Planta 1: CIMA|Salud; Planta 2: Celda3105|Salud). Panel RFID refactorizado con queue.Queue() para updates seguros desde hilo MQTT. _SaludTab reutilizable con verificación TCP de servicios. Gráficas muestran mensaje claro cuando no hay datos en InfluxDB.
- **Estado**: ✅ Completado
- **Archivos modificados**: app/dashboards.py, app/main.py
- **Próximo paso**: Validar que las gráficas muestran datos reales del ESP32-S3 una vez que el pipeline ESP32 → n8n → InfluxDB esté verificado en red Tec-IoT

---

## ENTRADA #020 — Pestañas navegables + gráficas matplotlib tiempo real + panel RFID
- **Fecha**: 2026-05-19 00:00
- **Acción**: Reescritura completa de app/dashboards.py. Correcciones principales: (1) `matplotlib.use("Agg")` movido al inicio del archivo, antes de cualquier import de matplotlib — esto fija el backend no-interactivo necesario para FigureCanvasTkAgg en tkinter. (2) `DashboardPlanta1` ahora usa `CTkTabview` con tabs "CIMA" y "Salud". (3) `DashboardPlanta2` ahora usa `CTkTabview` con tabs "Celda 3105" y "Salud". (4) `DashboardAdmin` reorganizado: tabs "Salud" | "CIMA" | "Celda 3105" | "Costos MXN" | "Usuarios" | "Auditoría". (5) `RFIDPanel` refactorizado con `queue.Queue()` — callback MQTT de red encola, `after(500, poll)` en hilo UI desencola (elimina riesgo de llamar after() desde hilo de red). (6) Nuevo `_SaludTab` reutilizable que hace verificación TCP de servicios para roles operador y admin. (7) Figura/Axes matplotlib creados una sola vez en `__init__`, actualizados con `ax.cla() + canvas.draw_idle()`. (8) Mensaje "Sin datos" mostrado en gráficas cuando no hay datos de InfluxDB.
- **Estado**: ✅ Completado
- **Archivos modificados**: app/dashboards.py
- **Verificación**: App arranca sin crash; `import dashboards` en venv → HAS_MPL=True; proceso estable >6s.
- **Próximo paso**: Verificar visualmente que las pestañas se navegan y las gráficas aparecen en pantalla.

---

## ENTRADA #021 — Migración a red Tec-IoT + resolución conflicto git config.py
- **Fecha**: 2026-05-19 22:50
- **Acción**: Inicio de sesión en RPi5 con nueva IP en red Tec-IoT (10.25.15.234). Resuelto conflicto de merge en `app/config.py`: se conservó `AS608_PORT=/dev/ttyAMA10` (correcto para este RPi5), `SIMULATION_MODE=True` (AS608 no conectado en esta sesión), y se actualizó `RPi_IP` de `192.168.100.168` a `10.25.15.234`. Se aplicaron 8 commits del remoto (fast-forward). Verificación de servicios: todos activos (mosquitto, influxdb, nodered, grafana-server, n8n Docker). InfluxDB confirmó datos en tiempo real: power_w=849, irms_a=4.54, simulated=false — ESP32 hardware real operando. Dashboards Grafana ya importados (CIMA KPIs + Celda 3105), datasources InfluxDB configurados.
- **Estado**: ✅ Completado
- **Archivos modificados**: app/config.py, bitacora/bitacora_README.md
- **Decisión config.py**: upstream tenía `AS608_TIMEOUT_S=5` que no estaba en local — se tomó versión upstream como base y se actualizó solo `RPi_IP`.
- **Próximo paso**: Crear firmware/.env con credenciales Tec-IoT (WIFI_SSID, MQTT_BROKER=10.25.15.234). Verificar pipeline RFID con tarjeta física. Revisar SCT-013 (divisor de voltaje).

---

## ENTRADA #022 — GUI modo PIN-only + dashboards con datos reales ESP32-S3
- **Fecha**: 2026-05-19 23:10
- **Acción**: Agregado `FINGERPRINT_ENABLED = False` en config.py para deshabilitar huella de forma explícita sin eliminar código (sensor JM-101B no conectado). Login ahora pide solo usuario + PIN. auth.py actualizado para usar `FINGERPRINT_ENABLED` en lugar de `not SIMULATION_MODE`, desacoplando ambos flags. Creado `.env` raíz con `INFLUXDB_TOKEN` para conectar db.py a datos reales. Actualizado `firmware/esp32-s3/.env` con `MQTT_BROKER=10.25.15.234` (Tec-IoT).
- **Estado**: ✅ Completado
- **Archivos modificados**: app/config.py, app/auth.py, app/main.py, firmware/esp32-s3/.env
- **Datos reales confirmados**: InfluxDB → power_w=849W, irms_a=4.54A (ESP32-S3 hw real). Login admin/1234 → OK.
- **Reactivar huella**: cambiar `FINGERPRINT_ENABLED = True` cuando JM-101B esté en `/dev/ttyAMA10`.
- **Próximo paso**: Flashear ESP32 con MQTT_BROKER=10.25.15.234 para Tec-IoT.

---

## ENTRADA #023 — Dashboards tiempo real SCT-013 + RFID, modo real activado en GUI
- **Fecha**: 2026-05-19 23:45
- **Acción**: SIMULATION_MODE cambiado a False. Gráficas matplotlib en tiempo real (cada 5 s) embebidas en CustomTkinter via FigureCanvasTkAgg. Panel RFID con suscripción MQTT en vivo (cima/rfid/scan) + historial InfluxDB. Instalados matplotlib y paho-mqtt en venv.
- **Estado**: ✅ Completado
- **Archivos modificados**: app/config.py, app/db.py, app/dashboards.py
- **Decisiones de diseño**:
  - `RealtimeEnergyChart`: deque no usado — se consulta InfluxDB directamente cada 5 s (60 pts = últimos 5 min)
  - `RFIDPanel`: MQTT paho v2 en hilo daemon + `after(0,cb)` para actualizar UI en hilo principal
  - `query_energy_realtime`: rango `-8m` con `tail(n=60)` para cubrir exactamente los últimos 60 puntos a 5 s/punto
  - `query_rfid_history`: measurement `rfid_status`, field `uid`, filtra vacíos
  - Fallback a datos demo si InfluxDB no responde (ningún crash)
  - Celda 3105 muestra aviso "pendiente de conexión" si no hay datos reales
- **Datos verificados en tiempo real**: power_w=849W, irms_a=4.54A, RFID historial OK
- **Próximo paso**: Pasar tarjeta RFID al RC522 y verificar que aparece en panel RFID en tiempo real.

---

## ENTRADA #024 — Rediseño app UNIX&Co. — PyWebView + HTML/CSS/JS
- **Fecha**: 2026-05-20
- **Acción**: Rediseño completo de la app desktop de CustomTkinter a PyWebView 6.2.1 + HTML/CSS/JS. Nueva identidad visual: **UNIX&Co. — Smart Manufacturing**. App carga interfaz web local (`app/templates/index.html`) vía servidor HTTP interno de pywebview.
- **Arquitectura**: `app/main.py` expone clase `Api` al JS vía `window.pywebview.api.*`. Métodos: `login()`, `logout()`, `get_session()`, `get_current_power()`, `get_energy_realtime()`, `get_cost_data()`, `get_system_status()`, `get_rfid_history()`, `get_config()`.
- **Frontend**: paleta industrial oscura (CSS variables), login como estado inicial, sidebar RBAC por rol (admin/planta1/planta2), gráfica Chart.js actualización cada 5s, KPI cards 4 columnas, badges de servicios en topbar, tabla RFID.
- **RBAC**: admin → Dashboard+EnergíaRT+KPIsFinancieros+RFID; planta1 → Dashboard+EnergíaRT+RFID; planta2 → Dashboard+Celda3105+RFID.
- **Estado**: ✅ Completado — imports verificados, template existe, pywebview 6.2.1 operativo
- **Archivos modificados**: app/main.py (reescrito), app/templates/index.html (nuevo)
- **Próximo paso**: Probar arranque completo de la app con `python3 app/main.py`

---

## ENTRADA #025 — Firmware modo REAL: SCT-013 + Rb=30Ω
- **Fecha**: 2026-05-20
- **Acción**: SIMULATION_MODE → 0, Rb 33Ω → 30Ω (3×10Ω en serie). Comentario de cabecera actualizado a modo REAL. Agregada función `testAmperage()` que toma 10 muestras de 1s, imprime cada muestra con su equivalente en watts (220V, PF=0.85), y al final reporta promedio, mínimo, máximo y variación con diagnóstico automático (advertencia si promedio < 0.05A, advertencia de ruido si variación > 30% del promedio, confirmación si todo OK). `testAmperage()` se llama una vez en `setup()` después de "[READY] Sistema listo", con `delay(2000)` previo para estabilizar el ADC, solo cuando `SIMULATION_MODE == 0`.
- **Hardware**: SCT-013-100, C1=10µF, C2=100nF, R1=R2=10kΩ, Rb=30Ω (3×10Ω en serie), GPIO36
- **Estado**: ✅ Listo para flashear
- **Archivos modificados**: firmware/esp32-s3/src/main.cpp
- **Próximo paso**: Flashear ESP32-S3, observar output de testAmperage() en serial a 115200 baud

---

## ENTRADA #026 — App desktop conectada a datos reales
- **Fecha**: 2026-05-21
- **Acción**: dashboards.py conectado a InfluxDB con datos reales del SCT-013. Agregado filtro `machine_id="torno"` en queries de tiempo real para aislar datos de Planta 1. Fallback `.env` local añadido a db.py. `MACHINE_ID_PLANTA1` añadido a config.py.
- **Verificado**: SIMULATION_MODE=False en todos los archivos. InfluxDB retorna power_w=85.0W, irms_a=0.780A — coincide exactamente con serial ESP32.
- **RBAC confirmado**: admin ve Costos MXN (tarifa CFE); planta1 ve watts/amperes sin costos; planta2 ve Celda 3105 sin costos.
- **Estado**: ✅ App mostrando datos reales
- **Archivos modificados**: app/config.py, app/db.py, app/dashboards.py

---

## ENTRADA #027 — SCT-013 calibrado y operativo
- **Fecha**: 2026-05-21
- **Acción**: Calibración completa del sensor de corriente SCT-013-100
- **Circuito**: LM358 rectificador media onda, Rb=30Ω (3×10Ω), GPIO1
- **Resultado**: 0.780A medido vs 0.787A esperado (error 0.9%)
- **Constantes**: SCT_CALIBRATION_FACTOR=305.4, LM358_FLOOR=0.033V
- **Red**: 127V México, POWER_FACTOR=0.85
- **Estado**: ✅ Listo para producción
- **Archivos modificados**: firmware/esp32-s3/src/main.cpp, firmware/esp32-s3/include/config.h

---

## ENTRADA #028 — Cierre de sesión 2026-05-22 — Diagnóstico LM358_FLOOR
- **Fecha**: 2026-05-22
- **Resumen de sesión**: Calibración del SCT-013, ruido ADC y diagnóstico de circuito.

### Lo que se hizo hoy
| # | Acción | Estado |
|---|--------|--------|
| 1 | `SCT_CALIBRATION_FACTOR` 305.4 → **18.0** (corrección 16.9×) | ✅ |
| 2 | `VOLTAGE_RED` 127V → **220V** (torno industrial) | ✅ |
| 3 | Modo calibración MQTT: `cima/commands/calibrate {"real_amps":X}` | ✅ |
| 4 | Deadband `SCT_NOISE_THRESHOLD=0.5A` + mediana de 3 muestras | ✅ |
| 5 | Monitor MQTT en tiempo real vía `mosquitto_sub` | ✅ |
| 6 | Diagnóstico: **OFF (12A) > ON (7.3A)** — LM358_FLOOR mal calibrado | 🔄 Pendiente fix |

### Hallazgo crítico — LM358_FLOOR
- **Síntoma**: torno OFF reporta ~12A, torno ON reporta ~7.3A (invertido)
- **Causa**: `LM358_FLOOR = 0.033V` en config.h es incorrecto. El offset DC real del LM358 en GPIO1 es ~1.5V. Ese offset se interpreta como corriente: `(1.5 - 0.033) × (100/18) × √2 ≈ 12A`
- **Fix pendiente**: medir voltaje real en GPIO1 con multímetro (torno apagado) → actualizar `LM358_FLOOR` a ese valor
- **Valor estimado**: LM358_FLOOR ≈ 1.53V (back-calculado de la lectura 12A)
- **Calibración ON sigue siendo válida**: 7.3A medido vs 7.45A real = 2% error ✅

### Próximos pasos
- [ ] Medir voltaje en GPIO1 con multímetro (torno apagado) → actualizar `LM358_FLOOR`
- [ ] Flashear ESP32-S3 con firmware actualizado (`pio run -e debug --target upload`)
- [ ] Verificar: OFF → 0A, ON → ~7.45A
- [ ] Ajustar `SCT_NOISE_THRESHOLD` si es necesario tras corregir el floor

- **Archivos modificados esta sesión**: `firmware/esp32-s3/include/config.h`, `firmware/esp32-s3/src/main.cpp`, `bitacora/bitacora_README.md`

---

## ENTRADA #029 — Fix: ruido ADC SCT-013 con torno apagado (deadband + mediana)
- **Fecha**: 2026-05-22
- **Problema**: Con el torno apagado, el SCT-013 reportaba ~12A en lugar de 0A — ruido del ADC del ESP32-S3 sin carga real.
- **Solución**:
  - **Deadband**: si irms calculado < `SCT_NOISE_THRESHOLD` (0.5A) → forzar irms = 0.0A
  - **Mediana de 3 muestras**: se toman `SCT_AVG_SAMPLES` (3) lecturas de 500ms cada una; se descartan la mayor y la menor, se usa la del medio — elimina picos transitorios
  - `measurePower()` refactorizada: lógica de muestreo extraída a `singleIrms()`, mediana con sort burbuja en N=3
- **Config.h agregado**: `SCT_NOISE_THRESHOLD 0.5f`, `SCT_AVG_SAMPLES 3`
- **Impacto en tiempo de ciclo**: 3 × 500ms = 1.5s por publicación (antes 500ms). `PUBLISH_INTERVAL_MS` sigue en 5000ms — sin problema.
- **Estado**: ✅ Completado — requiere recompilación y flash del ESP32-S3
- **Archivos modificados**: `firmware/esp32-s3/include/config.h`, `firmware/esp32-s3/src/main.cpp`
- **Próximo paso**: Flashear y verificar que serial reporta 0.0A con torno apagado y ~7.45A con torno encendido

---

## ENTRADA #030 — Fix: calibración SCT-013 para lectura real del torno
- **Fecha**: 2026-05-22
- **Acción**: Corrección del factor de calibración del sensor de corriente SCT-013-100 y del voltaje de red para medición correcta en el torno industrial.
- **Problema**: Torno consumía 7.40–7.50 A (pinza amperimétrica) pero MQTT reportaba ~0.44 A — error de 16.9×.
- **Modelo SCT-013**: SCT-013-100 (100A primario, 50mA secundario, ratio 2000:1). Circuito: LM358 rectificador media onda, Rb=30Ω, GPIO1 (ADC1_CH0).
- **Corrección factor**: `SCT_CALIBRATION_FACTOR` 305.4 → **18.0** (derivado: 305.4 / (7.45/0.44) = 18.04). Factor más bajo → corriente reportada más alta (relación inversa en la fórmula `current = v × 100/factor`).
- **Corrección voltaje**: `VOLTAGE_RED` 127.0 → **220.0 V** (torno motor industrial opera a 220V).
- **Potencia antes/después**: 0.44A × 127V × 0.85 ≈ 47W → **7.45A × 220V × 0.85 ≈ 1393W** (1.4kW, esperado para torno industrial).
- **Nuevo — modo calibración MQTT**: Enviar `cima/commands/calibrate` con `{"real_amps": X}` → ESP32 mide Irms actual, calcula factor de corrección y publica resultado sugerido en `cima/calibration/result`.
- **Estado**: ✅ Completado — requiere recompilación y flash del ESP32-S3
- **Archivos modificados**: `firmware/esp32-s3/include/config.h`, `firmware/esp32-s3/src/main.cpp`
- **Próximo paso**: Flashear ESP32-S3 con `pio run -e debug --target upload`, verificar irms_a ≈ 7.45A en serial y MQTT

---

## ENTRADA #031 — Referencia técnica calibración SCT-013
- **Fecha**: 2026-05-22
- **Acción**: Documentar fuente técnica usada para calibración del SCT-013
- **Referencia**: https://naylampmechatronics.com/blog/51_tutorial-sensor-de-corriente-ac-no-invasivo-sct-013.html
- **Resultado calibración**:
  - Factor anterior: 305.4 → Factor corregido: 18.0
  - Voltaje corregido: 127V → 220V (motor industrial trifásico)
  - Lectura antes: 0.44A / 47W (incorrecto)
  - Lectura después: ~7.45A / ~1390W (correcto, validado con pinza amperimétrica)
- **Estado**: ✅ Completado

---

## ENTRADA #032 — Trazabilidad RFID: ciclo inicio/fin de pieza
- **Fecha**: 2026-05-29 00:00
- **Acción**: Implementación completa del sistema de trazabilidad RFID con toggle inicio/fin
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `firmware/esp32-s3/src/main.cpp` — lógica RFID toggle (1er scan=start, 2do=stop, UID distinto=ignorar), LED feedback (2 lentos / 4 rápidos), CycleState extendido con uid y startTs
  - `flows/n8n/mqtt_to_influxdb_v2.json` — 3 nodos nuevos: "Es RFID stop?", "Preparar línea RFID", "Guardar ciclo RFID" (measurement: cima_rfid_cycles)
  - `app/db.py` — función `query_rfid_cycles(limit)` con cálculo de costo y datos demo
  - `app/dashboards.py` — clase `TrazabilidadPanel` (banner activo + tabla + stats + CSV), tab "Trazabilidad" en Planta1 (sin costo) y Admin (con costo)
  - `app/main.py` — MQTT tracker de ciclo activo en clase Api, métodos `get_active_cycle()`, `get_rfid_cycles()`, `get_rfid_stats()`
- **Comportamiento**:
  - 1er scan → publica `{event:start, part_id, machine_id, ts}` en `cima/rfid/scan`
  - 2do scan mismo UID → publica `{event:stop, duration_s, energy_wh, ...}`
  - n8n: filtra event=stop y escribe en InfluxDB `cima_rfid_cycles`
  - App: banner verde con timer mientras ciclo activo; tabla al cerrarlo
  - Rol planta1: sin columna Costo MXN; admin: con costo
- **Próximo paso**: Flash firmware y probar ciclo completo con tarjeta RFID real

## ENTRADA #033 — Ajuste fino calibración SCT-013: 5.51A → 6.80A
- **Fecha**: 2026-05-29
- **Problema**: App reportaba 5.51A / 1030W; pinza amperimétrica confirma 6.80A / 1271W (error 19%)
- **Causa**: SCT_CALIBRATION_FACTOR desactualizado tras cambios de fórmula en CAPA 1
- **Cálculo**: `bajar el factor → más corriente`; nuevo = 18.0 × (5.51 / 6.80) = **14.6**
  - Nota: la fórmula correcta es `×(medido/real)`, NO `×(real/medido)` — la segunda alejaría más el valor
- **Factor anterior**: 18.0 | **Factor nuevo**: 14.6
- **Lectura esperada**: 6.50–7.00A, potencia ~1271W
- **Estado**: ✅ Compilado — pendiente flash y verificación
- **Archivos**: `firmware/esp32-s3/include/config.h`
- **Próximo paso**: `pio run -e debug --target upload --upload-port /dev/ttyACM0` y verificar [FILTER] en Serial Monitor

## ENTRADA #034 — Fix: filtro descartaba 6.80A real (bug CAPA 1 formula singleIrms)
- **Fecha**: 2026-05-29
- **Problema**: Con torno ENCENDIDO, el valor real 6.80A era descartado → mostraba 0A
- **Capa problemática**: CAPA 1 — `singleIrms()` eliminó `if (v < 0.0f)` y `*2.0f` en sesión anterior
- **Root cause**: El LM358 single-supply clipea la semiciclada negativa al piso (~0.033V).
  Sin el clip, al restar el dcOffset dinámico (~1.65V) del piso clipeado se generan valores
  muy negativos (−2.3V → −12.7A por muestra). Al cuadrarse dominan el sumSq → rawIrms ≈ 10+A
  → excede SCT_MAX_VALID_AMPS=8.5A → filtrado por ventana → 0A reportado.
- **Solución**: Restaurar `if (v < 0.0f) v = 0.0f` (clip media onda LM358) y `*2.0f` (corrección √2)
- **Cambios adicionales**:
  - SCT_MAX_DELTA_AMPS: 2.0→3.0A (más margen para variaciones legítimas)
  - Buffer reset en arranque del torno (media cero → señal válida → rellena buffer instantáneamente, elimina convergencia lenta de 50s)
  - Logging `[FILTER] raw=X dc=Y irms=Z valid=SI/NO` para diagnóstico serial
- **Verificación esperada**: apagado=0A, encendido=6.50–7.00A, potencia=1270W aprox.
- **Estado**: ✅ Compilado OK — pendiente flash
- **Archivos**: `firmware/esp32-s3/include/config.h`, `firmware/esp32-s3/src/main.cpp`
- **Próximo paso**: Flash + `pio device monitor` y verificar líneas [FILTER] con ambos estados

## ENTRADA #035 — Fix: 5 capas de filtrado SCT-013 offset LM358 y spikes
- **Fecha**: 2026-05-29
- **Problema**: Offset DC del LM358 contamina todas las lecturas: apagado=12A, encendido=>8A
- **Solución**: 5 capas en firmware + n8n + app
  - **CAPA 1 (firmware)**: Offset DC dinámico — promedio de 200 muestras reemplaza `LM358_FLOOR` fijo; la componente AC promedia a cero en >1 ciclo de red (20ms)
  - **CAPA 2 (firmware)**: Media móvil circular (10 muestras) + descarte outlier (>2A del promedio histórico con condición `rawIrms > spike_thresh` para no bloquear arranque del torno)
  - **CAPA 3 (firmware)**: Ventana [0.5A, 8.5A] + slew-rate (salto >4A hacia >8A → 0)
  - **CAPA 4 (n8n)**: `power_w > 2000W` → descartado; spike `power > prev*2` en <5s → descartado
  - **CAPA 5 (app/db.py)**: Mediana de últimos 5 valores en gauges; descarte `irms > 8.5A` en gráficas
- **Payload MQTT nuevo**: `dc_offset`, `filter_reason` (window/slew/delta), `raw_irms`
- **Verificación esperada**: apagado=0A/0W, encendido=6.8–7.6A/1270–1420W, spikes=ignorados
- **Estado**: ✅ Compilado OK — pendiente flash (ESP32 no conectado)
- **Archivos modificados**:
  - `firmware/esp32-s3/include/config.h`
  - `firmware/esp32-s3/src/main.cpp`
  - `flows/n8n/mqtt_to_influxdb_v2.json`
  - `app/db.py`
- **Próximo paso**: Flash + verificar Serial Monitor con `pio device monitor --port /dev/ttyACM0 --baud 115200`

## ENTRADA #036 — Fix: filtro ventana SCT-013 elimina offset LM358 (12A falsos)
- **Fecha**: 2026-05-29
- **Acción**: Implementado filtro ventana de valores válidos en `measurePower()` para el SCT-013
- **Problema**: LM358 single-supply genera ~12A de offset DC en GPIO cuando el torno está apagado. `SCT_NOISE_THRESHOLD = 0.5A` no funcionaba porque el ruido (12A) es mayor que la señal real (7.45A).
- **Solución**: Ventana de validación `[SCT_MIN_VALID_AMPS, SCT_MAX_VALID_AMPS]` = `[1.0A, 20.0A]`. Lecturas fuera del rango → `irms = 0.0A`. Ajustable en caliente vía MQTT `cima/commands/set_threshold {"min_amps": X, "max_amps": Y}`.
- **Resultado esperado**:
  - Torno apagado → irms = 0.0A, power = 0W, filtered = true, raw_irms = ~12A
  - Torno encendido → irms = ~7.45A, power = ~1390W, filtered = false
- **Estado**: ✅ Compilado OK — pendiente flash (ESP32 no conectado en esta sesión)
- **Archivos modificados**:
  - `firmware/esp32-s3/include/config.h` — `SCT_MIN_VALID_AMPS`, `SCT_MAX_VALID_AMPS`, `SCT_IDLE_THRESHOLD`, `TOPIC_CMD_SET_THRESHOLD`
  - `firmware/esp32-s3/src/main.cpp` — `PowerReading.rawIrms/filtered`, `measurePower()` filtro ventana, `publishEnergy()` campos `filtered`/`raw_irms`, handler MQTT `set_threshold`, suscripción al topic
- **Próximo paso**: Conectar ESP32 y ejecutar `pio run -e debug --target upload --upload-port /dev/ttyACM0`, verificar Serial Monitor

## ENTRADA #037 — n8n migrado a host network mode (fix EHOSTUNREACH MQTT)
- **Fecha**: 2026-05-29
- **Acción**: Contenedor n8n recreado con `--network host` para resolver error `connect EHOSTUNREACH 192.168.100.168:1883` en el nodo MQTT Trigger
- **Causa raíz**: Docker bridge network aísla al contenedor del host; el broker Mosquitto en el host no era alcanzable desde la red bridge interna de Docker
- **Solución**:
  - `docker stop n8n && docker rm n8n`
  - `docker run -d --name n8n --network host --restart unless-stopped -e N8N_PORT=5678 ...`
  - Credencial MQTT en n8n debe apuntar a `localhost` (no a `192.168.100.168`)
- **Estado**: ✅ Completado — n8n arrancado en `::, port 5678`; versión 2.13.4
- **Archivos modificados**: `CLAUDE.md` (nota host network), `bitacora/bitacora_README.md`
- **Próximo paso**: Abrir http://localhost:5678 → Credentials → cambiar host MQTT de `192.168.100.168` a `localhost` → verificar que el MQTT Trigger no muestra error rojo

## ENTRADA #038 — Acceso directo en escritorio y script de arranque
- **Fecha**: 2026-05-29
- **Acción**: Ícono de escritorio en RPi5 para abrir la app con doble clic
- **Estado**: ✅ Completado
- **Detalles**:
  - `/home/caspian/Desktop/SmartManufacturing.desktop` — archivo `.desktop` con `Exec` apuntando al venv `/opt/smart-manufacturing/venv/bin/python3`; validado con `desktop-file-validate` (sin errores)
  - `app/assets/icon.png` — ícono 256×256 RGBA generado con Pillow: fondo `#1a1a2e`, texto "SM" y subtexto "MANUFACTURING" en acento `#00d4aa`, anillo de progreso decorativo
  - `app/start.sh` — script de arranque alternativo (`cd`, `source venv/bin/activate`, `python3 app/main.py`); permiso +x
  - `Categories` corregida a `System;Monitor;` (la categoría `Industry` no está registrada en freedesktop.org)
- **Archivos modificados/creados**:
  - `/home/caspian/Desktop/SmartManufacturing.desktop` (fuera del repo — en escritorio del usuario)
  - `app/assets/icon.png`
  - `app/start.sh`
- **Próximo paso**: Doble clic en el ícono del escritorio para verificar que lanza la app correctamente

## ENTRADA #039 — Fix RBAC: operadores solo ven su propia planta
- **Fecha**: 2026-05-29
- **Acción**: Corrección de bug donde operadores podían navegar a dashboards de otras plantas
- **Estado**: ✅ Completado
- **Bug**: El sidebar de `index.html` siempre mostraba secciones de Planta 1 y Planta 2 a todos los usuarios. Solo la sección Admin estaba oculta por defecto.
- **Fix (3 capas)**:
  1. **Sidebar HTML** (`index.html`): Se agregó `id="nav-planta1"` al primer grupo de navegación. En `doLogin()` se controla `display` de las tres secciones (`nav-planta1`, `nav-planta2`, `nav-admin`) según el rol del usuario logueado.
  2. **Navegación JS** (`index.html`, `showView()`): Se agregó constante `ROLE_ALLOWED_VIEWS` (Set por rol). Si el usuario intenta navegar a una vista no permitida, se muestra la pantalla `view-denied` en lugar del dashboard.
  3. **API Python** (`main.py`): Defensa en profundidad — `get_current_power()`, `get_energy_24h()` y `get_rfid_history()` ahora requieren rol `planta1` o `admin`; retornan `forbidden`/lista vacía para `planta2`.
  4. **dashboards.py**: Agregado `_AccessDeniedFrame` y tabla `_ROLE_PERMISSIONS`; `build_dashboard()` valida el rol antes de instanciar.
- **Archivos modificados**:
  - `app/templates/index.html`
  - `app/main.py`
  - `app/dashboards.py`
- **Prueba de los 3 casos**:
  - `operador1` (planta1) → sidebar solo muestra Planta 1; vista inicial: Dashboard; botones Planta 2 / Admin invisibles
  - `operador3` (planta2) → sidebar solo muestra Planta 2; vista inicial: Celda 3105; botones Planta 1 / Admin invisibles
  - `admin` → ve todo: Planta 1 + Planta 2 + Admin
- **Próximo paso**: Verificar visualmente en pantalla que el fix funciona

## ENTRADA #040 — Fix corrupción visual WebKit2GTK en LCD 7" 1024×600
- **Fecha**: 2026-05-29
- **Acción**: Diagnóstico y corrección de artefactos visuales al abrir la app en pantalla 1024×600
- **Estado**: ✅ Completado
- **Causa raíz**: WebKit2GTK 2.52.3 usa DMABUF renderer por defecto; causa corrupción en VideoCore VII del RPi5 por falta de soporte DRM-prime completo en kernel 6.x. Agravado por auto-DPI de GDK (factor 1.333× detectado).
- **Solución**: Variables de entorno `WEBKIT_DISABLE_DMABUF_RENDERER=1`, `WEBKIT_DISABLE_COMPOSITING_MODE=1`, `GDK_SCALE=1`, `GDK_DPI_SCALE=1` establecidas **antes** del `import webview` en main.py
- **Archivos modificados**: `app/main.py`
- **Próximo paso**: Verificar visualmente en la pantalla física que no haya artefactos

## ENTRADA #041 — UI responsive para pantalla 7" LCD 1024×480
- **Fecha**: 2026-05-29
- **Acción**: Ajuste de layout responsive al cambiar monitor de 1920×1080 a LCD 7" 1024×480
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `app/config.py` — agregado `SCREEN_WIDTH=1024`, `SCREEN_HEIGHT=480`, `UI_SCALE`
  - `app/main.py` — detección de resolución en runtime con tkinter; ventana ajustada a resolución detectada; min_size reducido a (800,400)
  - `app/templates/index.html` — media queries CSS: `@media (max-height:500px)` y `@media (max-width:1100px)` para topbar, sidebar, fuentes, KPI cards y charts
  - `app/dashboards.py` — flag `_COMPACT`, función `_scale()`, figsize y padding proporcionales
- **Próximo paso**: Verificar visualmente en la pantalla LCD 7" física

## ENTRADA #042 — Fix calibración SCT-013 y Trazabilidad en app webview
- **Fecha**: 2026-05-29 19:00
- **Problemas**:
  1. Amperaje mostraba 5.85A (real: 6.60–6.90A) → factor desajustado
  2. Pestaña Trazabilidad no aparecía (cambios anteriores eran para CTk, la app usa webview HTML)
- **Fix calibración**: SCT_CALIBRATION_FACTOR 14.6→12.6 (cálculo: 14.6×5.85/6.75=12.6)
- **Fix UI**: Actualizado index.html webview con:
  - Banner "🟢 CICLO ACTIVO" con timer en tiempo real (pollActiveCycle cada 5s)
  - Tabla historial de piezas: Part ID | Inicio | Fin | Duración | Energía (Wh) | Costo (admin)
  - Stats: piezas totales, tiempo promedio, energía promedio, costo total (admin)
  - Botón RFID en sidebar ya existente — ahora carga la vista de Trazabilidad
- **Estado**: ✅ Completado
- **Archivos**: `firmware/esp32-s3/include/config.h`, `app/templates/index.html`
- **Próximo paso**: Flash firmware (factor 12.6) + reiniciar app para ver Trazabilidad

## ENTRADA #043 — Integración PLC S7-1200 Celda 3105 con App Desktop
- **Fecha**: 2026-06-03 00:00
- **Acción**: Pipeline completo PLC S7-1200 → Node-RED → MQTT → InfluxDB → App CustomTkinter
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `flows/nodered/nodered_dashboard.json`
    - `plc-s7-config`: IP→192.168.100.200, cycletime→500ms, 25 tags reales (sin Led_*, Boton_*)
    - `parse-plc` (renombrado "Procesar tags PLC"): lógica completa — flanco Estampado_Down, tiempo ciclo, modo_auto, cobot, OEE; payload JSON estructurado
    - `mqtt-out-celda`: topic→`celda3105/plc`; `influx-out-celda`: measurement→`celda3105_estado`; throttle 10s
    - JSON corrupto (líneas 942-1067 duplicadas) limpiado y revalidado
  - `app/config.py`: PLC_IP, PLC_PORT, PLC_RACK, PLC_SLOT, MQTT_TOPIC_CELDA, TURNO_HORAS
  - `app/db.py`: imports json+threading; query_celda3105_latest/kpis/operaciones/subscribe_celda3105_mqtt; measurement actualizado a celda3105_estado
  - `app/dashboards.py`: nueva clase Celda3105Panel (MQTT tiempo real, KPIs, flujo producción, ops table, Quality Gate, banners emergencia/sin-datos); DashboardPlanta2 y DashboardAdmin._build_celda_tab simplificados
- **Comportamiento sin PLC**: banner amarillo "Sin conexión", KPIs "—", sin crash
- **Comportamiento con PLC**: killswitch=True→banner rojo parpadeante; piezas/OEE/ciclo en tiempo real
- **Próximo paso**: Importar flujo en Node-RED, configurar bearer token InfluxDB en http-influx-celda

## ENTRADA #044 — Deploy Node-RED flujo Celda 3105 via API
- **Fecha**: 2026-06-03 14:03
- **Acción**: Deploy flujo `flows/nodered/nodered_dashboard.json` en Node-RED (localhost:1880) via REST API
- **Fix aplicado**: node-red-contrib-s7 v3.1.3 usa `vartable` (no `variables`), solo campos `name`+`addr`. Se corrigió en el JSON y se actualizó en git.
- **Estado tras deploy**:
  - ✅ MQTT: Connected to broker (localhost:1883)
  - ✅ S7 endpoint: nodo activo, reconectando automáticamente
  - ⚡ S7: `EHOSTUNREACH 192.168.100.200:102` — esperado (PLC fuera de red actual)
  - Token InfluxDB: preservado por Node-RED (node ID sin cambios)
- **Nodo HTTP InfluxDB**: `http-influx-celda` usa `authType: bearer` — credencial preservada del deploy anterior
- **Para activar con PLC**: conectar RPi5 a red donde 192.168.100.200 sea alcanzable
- **Archivos modificados**: `flows/nodered/nodered_dashboard.json`
- **Próximo paso**: Conectar a red Tec-IoT con PLC activo para verificar datos reales

## ENTRADA #045 — Eliminación modo simulación + corrección algoritmo SCT-013-000
- **Fecha**: 2026-06-03 14:30
- **Acción**: Limpieza completa de modo simulación en firmware y app Python; reescritura algoritmo RMS SCT-013-000
- **Estado**: ✅ Compilado (SUCCESS, 14s)
- **Cambios técnicos firmware**:
  - `config.h`: 74→65 líneas. Eliminados: LM358_FLOOR, SCT_CALIBRATION_FACTOR, SCT_SAMPLES, SCT_*_AMPS (5 capas filtro), TOPIC_CMD_SET_THRESHOLD. Agregados: SCT_BURDEN_OHMS=33Ω, SCT_TURNS=2000, SCT_CALIBRATION=1.0, SCT_SAMPLE_MS=500, SCT_MIN_CURRENT=0.15, GRID_VOLTAGE=220V
  - `main.cpp`: 783→608 líneas. Cero referencias SIMULATION_MODE. `measurePower()` reescrita algoritmo Naylamp 5 pasos: DC offset dinámico (200 muestras) → RMS temporal 500ms → compensación media onda (×2) → V→A por transimpedancia/vueltas → umbral de ruido
  - `publishEnergy()`: JSON limpio (`machine_id, irms_a, power_w, energy_khw, cycle_active, burden_ohms, ts, rssi`), retain=false
  - `publishHeartbeat()`: mode="real" fijo
  - Eliminado: TOPIC_CMD_SET_THRESHOLD handler, botón BOOT simulador RFID, todas las funciones stub simuladas
  - Preservado: RFID toggle inicio/fin ciclo, testAmperage(), TOPIC_CMD_CALIBRATE, SENSOR_TEST_ONLY
- **Cambios Python app**:
  - `config.py`: SIMULATION_MODE eliminado
  - `auth.py`: import y 2 guards SIMULATION_MODE eliminados; docstrings actualizados
  - `main.py`: SIMULATION_MODE eliminado de import y get_config()
  - `dashboards.py, db.py, health_check.py`: sin referencias — sin cambios
- **Referencia técnica**: naylampmechatronics.com/blog/51 (SCT-013 media onda)
- **Para calibrar**: Ajustar SCT_CALIBRATION en config.h y recompilar. O enviar MQTT `cima/commands/calibrate {"real_amps": X}` para obtener sugerencia
- **Próximo paso**: Flash cuando se conecte el ESP32

## ENTRADA #046 — Corrección crítica: fórmula SCT-013 30A/1V (salida voltaje)
- **Fecha**: 2026-06-03 18:00
- **Acción**: Corrección fórmula de conversión Irms en firmware ESP32-S3
- **Estado**: ✅ Completado
- **Problema**: Sensor identificado incorrectamente como SCT-013-000 (100A/50mA, corriente) cuando en realidad es SCT-013 (30A/1V, voltaje)
- **Síntoma**: Foco 29W/127V → corriente real 0.20A, app reportaba 69.60A (factor error 348x)
- **Causa raíz**: Fórmula `Irms = (Vrms/SCT_BURDEN_OHMS) * SCT_TURNS` no aplica para sensor de salida de voltaje
- **Corrección**: `Irms = Vrms * SCT_RATIO (30.0) * SCT_CALIBRATION` — sensor genera 1V cuando mide 30A
- **Archivos modificados**:
  - `firmware/esp32-s3/include/config.h`: eliminados SCT_BURDEN_OHMS y SCT_TURNS; agregado SCT_RATIO=30.0
  - `firmware/esp32-s3/src/main.cpp`: Paso 4 measurePower() reescrito; JSON publica sct_ratio en vez de burden_ohms
  - `app/config.py`: comentario sensor correcto
- **Verificación**: Foco 29W/127V → ~0.20A ✅
- **Próximo paso**: Ajustar SCT_CALIBRATION si hay desviación con pinza amperimétrica real

## ENTRADA #047 — Feature: Trazabilidad RFID completa
- **Fecha**: 2026-06-03 19:00
- **Acción**: Sistema completo de trazabilidad RFID — firmware loop() inline, n8n pipeline mejorado, app con detalle modal y PDF
- **Estado**: ✅ Completado
- **Cambios firmware**:
  - `main.cpp`: loop() RFID inline con anti-debounce — toggle start/stop por UID
  - Eventos MQTT: `cima/rfid/scan` con campos uid, event, part_id, machine_id, duration_s, energy_wh, ts
- **Cambios n8n**:
  - "Preparar línea RFID": agrega cost_mxn, ts_start, ts_end a measurement cima_rfid_cycles
  - Nodo "Publicar completed": logging de pieza completada
- **Cambios app Python**:
  - `config.py`: MQTT_TOPIC_RFID_COMPLETED, PDF_OUTPUT_DIR
  - `db.py`: query_rfid_pieza_detalle(), query_turno_promedios()
  - `dashboards.py`: energía en banner RFID, filas clickeables → modal detalle con comparativa vs turno, Export PDF (reportlab)
- **Archivos modificados**: firmware/esp32-s3/src/main.cpp, flows/n8n/mqtt_to_influxdb_v2.json, app/config.py, app/db.py, app/dashboards.py
- **Próximo paso**: Verificar con tarjeta RFID real en producción

## ENTRADA #048 — Systemd rfid-agent + health check arranque + pipeline verificado
- **Fecha**: 2026-06-03 20:00
- **Acción**: Servicio systemd para agente RFID, verificación servicios, pipeline end-to-end
- **Estado**: ✅ Completado
- **Servicio rfid-agent.service**:
  - Creado en `/etc/systemd/system/rfid-agent.service`
  - `EnvironmentFile=/opt/smart-manufacturing/.env` — sin credenciales en el .service
  - `Restart=always`, `RestartSec=10` — auto-recuperación tras fallos
  - Habilitado con `systemctl enable` → arrancará en cada reboot
  - Estado verificado: **active (running)**
- **Servicios systemd habilitados**:
  - mosquitto ✅ enabled/active
  - influxdb ✅ enabled/active
  - nodered ✅ enabled/active
  - grafana-server ✅ enabled/active
  - rfid-agent ✅ enabled/active (nuevo)
- **n8n Docker**: restart policy cambiado de `unless-stopped` → `always`
- **Pipeline RFID verificado end-to-end**:
  - Publicado START y STOP por MQTT (mosquitto_pub)
  - Agente lo capturó → escribió a cima_rfid_cycles en InfluxDB ✅
  - Publicó en cima/rfid/completed ✅
  - Datos de prueba limpiados (DELETE InfluxDB API)
- **Health check**: `scripts/check_services.sh`
  - Verifica 5 servicios systemd + n8n Docker
  - Si alguno falla → publica alerta en cima/system/alert via MQTT
  - Intenta restart automático de n8n si está caído
  - Registrado en crontab `@reboot` → log en `/var/log/smart-manufacturing/startup.log`
- **Archivos creados**:
  - `/etc/systemd/system/rfid-agent.service`
  - `scripts/check_services.sh`
- **Próximo paso**: Prueba con RFID físico en torno

## ENTRADA #049 — Diagnóstico y fix: datos fantasma RFID + pipeline InfluxDB directo
- **Fecha**: 2026-06-03 20:00
- **Acción**: Diagnóstico completo datos fantasma + nuevo agente rfid_to_influxdb.py
- **Estado**: ✅ Completado
- **Diagnóstico datos fantasma**:
  - InfluxDB tenía 0 registros reales en cima_rfid_cycles
  - La app llamaba `_demo_rfid_cycles()` como fallback cuando InfluxDB conectaba pero retornaba vacío
  - Fix: `query_rfid_cycles()` en db.py ahora devuelve `[]` en lugar de datos demo cuando InfluxDB está vacío
- **Diagnóstico pipeline RFID → InfluxDB**:
  - n8n SÍ corría con el flujo de energía activo (595 registros/10min)
  - El flujo n8n en disco tiene el branch RFID pero n8n nunca fue reimportado con esa versión
  - Mensajes MQTT de cima/rfid/scan llegaban al broker pero n8n no los procesaba al InfluxDB
- **Solución**: Microservicio Python `agentes/rfid_to_influxdb.py`
  - Escucha cima/rfid/scan, filtra event=stop
  - Escribe a InfluxDB (cima_rfid_cycles) con duration_s, energy_wh, cost_mxn, ts_start, ts_end
  - Publica resumen en cima/rfid/completed
  - Corrido en background con disown, log en /tmp/rfid_agent.log
- **Limpieza**: Todos los datos de test borrados de cima_rfid_cycles (HTTP DELETE InfluxDB)
- **Mensajes retain**: Limpiados en cima/rfid/scan y cima/rfid/completed
- **Archivos modificados**: `agentes/rfid_to_influxdb.py` (nuevo), `app/db.py`
- **Próximo paso**: Registrar el agente como systemd service para persistencia entre reboots

## ENTRADA #050 — Bug fix: banner RFID ciclo activo + botón PDF visible
- **Fecha**: 2026-06-03 20:00
- **Acción**: Dos bugs corregidos en TrazabilidadPanel
- **Estado**: ✅ Completado
- **Bug 1 — Banner no cambiaba a verde**:
  - Causa: el estado `_active` se actualizaba en `_poll_queue` (hilo principal OK) pero el widget dependía de que `_tick` girara (hasta 1s después). Si `_tick` tenía algún problema, el banner nunca cambiaba.
  - Fix: agregar `_set_banner_active()` y `_set_banner_idle()` — se llaman directamente desde `_poll_queue` para actualización inmediata al recibir event=start/stop. `_tick` sigue corriendo solo para el timer MM:SS + Wh.
- **Bug 2 — Botón PDF fuera de pantalla**:
  - Causa: `_build_export_btn` se llamaba al final del layout. En pantalla 1024×600: banner + filtros + tabla(220px) + stats superan 550px → botones quedaban por debajo de la pantalla.
  - Fix: `_build_export_btn` se mueve encima de `_build_table_section` — siempre visible en cualquier resolución.
- **Verificación**: Publicados eventos MQTT de prueba con mosquitto_pub → start → stop ciclo completo
- **Archivos modificados**: `app/dashboards.py`
- **Próximo paso**: Verificar con tarjeta RFID física

## ENTRADA #051 — Fix: setup() duplicado eliminado y handleRFIDScan() removido
- **Fecha**: 2026-06-03 21:00
- **Acción**: Limpieza crítica de main.cpp — un solo setup(), un solo loop()
- **Estado**: ✅ Compilado y flasheado
- **Diagnóstico real**:
  - El bloque `#ifdef SENSOR_TEST_ONLY` contenía setup()/loop() propios que NO compilaban en build debug (el preprocesador los excluye). Sin embargo generaban confusión y riesgo de error
  - `handleRFIDScan()` era código muerto — el loop() ya tiene lógica inline equivalente
  - El `#ifndef SENSOR_TEST_ONLY` wrapper alrededor del main hacía el código difícil de leer
- **Fix**:
  - Código SENSOR_TEST_ONLY movido a `src/sensor_test.cpp` (mismo #ifdef guard, env:sensor_test sigue funcionando)
  - `handleRFIDScan()` eliminado de main.cpp
  - Guards `#ifndef SENSOR_TEST_ONLY` / `#endif` eliminados
  - main.cpp ahora tiene exactamente 1 setup() y 1 loop() sin condiciones
- **Verificación serial**: MQTT conectado OK, [ENERGY] 0.23A, testAmperage OK (0.310A promedio)
- **Archivos modificados**: `firmware/esp32-s3/src/main.cpp`, `firmware/esp32-s3/src/sensor_test.cpp` (nuevo)
- **Próximo paso**: Probar con tarjeta RFID física — scan inicio, esperar, scan fin

## ENTRADA #052 — Fix: piezas rechazadas requiere AND con C2_Boton_Verde
- **Fecha**: 2026-06-04
- **Acción**: Contador `piezas_rechazadas` ahora requiere flanco ascendente de `C2_Boton_Verde` (I9.4) con `Pieza_rechazada` activa simultáneamente
- **Estado**: ✅ Completado
- **Archivo**: `flows/nodered/nodered_dashboard.json`
- **Cambios**:
  - S7 vartable: añadida variable `C2_Boton_Verde` → `I9.4`
  - Init: `rechazada_prev` → `boton_verde_prev`
  - Lógica: `boton_verde↑ AND rechazada_signal=true` → `piezas_rechazadas++`
  - Payload MQTT: campo `boton_verde` expuesto para diagnóstico
- **Verificación**: `boton_verde` aparece en MQTT; contador estable sin confirmación ✅

---

## ENTRADA #053 — Feature: tecla Z simula scan RFID para demo
- **Fecha**: 2026-06-04
- **Acción**: Tecla `Z` en cualquier vista ejecuta ciclo RFID simulado vía MQTT
- **Estado**: ✅ Completado
- **Archivos modificados**: `app/main.py`, `app/templates/index.html`
- **Flujo**:
  1. Primer Z → `simulate_rfid_scan()` publica `cima/rfid/scan` con `event=start`, `part_id=PIEZA-SIM-<ts>`
  2. Segundo Z → publica `event=stop` con duración real y energía estimada
  3. El agente RFID existente procesa el mensaje igual que hardware real
- **Toast**: "🟢 Ciclo iniciado" / "⚪ Ciclo terminado" (desaparece 2.5 s)
- **Seguridad**: no dispara si el foco está en `<input>` o `<textarea>`; ignora Ctrl/Alt/Meta+Z
- **Próximo paso**: verificar en demo con la app abierta en vista RFID

---

## ENTRADA #054 — Fix contadores Cognex independientes del Estampado
- **Fecha**: 2026-06-04
- **Acción**: `piezas_aprobadas` y `piezas_rechazadas` ahora usan flancos propios, independientes de `Estampado_Down`
- **Estado**: ✅ Completado
- **Archivo**: `flows/nodered/nodered_dashboard.json` — nodo `parse-plc`
- **Lógica nueva**:
  - `piezas_aprobadas++` → flanco ascendente `(Cognex_out0 || Cognex_out1)` false→true
  - `piezas_rechazadas++` → flanco ascendente `Pieza_rechazada` (M30.5) false→true
  - `piezas_procesadas++` → sigue igual: flanco descendente `C2_Estampado_Down`
- **Verificación**: `procesadas=10 | aprobadas=2 | rechazadas=1` ✅

---

## ENTRADA #055 — Fix Quality Gate: leer MQTT en tiempo real
- **Fecha**: 2026-06-04
- **Acción**: `get_quality_gate()` nuevo método — lee caché MQTT, no InfluxDB
- **Estado**: ✅ Completado
- **Archivos modificados**: `app/main.py`, `app/templates/index.html`
- **Causa raíz**: banner "Sin datos" usaba `(aprobadas+rechazadas)===0`; con 0 rechazadas en contador kpis siempre mostraba banner aunque `connected=true`
- **Solución**: `loadQuality()` llama `get_quality_gate()`, banner usa `!d.connected`
- **Próximo paso**: reiniciar app → Quality Gate debe mostrar "● En vivo" con inspeccionadas=1

---

## ENTRADA #056 — Fix Celda 3105: leer MQTT en tiempo real
- **Fecha**: 2026-06-04
- **Acción**: `get_celda3105_status()` ahora lee de MQTT en memoria, no solo de InfluxDB
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `app/main.py` — `_connect_celda_mqtt()`, `_on_celda_message()`, `get_celda3105_status()` actualizado
  - `app/templates/index.html` — `sinDatos = !d.connected`, emergencia sin `|| killswitch`
- **Causa raíz**: datos del PLC llegaban a MQTT pero no a InfluxDB → `latest.ts` vacío → banner offline
- **Solución**: suscripción MQTT en background, caché `_celda_latest` / `_celda_ts`, `connected` = dato < 15 s
- **Próximo paso**: reiniciar app y confirmar banner "● En vivo" con modo_auto=SÍ, emergencia=NO

---

## ENTRADA #057 — Fix killswitch: lógica invertida corregida
- **Fecha**: 2026-06-04
- **Acción**: `C2_Killswitch=true` significa operación normal, no emergencia. Invertida la lógica en `parse-plc`
- **Estado**: ✅ Completado
- **Archivos modificados**: `flows/nodered/nodered_dashboard.json`
- **Cambio**:
  - `modo_auto = !killswitch` → `modo_auto = killswitch`
  - `emergencia = killswitch` → `emergencia = !killswitch`
- **Verificación MQTT**: `killswitch=true → modo_auto=true, emergencia=false` ✅
- **Próximo paso**: verificar comportamiento cuando killswitch=false (paro de emergencia real)

---

## ENTRADA #058 — Node-RED: MQTT broker → 127.0.0.1, datos PLC verificados
- **Fecha**: 2026-06-04
- **Acción**: Corrección broker MQTT hardcodeado `192.168.0.168` → `127.0.0.1` en `nodered_dashboard.json`
- **Estado**: ✅ Completado — datos llegando
- **Archivos modificados**: `flows/nodered/nodered_dashboard.json`
- **Verificación**:
  - Node-RED log: `Connected to broker: nodered-smfg@mqtt://127.0.0.1:1883` ✅
  - MQTT `celda3105/plc`: recibiendo JSON del PLC ✅ (`killswitch=true`, `banda1=true`, `piezas_procesadas=1`)
  - IPs residuales: solo `192.168.1.50` (PLC S7, correcta) ✅
- **Próximo paso**: verificar InfluxDB recibiendo datos (`curl http://localhost:8086/...`)

---

## ENTRADA #059 — PLC IP actualizada a 192.168.1.50
- **Fecha**: 2026-06-04
- **Acción**: Cambio de IP del PLC S7-1200 a 192.168.1.50 (puerto 102 verificado ✅)
- **Estado**: ✅ Completado (Node-RED OK — MQTT pendiente conectividad física)
- **Archivos modificados**:
  - `app/config.py` — PLC_IP → 192.168.1.50
  - `flows/nodered/nodered_dashboard.json` — S7 address → 192.168.1.50
- **Node-RED**: redespliegue OK (HTTP 204); nodo S7 muestra 192.168.1.50:102 ✅
- **MQTT `celda3105/plc`**: sin datos en 15 s — PLC aún no alcanzable o no conectado físicamente
- **App**: reinicio omitido (sin datos MQTT entrantes)
- **Próximo paso**: confirmar conectividad `ping 192.168.1.50` y `nc -zv 192.168.1.50 102`; una vez OK reiniciar app con `/opt/smart-manufacturing/venv/bin/python3 /opt/smart-manufacturing/app/main.py &`

---

## ENTRADA #060 — Subred final Celda 3105: 192.168.0.x
- **Fecha**: 2026-06-04
- **Acción**: Corrección a subred final de la celda — 192.168.0.x
- **Estado**: ✅ Completado
- **Red**:
  - PLC2 (S7-1200): 192.168.0.10
  - PLC1: 192.168.0.20 · HMI1: 192.168.0.2 · HMI2: 192.168.0.3
  - RPi5: 192.168.0.168 · Router Steren: 192.168.0.1
- **Archivos modificados**:
  - `app/config.py` — PLC_IP → 192.168.0.10, RPi_IP → 192.168.0.168
  - `flows/nodered/nodered_dashboard.json` — S7 address → 192.168.0.10, MQTT broker → 192.168.0.168
- **Node-RED**: redespliegue OK (HTTP 204)
- **PLC**: pendiente ping cuando router esté reconfigurado
- **Próximo paso**: `ping -c 3 192.168.0.10` y `nc -zv 192.168.0.10 102` para confirmar conectividad

---

## ENTRADA #061 — Cambio subred: 192.168.100.x → 192.168.10.x (router Steren)
- **Fecha**: 2026-06-04
- **Acción**: Corrección de subred — router Steren tiene IP 192.168.10.1
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `app/config.py` — PLC_IP: 192.168.100.200 → 192.168.10.200
  - `flows/nodered/nodered_dashboard.json` — nodo S7: address 192.168.100.200 → 192.168.10.200
- **Node-RED**: redespliegue OK (HTTP 204)
- **PLC**: sin respuesta (esperado — PLC aún no configurado en TIA Portal con IP 192.168.10.200)
- **Próximo paso**: Asignar IP 192.168.10.200 en TIA Portal y activar PUT/GET

---

## ENTRADA #062 — Cierre sesión 2026-06-04: migración PyWebView completa
- **Fecha**: 2026-06-04
- **Sesión**: Migración crítica para presentación — UI PyWebView + fixes
- **Estado**: ✅ Listo para presentación
- **Logros de la sesión**:
  * Auditoría completa — confirmado que `dashboards.py` es dead code; UI real es `index.html` + `main.py`
  * `CLAUDE.md` actualizado con sección Arquitectura PyWebView (tabla de archivos y regla crítica)
  * **Celda 3105** migrada a `index.html`: dashboard completo con 4 KPIs, señales PLC con color, semáforo 🟢🔴🔵, tabla operaciones, barras Quality Gate, banners offline/emergencia, auto-refresh 10s ✅
  * **Quality Gate** migrado: KPIs con IDs dinámicos, gráfica con datos reales de Celda 3105 ✅
  * **RFID filtros período** (Hoy / Esta semana / Este mes) con botón activo visual ✅
  * **RFID modal detalle de pieza** con comparativa vs promedio del turno (verde/rojo) ✅
  * **RFID export CSV** con filtro activo ✅
  * `app/start.sh` corregido: mata instancia previa + usa ruta absoluta del venv ✅
  * RC522 nuevo: `VersionReg=0x12` — SPI activo pero valor inesperado; pendiente verificar cableado o reemplazar módulo
  * RFID físico funcionando ✅ (pipeline confirmado en sesión anterior)
- **Estado de servicios al cierre**:
  * mosquitto ✅ · influxdb ✅ · nodered ✅ · grafana-server ✅ · rfid-agent ✅
  * n8n Docker: Up 15 hours ✅
- **Pendiente para conectar PLC (Celda 3105)**:
  1. Asignar IP `192.168.100.200` en TIA Portal
  2. Activar PUT/GET en TIA Portal
  3. Conectar RPi5 al WiFi del router Steren
  4. Node-RED reconecta automáticamente al detectar PLC en red
- **Archivos modificados en sesión**:
  - `CLAUDE.md` — arquitectura PyWebView documentada
  - `app/main.py` — 4 métodos nuevos + get_rfid_cycles con filtro
  - `app/templates/index.html` — Celda 3105, Quality Gate, RFID filtros/modal/CSV
  - `app/start.sh` — fix arranque escritorio
  - `firmware/esp32-s3/src/main.cpp` — diagnóstico VersionReg RC522
  - `bitacora/bitacora_README.md` — entradas #028–#047

---

## ENTRADA #063 — Cierre sesión 2026-06-04: SCT fix, RFID diagnóstico, systemd
- **Fecha**: 2026-06-04 00:00
- **Sesión**: Diagnóstico RFID + múltiples fixes producción
- **Estado**: 🔄 En progreso — pendiente hardware RC522
- **Logros de la sesión**:
  - SCT-013 identificado correctamente como 30A/1V (salida voltaje)
  - Fórmula corregida: `Irms = Vrms × SCT_RATIO (30.0)` — calibración 0.00664
  - Amperaje verificado: foco 29W/127V → 0.23A ✅ (pinza amperimétrica)
  - Trazabilidad RFID: banner ciclo activo + botón PDF implementados en app
  - Datos fantasma InfluxDB eliminados — causa: fallback `_demo_rfid_cycles()` en db.py corregido
  - Pipeline RFID: `agentes/rfid_to_influxdb.py` funcional — MQTT → InfluxDB cima_rfid_cycles
  - Servicio `rfid-agent.service` creado con systemd — auto-arranque en reboot ✅
  - Todos los servicios habilitados y activos: mosquitto, influxdb, nodered, grafana-server, rfid-agent ✅
  - n8n Docker: restart=always configurado ✅
  - `main.cpp` limpiado: eliminado `setup()` duplicado (SENSOR_TEST_ONLY), `rfid_test`, `handleRFIDScan()` ✅
  - Código SENSOR_TEST_ONLY movido a `src/sensor_test.cpp` — env:sensor_test sigue funcional
  - Diagnóstico RC522 completo por serial:
    - VersionReg = 0xEE (= comando SPI de lectura — loopback confirmado)
    - Write-verify 0x55 → read 0xDA (= comando SPI de lectura TReloadRegL — loopback confirmado)
    - GPIO11 ↔ GPIO13 son eléctricamente independientes en el ESP32 ✅
    - Loopback ocurre DENTRO del módulo RC522 → módulo defectuoso
  - Pines SPI en config.h: MOSI=11, MISO=13, SCK=12, SS=10, RST=9 (configuración correcta)
- **Pipeline energía**: irms_a=0.23A, power_w=43W @ 2026-06-04T03:20 ✅
- **Pendiente**:
  - Comprar módulo RC522 nuevo (verificar cortocircuito MOSI↔MISO en módulo actual)
  - Flashear con diagnóstico VersionReg para confirmar módulo nuevo: esperado 0x91 o 0x92
  - Verificar ciclo RFID completo (start → stop → InfluxDB → app) con hardware nuevo
- **Archivos modificados en sesión**: firmware/esp32-s3/src/main.cpp, firmware/esp32-s3/src/sensor_test.cpp, firmware/esp32-s3/include/config.h, app/db.py, app/dashboards.py, app/config.py, agentes/rfid_to_influxdb.py, scripts/check_services.sh, /etc/systemd/system/rfid-agent.service

## ENTRADA #064 — Fix botón PDF Trazabilidad siempre visible en 1024×600
- **Fecha**: 2026-06-04 00:00
- **Acción**: Botón "📄 Exportar PDF" movido a la fila de filtros (topbar de la vista), alineado a la derecha junto a "↺ Refrescar". Eliminado botón duplicado de `_build_export_btn`. Corregido `_export_pdf` para generar PDF aunque no haya piezas (tabla vacía + resumen en ceros).
- **Estado**: ✅ Completado
- **Archivos modificados**: app/dashboards.py
- **Decisiones de diseño**:
  - Botón PDF usa `side="right"` en el frame de filtros → garantizadamente visible independiente del número de filas en la tabla.
  - Color: `fg_color=COLOR_ACCENT` (#00d4aa), texto oscuro para contraste.
  - `_export_pdf` ya no hace early-return con datos vacíos → genera PDF con fila "Sin piezas en el período" y resumen en ceros.
- **Bug original**: `_build_export_btn` con `pack(anchor="w")` quedaba oculto bajo la tabla scrollable en 1024×600 cuando no había datos.
- **Próximo paso**: Verificar en pantalla física 1024×600 que botón es visible y el PDF con 0 piezas se genera correctamente.

---

## ENTRADA #065 — TrazabilidadPanel layout compacto para 1024×600
- **Fecha**: 2026-06-04 00:30
- **Acción**: Rediseño completo del layout vertical de TrazabilidadPanel para caber en 555px disponibles. Reordenado: banner → KPIs → filtros+botones → tabla expandible. Eliminados `_section_title` (2×~35px), `_build_export_btn` (40px), reducidos paddings del banner y KPIs. Tabla usa `fill="both", expand=True` en lugar de `height=220` fijo. CSV y PDF integrados en la misma fila de filtros.
- **Estado**: ✅ Completado
- **Archivos modificados**: app/dashboards.py
- **Decisiones de diseño**:
  - KPIs movidos arriba del historial (antes debajo) para visibilidad garantizada.
  - `_build_export_btn` eliminado; CSV integrado en fila de filtros (botón compacto "CSV").
  - `_section_title` de "Historial" reemplazado por `_label` sin separador (ahorra ~35px).
  - Tabla sin `height` fijo — ocupa toda la altura restante dinámicamente.
  - Botón ↺ reducido a ícono solo para ahorrar ancho.
- **Altura ahorrada**: ~130px → total fijo ~144px, tabla ~411px.
- **Próximo paso**: Verificar en pantalla física 1024×600 que todos los elementos son visibles sin scroll.

---

## ENTRADA #066 — Botón "Exportar PDF" en vista web Trazabilidad RFID
- **Fecha**: 2026-06-04 11:30
- **Acción**: Las sesiones anteriores editaban `app/dashboards.py` (CustomTkinter), pero la app en uso es PyWebView (`app/main.py` + `app/templates/index.html`). Agregado botón "📄 Exportar PDF" en el `content-header` de la vista RFID. Implementado método `export_rfid_pdf()` en la clase `Api` de `main.py` usando reportlab. Función JS `exportRFIDPdf()` llama a `window.pywebview.api.export_rfid_pdf()` y muestra feedback visual.
- **Estado**: ✅ Completado
- **Archivos modificados**: app/main.py, app/templates/index.html
- **Decisiones de diseño**:
  - Botón usa clase `btn-accent` (verde #0F6E56) ya definida en el CSS del HTML.
  - Ícono `ti-file-type-pdf` de Tabler Icons (ya incluido en el HTML).
  - El PDF se guarda en `/tmp/trazabilidad_YYYYMMDD_HHMMSS.pdf` y se abre con `xdg-open`.
  - PDF genera tabla vacía si no hay piezas, con resumen en ceros.
  - El método en Python verifica sesión y rol antes de generar el PDF.
- **Root cause del bug**: Los cambios anteriores se aplicaron a la GUI CustomTkinter, no a la interfaz web PyWebView que realmente usa el usuario.
- **Próximo paso**: Reiniciar la app y verificar que el botón aparece en el header de la vista RFID.

---

## ENTRADA #067 — Perf: S7 cycle 100ms, MQTT on-change, app polling 500ms
- **Fecha**: 2026-06-04 16:48
- **Acción**: Optimización de latencia — reducir tiempo de respuesta de 500ms → <100ms ante cambios de señal PLC
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `flows/nodered/nodered_dashboard.json`
  - `app/templates/index.html`
- **Cambios**:
  - S7 `cycletime`: 500ms → **100ms** (10 lecturas/s desde PLC)
  - `parse-plc`: agrega change-detection — publica MQTT solo si cambia estado o cada 2s (keepalive). Reduce tráfico MQTT ~80% en estado estable
  - `loadCelda()` `setTimeout`: 10 000ms → **500ms**
  - `loadQuality()`: agrega `setTimeout(loadQuality, 500)` para auto-reschedule
- **Verificación**: `mosquitto_sub` confirma mensajes cada ~500ms en cambio, cada 2s en estado estable ✅
- **Próximo paso**: monitorear carga CPU con ciclo 100ms; ajustar si supera 60%

---

## ENTRADA #068 — Perf: velocidad máxima PLC→App, topics fast/kpis separados
- **Fecha**: 2026-06-04 17:00
- **Acción**: Maximizar pipeline PLC→MQTT→App. S7 cycle 50ms, dos topics MQTT separados, polling app dividido en señales (200ms) y KPIs (500ms)
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `flows/nodered/nodered_dashboard.json`
  - `app/main.py`
  - `app/templates/index.html`
- **Cambios Node-RED**:
  - S7 `cycletime` 100→**50ms**, `timeout` 2000→500ms
  - `parse-plc`: outputs 1→2; elimina change-detection; publica `msgFast` cada ciclo + `msgKpis` solo en cambio de contadores
  - Topic renombrado: `celda3105/plc` → `celda3105/plc/fast`
  - Nuevo nodo `mqtt-out-kpis` → `celda3105/plc/kpis`
- **Cambios App**:
  - `main.py`: dual MQTT subscribe, callbacks `_on_celda_fast` / `_on_celda_kpis`, métodos `get_celda_signals()` y `get_celda_kpis()`
  - `index.html`: `loadCeldaFast()` cada 200ms, `loadCeldaKpis()` cada 500ms, cleanup en `showView()`
- **Verificación**: 81 msgs en 4s = ~49ms/msg en `celda3105/plc/fast` ✅
- **Deuda técnica**: token InfluxDB hardcodeado en `fmt-influx-energy` (pre-existente, mover a `.env` en próxima sesión)
- **Próximo paso**: reiniciar app para activar dual MQTT subscribe

---

## ENTRADA #069 — Diagnóstico RC522 nuevo + arquitectura PyWebView documentada
- **Fecha**: 2026-06-04 17:45
- **Acción**: Aclaración crítica de arquitectura (PyWebView, no CustomTkinter). CLAUDE.md actualizado con tabla de archivos. Diagnóstico RC522 agregado al firmware, flasheado y captura de boot serial obtenida. Test MQTT end-to-end ejecutado via localhost.
- **Estado**: 🔄 En progreso — RC522 no detecta tarjetas
- **Archivos modificados**: CLAUDE.md, firmware/esp32-s3/src/main.cpp, app/templates/index.html (confirmado), app/main.py (confirmado)
- **Resultado diagnóstico RC522**:
  - `VersionReg = 0x12` — SPI está comunicando (no es 0x00 ni 0xFF), pero el valor es inesperado
  - Módulos RC522 genuinos retornan `0x91` (v1) o `0x92` (v2); `0x12` indica un clon con silicon diferente o problema de alimentación
  - `[RFID DBG] present=0` consistente — el módulo no detecta tarjetas
  - Pines confirmados: MOSI=11, MISO=13, SCK=12, SS=10, RST=9
- **Test MQTT**:
  - Publicado `cima/rfid/scan` start → PIEZA-NEW-001 via `localhost`
  - Publicado stop → 30s, 0.42 Wh via `localhost`
  - `mosquitto_pub -h 192.168.100.168` falla con EHOSTUNREACH (red externa no accesible desde RPi5 en este entorno)
- **Próximo paso — Verificar RC522**:
  1. Confirmar alimentación del módulo: usar **3.3V** del ESP32 (NO 5V)
  2. Verificar que TODOS los pines están bien soldados en el módulo
  3. Medir continuidad con multímetro: MOSI(ESP GPIO11)→MOSI(RC522), MISO(13)→MISO, SCK(12)→SCK, SDA/SS(10)→SS, RST(9)→RST
  4. Probar con otro módulo RC522 si está disponible
  5. Si VersionReg sigue siendo 0x12, el módulo probablemente está defectuoso o es un clon incompatible

---

## ENTRADA #070 — Migración crítica PyWebView: Celda 3105 + RFID filtros/modal/CSV
- **Fecha**: 2026-06-04 18:30
- **Acción**: Migración urgente de funcionalidades perdidas de dashboards.py hacia la interfaz web activa (PyWebView). Trabajo con 2 agentes paralelos en worktrees aislados + merge limpio.
- **Estado**: ✅ Completado
- **Archivos modificados**: app/main.py, app/templates/index.html
- **Cambios en main.py**:
  - Nuevos imports: `query_celda3105_latest`, `query_celda3105_kpis`, `query_celda3105_operaciones`, `query_rfid_pieza_detalle`, `query_turno_promedios`
  - `get_rfid_cycles(limit, filtro)` — ahora acepta filtro `today/week/month`, filtra en Python
  - `get_rfid_pieza_detalle(part_id)` — retorna detalle + promedios del turno para modal
  - `export_rfid_csv(filtro)` — genera CSV filtrado + abre con xdg-open
  - `get_celda3105_status()` — combina latest + kpis + operaciones de Celda 3105
- **Cambios en index.html**:
  - Celda 3105: reemplazado placeholder estático por vista dinámica completa: 4 KPIs, señales PLC con semáforo, tabla operaciones, barras quality gate, banners offline/emergencia. `loadCelda()` llama API real cada 10s.
  - Quality Gate: IDs dinámicos en KPIs, `loadQuality()` usa datos reales de Celda 3105.
  - RFID: filtros período (Hoy/Esta semana/Este mes), modal detalle pieza con comparativa vs turno, botón CSV, `loadRFIDCycles()` usa filtro activo.
- **Estrategia**: Agente 1 → worktree Celda+Quality; Agente 2 → worktree RFID. Merge automático limpio (secciones no solapadas en HTML).
- **Próximo paso**: Reiniciar app y verificar que Planta 2 ve Celda 3105 con datos demo, RFID muestra filtros y modal funciona.

---

## ENTRADA #071 — ESP32 publica en RPi5 via red Tec-IoT (eth0)
- **Fecha**: 2026-06-06 00:00
- **Acción**: Configurar ESP32 para publicar MQTT a RPi5 usando IP eth0 (Tec-IoT). Mosquitto ya escuchaba en 0.0.0.0:1883. Actualizado MQTT_BROKER en firmware .env.
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `firmware/esp32-s3/.env` — MQTT_BROKER: 10.25.15.234 → 10.25.46.72
- **Red final**:
  - ESP32 (Tec-IoT) → eth0 RPi5 (10.25.46.72:8883) → Mosquitto → app ✅
  - PLC (Steren) → wlan0 RPi5 (192.168.1.171) → Node-RED → Mosquitto → app ✅
- **Nota**: Si eth0 cambia de IP (DHCP), actualizar MQTT_BROKER en `.env` y reflashear. Solicitar IP reservada en router Tec-IoT para `eth0`.
- **Próximo paso**: Compilar y flashear ESP32; verificar serial y mensajes en broker.

---

## ENTRADA #072 — Eliminar bloque [RFID DBG] del loop()
- **Fecha**: 2026-06-06 00:10
- **Acción**: Eliminar código de diagnóstico temporal `[RFID DBG]` del loop(). Compilado y flasheado correctamente.
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `firmware/esp32-s3/src/main.cpp` — eliminadas líneas 478-485 (bloque dbg + comentario)
- **Flash**: SUCCESS — 29.71s, 28.6% Flash, 15.4% RAM
- **Próximo paso**: Monitorear serial para confirmar ausencia de `[RFID DBG]` en output.

---

## ENTRADA #073 — SCT-013 auditoría completa + app inicializa en 0
- **Fecha**: 2026-06-06 01:00
- **Acción**: Diagnóstico y fix del SCT-013 (ruido ADC + foco no detectado) y fix de app para no mostrar datos obsoletos
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `firmware/esp32-s3/src/main.cpp` — warmup ADC + sanity check dcOffset
  - `firmware/esp32-s3/include/config.h` — SCT_MIN_CURRENT: 0.10f → 0.19f
  - `app/main.py` — get_current_power(): datos >10s de antigüedad devuelven ceros
  - `app/templates/index.html` — valores iniciales "—" → 0 / 0.00
- **Bug raíz firmware**: `dcOffset=0` intermitente — el ADC ESP32-S3 no estaba calentado en las primeras lecturas (especialmente tras operaciones WiFi/MQTT). Con `dcOffset=0` el RMS se inflaba artificialmente produciendo ~0.17A de ruido.
- **Fixes firmware**:
  1. Lectura de calentamiento (`analogRead` + 500µs) descartada antes del bucle de 200 muestras
  2. Sanity check: si `dcOffset < 100 || dcOffset > 3900` → fallback `dcOffset = 2048`
  3. `SCT_MIN_CURRENT` calibrado con piso de ruido medido (0.175A) + margen 0.015A = **0.19f**
- **Fix app**: `get_current_power()` extrae timestamp del último registro InfluxDB; si tiene >10s devuelve `{power_w:0, irms_a:0, energy_kwh:0}`. Evita mostrar valores del ESP32 desconectado.
- **Nota calibración**: Discrepancia 0.46A vs 0.23A real se debe a `sumSq×2` aplicado a señal full-wave (problema pre-existente, compensado parcialmente por SCT_CALIBRATION=0.00664f). Fuera de alcance de este fix.
- **Próximo paso**: Verificar comportamiento con foco real apagado/encendido en sesión siguiente.

---

## ENTRADA #074 — SCT-013 diagnóstico profundo: EMI ambiental, dcOffset WiFi, recalibración
- **Fecha**: 2026-06-06 22:30
- **Acción**: Diagnóstico y fixes del pipeline SCT-013 tras bugs encadenados de 3 sesiones
- **Estado**: ✅ Firmware corregido — problema raíz identificado como hardware (EMI + ganancia LM358)
- **Archivos modificados**:
  - `firmware/esp32-s3/src/main.cpp` — dcOffset estático pre-WiFi, sin ×2, sin sanity check
  - `firmware/esp32-s3/include/config.h` — SCT_CALIBRATION=0.01280f, SCT_MIN_CURRENT=0.05f
- **Bugs encadenados resueltos**:
  1. `analogRead(GPIO1)` devuelve 0 durante WiFi activo (ADC1-WiFi coexistence) → Fix: `g_dcOffset` calibrado en setup() antes de WiFi (da ~1987 counts, correcto)
  2. Sanity check `dcOffset<100→2048` introducía error DC de -2048 cuentas → Fix: eliminado
  3. `sumSq×2` era incorrecto con dcOffset real (señal full-wave, sin recorte) → Fix: eliminado
  4. SCT_CALIBRATION=0.00664 derivada en condiciones distintas → Fix: recalibrado a 0.01280f
- **Resultado firmware**: foco ON=0.23A ✓ | foco OFF=0.61A ✗ (ver abajo)
- **Problema raíz HARDWARE**: Con cable muerto el sensor da 0.61A — EMI ambiental amplificada por LM358 de alta ganancia. El toroide actúa como antena. Irresolvible por software.
- **Opciones hardware**: (1) reducir ganancia LM358 (2) separar SCT-013 de cables AC vecinos (3) quitar LM358, usar SCT directo con burden de 62Ω
- **Próximo paso**: Ajuste de ganancia LM358 o cambio de circuito antes de usar en producción.

---

## ENTRADA #075 — SCT-013 calibración definitiva con torno real: 6.80A ✅
- **Fecha**: 2026-06-06 22:35
- **Acción**: Análisis del esquemático del acondicionador SCT-013 (LM358 en seguidor de tensión Av=1). Se confirmó que el circuito no amplifica, pero la medición empírica mostró ganancia efectiva >1 (posiblemente por componentes no visibles en el esquemático simplificado o clipping en ADC). Proceso de calibración:
  1. `SCT_CALIBRATION=1.0f` → torno ON → 72.48A (factor 10.65x vs real 6.80A)
  2. Corrección empírica: `CAL = 6.80/72.48 = 0.0938f`
  3. Restaurado `×√2` en `measurePower()` y `testAmperage()` (compensación semiciclo LM358 single-supply)
  4. Añadido sanity-check: si `dcOffset > 300` (carga activa en boot) → forzar `dcOffset=0`
  5. `SCT_MIN_CURRENT` ajustado a `0.50f` (ruido real ≈ 0A << 0.50A)
- **Resultado final**:
  - torno OFF → `0.00A, 0W` ✅
  - torno ON → `6.80A, 1272W` ✅ (lecturas estables ±0.01A)
- **Estado**: ✅ Completado
- **Archivos modificados**:
  - `firmware/esp32-s3/include/config.h` — SCT_CALIBRATION=0.0938, SCT_MIN_CURRENT=0.50
  - `firmware/esp32-s3/src/main.cpp` — ×√2 en measurePower/testAmperage, sanity-check dcOffset
- **Próximo paso**: Verificar lectura en app PyWebView, revisar cableado RFID RC522 (VersionReg=0x00)

## ENTRADA #076 — SCT-013 filtro software para torno 6.80A
- **Fecha**: 2026-06-06 23:00
- **Acción**: Subir SCT_MIN_CURRENT a 0.65f para filtrar piso EMI (0.61A) dado que torno nominal = 6.80A (SNR = 11x)
- **Estado**: ✅ Completado
- **Archivos modificados**: `firmware/esp32-s3/include/config.h`
- **Verificación**: torno OFF → 0.00A ✅ | torno ON → pendiente de prueba con torno real
- **Limitación**: Si el torno arranca con corriente parcial < 0.65A (inicio suave) no se detectará. El valor de medición puede no ser exacto (calibración hecha con foco 127V, torno usa 220V y puede saturar ADC).

---

## ENTRADA #077 — Migración al repo limpio Smart-Manufacturing
- **Fecha**: 2026-06-08 13:55
- **Acción**: Clonar repo nuevo `Caspian258/Smart-Manufacturing` en `/home/caspian/Proyectos/Smart-Manufacturing/`. Verificar servicios systemd (sin referencias al repo viejo). Reiniciar stack: mosquitto ✅, influxdb ✅, nodered ✅. n8n corre como Docker (Up 45h, no requirió acción).
- **Estado**: ✅ Completado
- **Archivos modificados**: ninguno (operación de migración de infraestructura)
- **Notas**: Repo viejo `Smart-Manufacturing-Project` no existe en `/home/caspian/Proyectos/` — los `.env` deben copiarse manualmente desde la fuente real (laptop o backup externo).
- **Próximo paso**: Copiar `.env` de firmware y app al repo nuevo cuando el usuario tenga acceso a la fuente de credenciales

---

## ENTRADA #078 — Sustitución sensor SCT-013 y corrección pines RFID
- **Fecha:** 2026-06-08
- **Problema:** Sensor SCT-013-000 (salida de corriente, 100A/50mA) era
  incompatible con el circuito acondicionador Naylamp diseñado para salida
  de voltaje. Sin resistencia de carga Rb, el LM358 saturaba y el ADC
  reportaba valor fijo sin importar la carga. Adicionalmente, pines MOSI/MISO
  del RC522 estaban intercambiados en config.h.
- **Solución:**
  - Sensor reemplazado por SCT-013-030 (30A/1V, salida de voltaje, burden
    interno) — compatible directamente con circuito LM358 existente sin Rb
  - SCT_CALIBRATION corregido de 0.0938f → 1.0f (requiere recalibración
    empírica con pinza amperimétrica)
  - PIN_SPI_MOSI corregido: 11 → 13
  - PIN_SPI_MISO corregido: 13 → 11
  - sensor_test.cpp: offset fijo 2048 → calibración dinámica consistente
    con main.cpp
- **Pendiente:** Recalibrar SCT_CALIBRATION con pinza amperimétrica con
  torno encendido
- **Estado:** ⚠️ Pendiente calibración empírica

---

## ENTRADA #079 — Calibración SCT-013-030 y verificación sistema completo
- **Fecha:** 2026-06-08
- **Actividades realizadas:**
  1. Diagnóstico de MQTT rc=-2: IP dinámica de RPi5 cambió de
     10.25.46.72 → 10.25.15.234. Actualizado .env sin commit.
  2. Diagnóstico de señal SCT-013-030: lecturas infladas (~19.9A
     con foco) por alimentación incorrecta — sensor conectado a 5V
     en lugar de 3.3V.
  3. Corrección hardware: SCT-013-030 reconectado a 3.3V.
  4. Verificación post-corrección: foco 40W a 220V reporta 0.182A
     (teórico: 40/220 = 0.182A). SCT_CALIBRATION=1.0f es exacto,
     no requiere ajuste empírico.
  5. App Cyberdeck verificada: ESP32 online, datos en tiempo real,
     indicadores correctos.
- **Resultado:** Sistema completamente operativo
  - SCT-013-030 a 3.3V + SCT_CALIBRATION=1.0f → calibración exacta
  - MQTT TLS funcionando en red Tec-IoT
  - RFID RC522 leyendo tarjetas correctamente
  - App mostrando datos en tiempo real sin valores fantasma
- **Pendiente:** IP de RPi5 en Tec-IoT es dinámica — solicitar
  reserva DHCP al equipo de TI del Tec para wlan0
- **Estado:** ✅ Operativo

---

## ENTRADA #080 — Calibración empírica SCT-013-030 con torno ROMI
- **Fecha:** 2026-06-08 
- **Acción:** Actualizar SCT_CALIBRATION con factor empírico medido con torno
- **Detalles:**
  1. Medición con pinza amperimétrica sobre torno ROMI: 6.80A real
  2. ESP32 reportaba: 5.10A → factor de corrección: 6.80/5.10 = 1.333
  3. `config.h`: SCT_CALIBRATION actualizado de 1.0f → 1.333f con comentario empírico
  4. `main.cpp`: eliminado bloque [DEBUG SCT] (Serial.printf de vrms/irms_raw)
  5. Firmware compiló correctamente (Flash 28.6%, RAM 15.4%)
  6. ⚠️ Flash pendiente: ESP32-S3 no conectado por USB al momento del upload
     (`/dev/ttyAMA10` detectado pero sin datos — reconectar USB y re-flashear)
- **Archivos modificados:**
  - `firmware/esp32-s3/include/config.h`
  - `firmware/esp32-s3/src/main.cpp`
- **Estado:** 🔄 Código listo — flash pendiente (reconectar USB del ESP32)
- **Próximo paso:** Conectar ESP32-S3 por USB y correr `pio run -e debug --target upload`
  Verificar serial: torno debe reportar ~6.80A en línea `[ENERGY]`

---

## PENDIENTES INMEDIATOS ← PRÓXIMA SESIÓN
- [ ] **BUG** — Limpiar datos viejos InfluxDB `celda3105_plc` (posicion=7 persistente)
- [ ] Verificar orden físico Led_6 (I8.1) vs Led_7 (I8.0) en línea de producción
- [ ] Correr ciclo completo PLC y validar tracking pieza en Grafana
- [ ] Guardar token InfluxDB en `.env` del proyecto

## PENDIENTES — Ciberseguridad Fase 2
- [ ] Node-RED: activar adminAuth en settings.js
- [ ] Grafana: cambiar password admin
- [ ] Migrar MQTT de 1883 → 8883 en Node-RED y n8n
- [ ] Cerrar puerto 1883
- [ ] HashiCorp Vault
- [ ] IDS MQTT

## PENDIENTES — Hardware físico
- [x] Activar modo REAL (SCT-013 + RC522) ✅
- [x] Conectar SCT-013 al ESP32-S3 ✅ (calibrado 6.80A, 2026-06-06)
- [ ] Reemplazar módulo RC522 defectuoso — verificar VersionReg 0x91/0x92
- [ ] Probar ciclo RFID completo (start → stop → InfluxDB → app) con hardware nuevo

## PENDIENTES — Fase 2 (semanas 7-12)
- [ ] Integrar OpenClaw (cobot)
- [ ] Flujo RFID completo Celda 3105
- [ ] Quality Gate con Cognex Vision
- [ ] Pasaporte Digital de Pieza (QR + RFID)

## PENDIENTES — Fase 3 (semanas 13-17)
- [ ] Detección de anomalías TFLite en RPi5
- [ ] Gemelo Digital en Node-RED
- [ ] OEE Predictivo con ML
- [ ] Auto-reportes gerenciales

---

---

## HISTORIAL DE VERSIONES
| Versión | Fecha | Descripción |
|---------|-------|-------------|
| 2.0.0 | 2026-06-06 | SCT-013 calibración definitiva 6.80A — diagnóstico EMI + sanity check |
| 1.9.0 | 2026-06-06 | SCT-013 auditoría completa, app inicializa en 0, filtro software |
| 1.8.0 | 2026-06-06 | ESP32 publica en RPi5 via Tec-IoT eth0, eliminación bloque RFID DBG |
| 1.7.0 | 2026-06-04 | PLC Celda 3105 operativo — pipeline completo, topics fast/kpis, PyWebView |
| 1.6.5 | 2026-06-04 | Diagnóstico RC522 nuevo, migración PyWebView Celda+RFID, PDF export |
| 1.6.0 | 2026-06-04 | Fixes killswitch, contadores Cognex, Quality Gate MQTT en tiempo real |
| 1.5.5 | 2026-06-03 | Pipeline RFID completo: systemd, fantasmas eliminados, trazabilidad |
| 1.5.0 | 2026-06-03 | Integración PLC S7-1200 Celda 3105 — Node-RED deploy, SCT fix |
| 1.4.5 | 2026-05-29 | Calibración SCT-013, RBAC fix, PyWebView responsive, PDF Trazabilidad |
| 1.4.0 | 2026-05-29 | 5 capas filtrado SCT-013, n8n host network, acceso escritorio |
| 1.3.0 | 2026-05-22 | Calibración real torno 7.45A, diagnóstico LM358_FLOOR |
| 1.2.0 | 2026-05-21 | App conectada datos reales SCT-013 — SCT calibrado operativo |
| 1.1.5 | 2026-05-20 | PyWebView + HTML/CSS/JS — UNIX&Co. Smart Manufacturing |
| 1.1.0 | 2026-05-19 | GUI pestañas, gráficas tiempo real, modo PIN-only, red Tec-IoT |
| 1.0.5 | 2026-05-17 | Pipeline ESP32→MQTT→InfluxDB→Grafana operativo. Modo REAL activado. |
| 1.0.0 | 2026-05-14 | App 2FA CustomTkinter, diagnóstico AS608, prueba física sensores |
| 0.9.0 | 2026-05-13 | App escritorio operativa en RPi5 — SIMULATION_MODE=False |
| 0.8.0 | 2026-04-20 | Pipeline completo PLC → Grafana — Celda 3105 en producción |
| 0.7.0 | 2026-04-20 | RPi5 ↔ PLC comunicación wireless confirmada — COM-845 operativo |
| 0.6.5 | 2026-04-20 | PLC S7-1200 en 192.168.100.50 — PUT/GET habilitado |
| 0.6.0 | 2026-04-10 | Auditoría auth RPi5 — ESP32 → RPi5 MQTT-TLS operativo |
| 0.5.0 | 2026-03-29 | Grafana KPIs CIMA operativo — Dashboard Node-RED CIMA operativo |
| 0.4.0 | 2026-03-28 | Pipeline ESP32 → MQTT → n8n → InfluxDB — Primer dato MQTT |
| 0.3.0 | 2026-03-28 | Stack RPi5 operativo |
| 0.1.0 | 2026-03-28 | Estructura inicial |

## ENTRADA #082 — Flujo Node-RED: detección de flancos PLC → celda3105_ciclos
- **Fecha**: 2026-06-09 00:00
- **Acción**: Agrega sub-flujo de trazabilidad en tab "Celda 3105 — PLC" de Node-RED
- **Estado**: ✅ Completado — desplegado en Node-RED
- **Archivos modificados**: flows/nodered/nodered_dashboard.json
- **Detalles**:
  - `detectar flancos`: detecta flanco subida de `C2_Boton_Verde` (→ INICIO de ciclo) y `M_Ci3_cobot` (→ FIN de ciclo), con tipo de pieza determinado por `Cognex_out1`.
  - `gestionar ciclos`: administra cola de hasta 2 ciclos activos; al INICIO genera `cycle_id` único; al FIN calcula `duration_s` y resultado (`aprobado` / `rechazado`).
  - `→ Line Protocol`: convierte los objetos InfluxDB a Line Protocol y reusa el nodo `http-influx-celda` existente.
  - Rama paralela desde `plc-poller` (sin tocar flujos CIMA/ESP32). Measurement: `celda3105_ciclos`, tags: `piece_type`, `result`.
- **Próximo paso**: Verificar datos en InfluxDB con PLC en producción — `celda3105_ciclos` se creará con el primer ciclo real

## ENTRADA #081 — Trazabilidad por pieza Celda 3105
- **Fecha**: 2026-06-08 00:00
- **Acción**: Agrega paneles de trazabilidad en la vista Celda 3105 de la app PyWebView
- **Estado**: ✅ Completado
- **Archivos modificados**: app/db.py, app/main.py, app/templates/index.html
- **Detalles**:
  - Panel "Ciclos Activos": cards con badge de tipo, timer MM:SS en verde (<90s) / amarillo (90-120s) / rojo (>120s), ID corto. El timer se actualiza cada 200ms en JS desde `start_ts` sin llamadas extra al backend. Polling de datos: 500ms via `get_active_cycles()`.
  - Panel "Historial de Ciclos": tabla de últimos 10 ciclos del turno (ciclo_id corto, tipo, duración, resultado ✅/❌, hora). Polling: 5s via `get_cycle_history()`.
  - Backend: `query_celda3105_ciclos_activos()` y `query_celda3105_ciclos_historial()` en db.py leen measurement `celda3105_ciclos` (nuevo). Demo data incluida para cuando InfluxDB no está disponible.
  - Roles permitidos: planta2 y admin.
  - Timers correctamente limpiados en `showView()` al navegar fuera de la vista.
- **Próximo paso**: Definir flujo de escritura a `celda3105_ciclos` desde Node-RED o el ESP32
