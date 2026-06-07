# 🏭 Smart Manufacturing — CIMA + Celda 3105

> Arquitectura de Industria 4.0 para manufactura distribuida en dos plantas.
> **Orquestador**: Claude Code | **Partners**: Rockwell Automation · Siemens · Cognex

---

## ¿Qué es este proyecto?

Simula la operación real de una compañía de manufactura distribuida que enfrenta el desafío de gestionar producción en dos plantas físicamente separadas, unificadas mediante una solución de **Industria 4.0**:

| Planta | Tipo | Operación |
|--------|------|-----------|
| **Planta 1 — CIMA** | Brownfield | Manufactura de componentes base (Aluminio 6061) con retrofit IoT |
| **Planta 2 — Celda 3105** | Greenfield | Recepción, Quality Gate (visión artificial) y paletizado con cobot |

---

## Arquitectura del sistema

```
Tú (instrucciones en lenguaje natural)
        ↓
Claude Code (orquestador — lee CLAUDE.md)
        ↓
n8n (middleware de flujos)
        ↓
┌──────────────┬──────────────┬──────────────┐
│ Agente IoT   │ Agente Visión│ Agente Cobot │
│ ESP32-S3     │ Cognex+Cloud │ OpenClaw     │
│ SCT-013      │              │              │
└──────┬───────┴──────────────┴──────────────┘
       ↓
MQTT Broker (Mosquitto — RPi5)
       ↓
InfluxDB → Grafana + Node-RED (Dashboard KPIs)
       ↓
GitHub (auto-push diario)
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Orquestador | Claude Code |
| Middleware | n8n |
| IoT Gateway | ESP32-S3 + PlatformIO |
| Sensor corriente | SCT-013 AC |
| Trazabilidad | RC522 RFID (Pasaporte Digital) |
| Cobot | OpenClaw |
| MQTT Broker | Mosquitto (RPi5) |
| Time-series DB | InfluxDB |
| Dashboard SCADA | Node-RED + Grafana |
| CI/CD | GitHub Actions |

---

## Estructura del repositorio

```
/
├── CLAUDE.md                        ← Instrucciones para Claude Code
├── README.md                        ← Este archivo
├── .gitignore
├── .github/workflows/
│   └── auto_push.yml                ← CI: valida estructura + sync diario
├── firmware/esp32-s3/               ← Proyecto PlatformIO
│   ├── platformio.ini               ← Configuración y dependencias
│   ├── src/main.cpp                 ← Código principal del gateway IoT
│   ├── include/config.h             ← Pines y parámetros
│   ├── scripts/inject_env.py        ← Inyecta .env en compilación
│   └── .env.template                ← Plantilla de credenciales
├── flows/
│   ├── n8n/mqtt_to_influxdb.json    ← Flujo MQTT → InfluxDB + alertas
│   └── nodered/                     ← Dashboard SCADA
├── scripts/
│   └── setup_rpi5.sh                ← Instalación completa del RPi5
├── agentes/                         ← Scripts de agentes activos
├── bitacora/README.md               ← Log automático de Claude Code
├── config/mqtt_topics.md            ← Mapa de todos los topics MQTT
├── dashboard/                       ← Config Grafana
└── docs/                            ← Documentación técnica
```

---

## KPIs del proyecto

| KPI | Descripción |
|-----|-------------|
| **Eficiencia Energética** | Consumo kWh total de ambas plantas |
| **Trazabilidad** | Pasaporte digital RFID — sin datos de origen, no hay proceso final |
| **Lead Time (OEE Lite)** | Tiempo total desde inicio hasta fin del proceso |
| **Rendimiento Calidad** | Piezas producidas vs. aprobadas en Quality Gate |

---

## Inicio rápido

```bash
# 1. Instalar servicios en Raspberry Pi 5
ssh pi@IP_DEL_RPI5
git clone https://github.com/TU_USUARIO/TU_REPO.git /opt/smart-manufacturing
sudo bash scripts/setup_rpi5.sh

# 2. Compilar y flashear firmware ESP32-S3
cd firmware/esp32-s3
cp .env.template .env   # completar con WiFi e IP del RPi5
pio run --target upload

# 3. Abrir Claude Code como orquestador
claude   # desde la raíz del repo
```

Ver guía detallada en [`docs/INICIO_RAPIDO.md`](docs/INICIO_RAPIDO.md)

---

## Fases del proyecto

| Fase | Semanas | Objetivo |
|------|---------|---------|
| 1 | 1–6 | Infraestructura: RPi5, MQTT, ESP32-S3 operando |
| 2 | 7–12 | Planta 2: Cobot, RFID, Dashboard en vivo |
| 3 | 13–17 | Integración total: Gemelo digital + detección de anomalías con IA |

---

*Proyecto académico — Tecnológico de Monterrey*
