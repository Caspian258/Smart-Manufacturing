# 🏭 Smart Manufacturing — CIMA + Celda 3105

Sistema integrado de monitoreo IoT y automatización distribuida para manufactura avanzada, desarrollado en el **Tecnológico de Monterrey** en colaboración con **Rockwell Automation**, **Siemens** y **Cognex**.

El proyecto unifica dos plantas físicamente separadas bajo una arquitectura de **Industria 4.0** completamente on-premises, eliminando dependencias de servicios en la nube.

---

## ¿Qué es este proyecto?

Se integran dos plantas de manufactura distribuida:

| Planta | Tipo | Descripción |
|--------|------|-------------|
| **Planta 1 — CIMA** | Brownfield | Torno ROMI con instrumentación IoT no invasiva (SCT-013 + ESP32-S3). Monitoreo de corriente, potencia y energía en tiempo real con trazabilidad RFID por pieza. |
| **Planta 2 — Celda 3105** | Greenfield | Inspección por visión artificial (Cognex In-Sight 2800), control de PLC Siemens S7-1200 programado en TIA Portal, paletizado con Cobot UF Lite 6 y HMI de operación. |

Como módulo de innovación se diseñó y construyó un **Cyberdeck industrial**: una terminal portátil de fabricación propia basada en Raspberry Pi 5 con interfaz RBAC (Control de Acceso Basado en Roles), que opera simultáneamente como servidor edge y punto de acceso unificado a toda la infraestructura.

---

## Arquitectura del sistema

```
ESP32-S3 (SCT-013 + RFID RC522)
        | MQTT
        v
Raspberry Pi 5 — Servidor Edge On-Premises
        |-- Mosquitto (broker MQTT :1883)
        |-- n8n (flujos MQTT -> InfluxDB :5678)
        |-- InfluxDB 2.7 (base de datos :8086)
        |-- Node-RED (dashboard SCADA :1880)
        +-- Grafana (análisis histórico :3001)
        |
        | S7 / ISO-on-TCP
        v
PLC Siemens S7-1200 (Celda 3105)
        |-- Cognex In-Sight 2800 (Quality Gate)
        |-- Cobot UF Lite 6
        +-- HMI local
```

---

## Hardware requerido

### Planta 1 — CIMA
- ESP32-S3-DevKitC-1
- Sensor de corriente SCT-013-000 (100A/50mA, salida de corriente)
- Circuito acondicionador LM358
- Lector RFID RC522

### Planta 2 — Celda 3105
- PLC Siemens S7-1200 (programado en TIA Portal)
- Cámara Cognex In-Sight 2800
- Cobot UF Lite 6
- HMI local

### Servidor Edge
- Raspberry Pi 5 (ARM64, Raspberry Pi OS 64-bit)

---

## Stack de software

| Capa | Tecnología | Puerto |
|------|-----------|--------|
| Firmware IoT | ESP32-S3 + PlatformIO (C++) | — |
| Broker MQTT | Mosquitto | 1883 |
| Motor de flujos | n8n | 5678 |
| Base de datos | InfluxDB 2.7 | 8086 |
| Dashboard SCADA | Node-RED | 1880 |
| Análisis histórico | Grafana | 3001 |
| Interfaz Cyberdeck | Python + PyWebView (RBAC) | — |
| Programación PLC | TIA Portal (Siemens) | — |
| Visión artificial | Cognex In-Sight Vision Suite | — |

---

## Estructura del repositorio

- `app/` — Cyberdeck: interfaz PyWebView con RBAC
  - `main.py` — Backend API (clase Api, PyWebView)
  - `templates/index.html` — Frontend (toda la UI visible)
  - `auth.py` — Autenticación PIN + bcrypt
  - `db.py` — Capa de datos (InfluxDB + SQLite)
  - `config.py` — Configuración central
  - `health_check.py` — Monitor de servicios del stack
- `firmware/esp32-s3/` — Proyecto PlatformIO
  - `src/main.cpp` — Gateway IoT (SCT-013 + RFID)
  - `include/config.h` — Pines y parámetros de calibración
  - `scripts/inject_env.py` — Inyección de credenciales desde .env
- `flows/`
  - `n8n/` — Flujo MQTT → InfluxDB + alertas
  - `nodered/` — Dashboard SCADA + lectura PLC S7-1200
- `dashboard/grafana/` — Dashboards y datasource de Grafana
- `scripts/setup_rpi5.sh` — Instalación completa del servidor edge
- `bitacora/` — Log de desarrollo del proyecto
- `docs/` — Documentación técnica adicional

> **Nota:** Los programas de TIA Portal (PLC), Cognex In-Sight y Cobot UF Lite 6 se agregarán próximamente.

---

## Instalación

### 1. Configurar el servidor edge (Raspberry Pi 5)

```bash
git clone https://github.com/Caspian258/Smart-Manufacturing.git /opt/smart-manufacturing
cd /opt/smart-manufacturing
sudo bash scripts/setup_rpi5.sh
```

El script instala y configura automáticamente: Mosquitto, InfluxDB, Node-RED, n8n y Grafana.

### 2. Configurar el firmware del ESP32-S3

```bash
cd firmware/esp32-s3
cp .env.template .env
# Editar .env con las credenciales WiFi e IP del RPi5
pio run --target upload
```

### 3. Importar flujos

- **n8n:** importar `flows/n8n/mqtt_to_influxdb_v2.json` en `http://IP_RPI5:5678`
- **Node-RED:** importar `flows/nodered/nodered_dashboard.json` en `http://IP_RPI5:1880`

### 4. Iniciar el Cyberdeck

```bash
cd /opt/smart-manufacturing
source venv/bin/activate
python3 app/main.py
```

---

## KPIs monitoreados

| KPI | Descripción | Fuente |
|-----|-------------|--------|
| Potencia activa (W) | Consumo instantáneo del torno | SCT-013 → ESP32 |
| Corriente eficaz (A) | Irms medida no invasivamente | SCT-013 → ESP32 |
| Energía acumulada (kWh) | Consumo por ciclo productivo | InfluxDB |
| Costo energético (MXN) | Costo en tarifa CFE | Cyberdeck (solo admin) |
| Trazabilidad RFID | Pasaporte digital por pieza | RC522 → MQTT |
| Piezas aprobadas/rechazadas | Quality Gate Cognex | PLC → Node-RED |
| OEE | Eficiencia global de la celda | Node-RED |

---

## Roles del Cyberdeck (RBAC)

| Rol | Acceso |
|-----|--------|
| **Operador** | Monitoreo en tiempo real: potencia, corriente, ciclos productivos, estado de Celda 3105 |
| **Administrador** | Todo lo anterior + costo energético en MXN, historial, gestión de usuarios y auditoría |

---

## Proyecto académico

**Institución:** Tecnológico de Monterrey, Querétaro  
**Colaboradores:** Rockwell Automation · Siemens · Cognex  
**Equipo:** UNIX & Co.
