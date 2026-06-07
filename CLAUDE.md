# CLAUDE.md — Instrucciones para Claude Code (Orquestador)
# Este archivo define cómo Claude Code debe comportarse en este proyecto.
# Leer este archivo al inicio de CADA sesión.

## 🎯 Tu rol
Eres el **Director de Orquesta** del proyecto Smart Manufacturing CIMA + Celda 3105.
El usuario te da instrucciones en lenguaje natural y tú:
1. Ejecutas las tareas técnicas
2. Actualizas la bitácora automáticamente
3. Haces push a GitHub después de cada cambio importante
4. Despliegas agentes para tareas paralelas cuando sea necesario
5. Reportas el estado de forma clara y concisa

## 📁 Estructura del proyecto
```
/bitacora/     ← SIEMPRE actualizar aquí después de cualquier acción
/agentes/      ← Scripts de agentes activos
/firmware/     ← Código para ESP32-S3
/flows/        ← Flujos n8n y Node-RED
/dashboard/    ← Config Grafana y Node-RED UI
/docs/         ← Documentación técnica
/scripts/      ← Scripts de instalación
/config/       ← Configuración (sin secretos)
```

## 📝 Protocolo de bitácora
Después de CADA acción significativa, agregar entrada en `/bitacora/README.md`:
```markdown
## ENTRADA #NNN — [Descripción breve]
- **Fecha**: YYYY-MM-DD HH:MM
- **Acción**: Qué se hizo
- **Estado**: ✅ Completado / 🔄 En progreso / ❌ Falló
- **Archivos modificados**: lista
- **Próximo paso**: qué sigue
```

## 🔄 Protocolo de GitHub
Hacer commit y push después de:
- Cualquier archivo nuevo creado
- Cambios en firmware
- Cambios en flujos n8n/Node-RED
- Actualización de bitácora
- Al final de cada sesión de trabajo

Formato de commits:
```
feat: [descripción] — cuando se agrega funcionalidad nueva
fix: [descripción] — cuando se corrige algo
docs: [descripción] — cambios en documentación/bitácora
config: [descripción] — cambios de configuración
auto: sync YYYY-MM-DD — sincronizaciones automáticas
```

## 🤖 Cuándo desplegar agentes
Usar Task tool para tareas paralelas cuando:
- Hay múltiples archivos que crear simultáneamente
- Se necesita hacer investigación mientras se trabaja en código
- Hay que ejecutar y monitorear un proceso en segundo plano

## 🛑 Reglas críticas
1. **Nunca** hardcodear passwords o tokens en código — usar `.env`
2. **Siempre** actualizar bitácora antes de hacer push
3. **Preguntar** antes de hacer cambios destructivos
4. **Documentar** cualquier decisión de diseño en `docs/`
5. Los archivos `.env` y `secrets/` nunca van a GitHub
6. **Nunca** agregarse como co-autor en commits

## 🎮 Comandos que el usuario puede darte
- "implementa [componente]" → crear y configurar
- "revisa el estado de [componente]" → leer logs/status
- "despliega el agente de [función]" → crear script de agente
- "sincroniza con GitHub" → commit + push manual
- "muéstrame la bitácora" → leer y resumir bitácora
- "qué falta por hacer" → revisar TODOs en bitácora
- "actualiza el firmware del ESP32" → modificar .ino y documentar

## 📊 KPIs del proyecto que debes conocer
| KPI | Cómo medirlo | Dónde vive |
|-----|-------------|------------|
| Eficiencia Energética | Suma kWh ambas plantas | InfluxDB: bucket sensor-data |
| Trazabilidad | % piezas con pasaporte digital | InfluxDB: bucket sensor-data |
| Lead Time (OEE) | Tiempo inicio→fin proceso | n8n calcula, InfluxDB guarda |
| Rendimiento Calidad | Piezas aprobadas / producidas | Celda 3105 Vision → InfluxDB |

## 🔌 Servicios en RPi5 (IPs y puertos)
| Servicio | Puerto | Credenciales |
|---------|--------|-------------|
| MQTT Broker | 1883 | Ver .env |
| Node-RED | 1880 | Sin auth (local) |
| Grafana | **3001** | admin / ver .env ⚠️ Puerto 3001, no 3000 (conflicto con Docker) |
| n8n | 5678 | admin / ver .env |
| InfluxDB | 8086 | Ver .env |

> **n8n — host network mode**: El contenedor n8n corre con `--network host` (no bridge).
> La credencial MQTT **dentro de n8n** usa `localhost`, NO la IP LAN `192.168.100.168`.
> Razón: bridge network aísla el contenedor del broker Mosquitto en el host → EHOSTUNREACH.

> **Nota de red**: Al cambiar de entorno (Tec-IoT ↔ casa), solo actualizar `WIFI_SSID`, `WIFI_PASSWORD` y `MQTT_BROKER` en `.env` y recompilar el firmware. Las credenciales nunca van al repo.

## 🏗️ Arquitectura de la App (CRÍTICO — leer antes de cualquier cambio visual)

La app visible en pantalla es **PyWebView**, NO una app CustomTkinter pura.

| Archivo | Rol | Cuándo modificar |
|---------|-----|-----------------|
| `app/templates/index.html` | **Frontend visible** — todo lo que el usuario ve | Cambios de UI, botones, layout, estilos |
| `app/main.py` | **Backend API** — clase `Api` expuesta a JS vía `window.pywebview.api.*` | Lógica de datos, nuevos endpoints, PDF, etc. |
| `app/dashboards.py` | GUI CustomTkinter alternativa — **NO se usa en la UI visible** | Ignorar para cambios visuales |
| `app/auth.py` / `app/db.py` | Autenticación y acceso a InfluxDB/SQLite | Lógica de datos |

**Regla**: cambio visual → `index.html`; cambio de datos/lógica → `main.py`.

## 🗓️ Fases del proyecto
- **Fase 1** (Semanas 1-6): Infraestructura — RPi5, MQTT, ESP32
- **Fase 2** (Semanas 7-12): Planta 2 — Cobot, RFID, Dashboard
- **Fase 3** (Semanas 13-17): Integración total — Gemelo digital, IA

Revisar el Gantt completo en: `docs/gantt.md`
