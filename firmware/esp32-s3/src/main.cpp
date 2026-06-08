/*
 * main.cpp — IoT Gateway Planta 1: CIMA
 * Modo: REAL — SCT-013-030 (30A/1V) con GPIO1
 *
 * Publica datos de energía cada 5 segundos via MQTT.
 * RFID toggle: 1er scan = INICIO pieza, 2do scan misma tarjeta = FIN pieza.
 * measurePower() usa offset DC dinámico + RMS por tiempo (500ms ≈ 30 ciclos de 60Hz)
 * con compensación de media onda (método Naylamp).
 */

#include <Arduino.h>
#include <esp_task_wdt.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ArduinoOTA.h>
#include <SPI.h>
#include <MFRC522.h>
#include <time.h>
#include "config.h"
#include "ca_cert.h"

// ─── Clientes globales ────────────────────────────────────────────────────────
#if MQTT_TLS
WiFiClientSecure wifiClient;
#else
WiFiClient       wifiClient;
#endif
PubSubClient mqtt(wifiClient);
MFRC522 rfid(PIN_RFID_SS, PIN_RFID_RST);

// ─── Offset DC del SCT-013 (calibrado en setup(), antes de WiFi) ─────────────
static int g_dcOffset = 2048;

// ─── Estado del ciclo ────────────────────────────────────────────────────────
struct CycleState {
  bool     active   = false;
  uint32_t startMs  = 0;
  float    energyWh = 0.0f;
  String   partId   = "";
  String   uid      = "";
  String   startTs  = "";
};
CycleState cycle;

uint32_t lastPublish   = 0;
uint32_t lastHeartbeat = 0;
uint32_t lastRfidMs    = 0;
String   lastRfidUid   = "";

// ─── Utilidades ──────────────────────────────────────────────────────────────
String isoTimestamp() {
  struct tm t;
  if (!getLocalTime(&t)) return "1970-01-01T00:00:00Z";
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
  return String(buf);
}

void ledBlink(uint8_t times, uint16_t ms = 100) {
  for (uint8_t i = 0; i < times; i++) {
    digitalWrite(PIN_LED, HIGH); delay(ms);
    digitalWrite(PIN_LED, LOW);  delay(ms);
  }
}

// ─── Medición de potencia (SCT-013 30A/1V) ──────────────────────────────────────
struct PowerReading {
  float irmsA;
  float powerW;
  float energyKwh;
};

PowerReading measurePower() {
  // Paso 1 — Usar offset DC calibrado en setup() (WiFi interfiere con ADC1 en loop)
  int dcOffset = g_dcOffset;

  // Paso 2 — Muestreo RMS por tiempo (500ms ≈ 30 ciclos de 60Hz)
  float    sumSq  = 0.0f;
  int      N      = 0;
  uint32_t tStart = millis();
  while (millis() - tStart < SCT_SAMPLE_MS) {
    int   raw     = analogRead(PIN_SCT) - dcOffset;
    float voltage = raw * (3.3f / 4095.0f);
    sumSq += voltage * voltage;
    N++;
    delayMicroseconds(200);
  }

  // Paso 3 — RMS media onda × √2: LM358 single supply recorta semiciclo negativo
  float vrms = (N > 0) ? sqrtf(2.0f * sumSq / N) : 0.0f;

  // Paso 4 — Conversión V → A (SCT-013 30A/1V: salida de voltaje)
  float irms = vrms * SCT_RATIO * SCT_CALIBRATION;

  // Paso 5 — Umbral de ruido y potencia
  if (irms < SCT_MIN_CURRENT) irms = 0.0f;
  float power  = irms * GRID_VOLTAGE * POWER_FACTOR;
  float energy = power * (SCT_SAMPLE_MS / 1000.0f) / 3600000.0f;

  Serial.printf("[ENERGY] %.0fW  %.2fA  dc=%d\n", power, irms, dcOffset);
  return { irms, power, energy };
}

// ─── Lectura RFID ────────────────────────────────────────────────────────────
String readRFID() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return "";
  String uid;
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (i) uid += ':';
    if (rfid.uid.uidByte[i] < 0x10) uid += '0';
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  return uid;
}

// ─── Diagnóstico de amperaje ────────────────────────────────────────────────
void testAmperage() {
  Serial.println("\n[TEST] === Prueba de Amperaje (10 muestras x 1s) ===");
  const int offset = g_dcOffset;
  float samples[10];
  float minA = 1e9f, maxA = -1e9f, sumA = 0.0f;

  for (int i = 0; i < 10; i++) {
    int64_t  sumSq = 0;
    int      count = 0;
    uint32_t t0    = millis();
    while (millis() - t0 < 1000) {
      int raw = analogRead(PIN_SCT) - offset;
      sumSq += (int64_t)raw * raw;
      count++;
      delayMicroseconds(10);
    }
    float vrms = (count > 0)
      ? sqrtf(2.0f * (float)sumSq / count) / 4096.0f * 3.3f
      : 0.0f;
    float irms = vrms * SCT_RATIO * SCT_CALIBRATION;
    if (irms < SCT_MIN_CURRENT) irms = 0.0f;
    float power = irms * 220.0f * 0.85f;
    samples[i]  = irms;
    sumA        += irms;
    if (irms < minA) minA = irms;
    if (irms > maxA) maxA = irms;
    Serial.printf("  [%2d/10] Irms: %.3f A  ->  %.1f W\n", i + 1, irms, power);
  }

  float avgA = sumA / 10.0f;
  float varA = maxA - minA;
  Serial.println("[TEST] ---------------------------------");
  Serial.printf("[TEST] Promedio:  %.3f A  |  %.1f W\n", avgA, avgA * 220.0f * 0.85f);
  Serial.printf("[TEST] Minimo:    %.3f A  |  Maximo: %.3f A  |  Variacion: %.3f A\n",
                minA, maxA, varA);

  if (avgA < 0.05f) {
    Serial.println("[TEST] ADVERTENCIA: senal casi cero — verificar conexion del SCT-013");
  } else if (varA > avgA * 0.30f) {
    Serial.println("[TEST] ADVERTENCIA: variacion > 30% del promedio — posible ruido en la senal");
  } else {
    Serial.println("[TEST] OK: circuito funcionando correctamente");
  }
  Serial.println("[TEST] ===================================\n");
}

// ─── Publicación MQTT ────────────────────────────────────────────────────────
void publishEnergy(float irms, float power, float energy) {
  JsonDocument doc;
  doc["machine_id"]   = MACHINE_ID;
  doc["irms_a"]       = roundf(irms * 100) / 100.0f;
  doc["power_w"]      = roundf(power);
  doc["energy_kwh"]   = energy;
  doc["cycle_active"] = cycle.active;
  doc["sct_ratio"]    = SCT_RATIO;
  if (cycle.active) doc["part_id"] = cycle.partId;
  doc["ts"]           = isoTimestamp();
  doc["rssi"]         = WiFi.RSSI();

  char topic[64];
  snprintf(topic, sizeof(topic), "cima/machines/%s/energy", MACHINE_ID);
  char payload[320];
  serializeJson(doc, payload);
  if (!mqtt.publish(topic, payload, false)) {  // retain=false
    Serial.printf("[MQTT] publish falló: %s\n", topic);
  }
  if (cycle.active) cycle.energyWh += energy * 1000.0f;
}

void publishHeartbeat() {
  JsonDocument doc;
  doc["device"]   = CLIENT_ID;
  doc["machine"]  = MACHINE_ID;
  doc["ip"]       = WiFi.localIP().toString();
  doc["rssi"]     = WiFi.RSSI();
  doc["uptime"]   = millis() / 1000;
  doc["mode"]     = "real";
  doc["ts"]       = isoTimestamp();
  char payload[200];
  serializeJson(doc, payload);
  if (!mqtt.publish(TOPIC_HEARTBEAT, payload)) {
    Serial.println("[MQTT] heartbeat publish falló");
  } else {
    Serial.println("[HEARTBEAT] enviado");
  }
}

// ─── MQTT callback ────────────────────────────────────────────────────────────
void onMqttMessage(char* topic, uint8_t* payload, unsigned int len) {
  String msg;
  msg.reserve(len);
  for (unsigned int i = 0; i < len; i++) msg += (char)payload[i];
  Serial.printf("[MQTT IN] %s: %s\n", topic, msg.c_str());

  if (String(topic) == TOPIC_CMD_CYCLE) {
    JsonDocument cmd;
    if (deserializeJson(cmd, msg) != DeserializationError::Ok) return;
    const char* action = cmd["action"] | "";
    if (strcmp(action, "start") == 0 && !cycle.active) {
      cycle.active   = true;
      cycle.startMs  = millis();
      cycle.energyWh = 0.0f;
      cycle.partId   = cmd["part_id"] | "MANUAL-001";
      Serial.printf("[CYCLE] Iniciado: %s\n", cycle.partId.c_str());
      ledBlink(2, 200);
    } else if (strcmp(action, "stop") == 0 && cycle.active) {
      cycle.active = false;
      Serial.printf("[CYCLE] Terminado. Energía: %.2f Wh\n", cycle.energyWh);
    }
  }

  if (String(topic) == TOPIC_CMD_CALIBRATE) {
    JsonDocument cmd;
    if (deserializeJson(cmd, msg) != DeserializationError::Ok) return;
    float real_amps = cmd["real_amps"] | 0.0f;
    if (real_amps > 0.1f) {
      auto p = measurePower();
      if (p.irmsA > 0.01f) {
        float correction       = real_amps / p.irmsA;
        float suggested_cal    = SCT_CALIBRATION * correction;
        JsonDocument resp;
        resp["measured_a"]       = roundf(p.irmsA * 1000) / 1000.0f;
        resp["real_a"]           = real_amps;
        resp["correction"]       = roundf(correction * 100) / 100.0f;
        resp["suggested_cal"]    = roundf(suggested_cal * 100) / 100.0f;
        resp["current_cal"]      = SCT_CALIBRATION;
        char respPayload[256];
        serializeJson(resp, respPayload);
        mqtt.publish(TOPIC_CAL_RESULT, respPayload);
        Serial.printf("[CAL] real=%.2fA medido=%.3fA correction=%.2fx calibration_sugerida=%.2f\n",
                      real_amps, p.irmsA, correction, suggested_cal);
      } else {
        Serial.println("[CAL] Señal demasiado débil — verificar conexión SCT-013");
      }
    }
  }
}

// ─── Helpers WiFi ────────────────────────────────────────────────────────────
#ifdef WIFI_BSSID
static uint8_t s_bssid[6];
static bool    s_bssid_parsed = false;

static bool parseBSSID(const char* str, uint8_t out[6]) {
  return sscanf(str, "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
    &out[0],&out[1],&out[2],&out[3],&out[4],&out[5]) == 6;
}
#endif

static void wifiBegin() {
#ifdef WIFI_BSSID
  if (!s_bssid_parsed)
    s_bssid_parsed = parseBSSID(WIFI_BSSID, s_bssid);
  if (s_bssid_parsed) {
#ifdef WIFI_CHANNEL
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD, WIFI_CHANNEL, s_bssid);
#else
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 0, s_bssid);
#endif
    return;
  }
#endif
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

// ─── Reconexión WiFi ─────────────────────────────────────────────────────────
void reconnectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("[WiFi] Reconectando");
  WiFi.disconnect();
  wifiBegin();
  uint8_t attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 3) {
    delay(500);
    Serial.print('.');
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Reconectado → IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] Sin conexión — continuando sin red");
  }
}

// ─── Reconexión MQTT ──────────────────────────────────────────────────────────
void reconnectMQTT() {
#if MQTT_TLS
  // Re-sincronizar NTP si el tiempo no es válido — necesario para validar certs TLS
  if (time(nullptr) < 1000000000UL) {
    configTime(NTP_UTC_OFFSET_SEC, 0, NTP_SERVER);
    Serial.print("[NTP] Re-sincronizando");
    uint32_t t0 = millis();
    while (time(nullptr) < 1000000000UL && millis() - t0 < 10000) {
      delay(200); Serial.print('.'); esp_task_wdt_reset();
    }
    Serial.println(time(nullptr) >= 1000000000UL ? " OK" : " TIMEOUT");
  }
#endif
  uint8_t attempts = 0;
  while (!mqtt.connected() && attempts < 3) {
#if MQTT_TLS
    wifiClient.setInsecure();
#endif
    Serial.printf("[MQTT] Conectando a %s...\n", MQTT_BROKER);
    if (mqtt.connect(CLIENT_ID, MQTT_USER, MQTT_PASSWORD)) {
      mqtt.subscribe(TOPIC_CMD_CYCLE);
      mqtt.subscribe(TOPIC_CMD_CALIBRATE);
      Serial.println("[MQTT] Conectado OK");
      ledBlink(4, 80);
    } else {
      Serial.printf("[MQTT] Fallo rc=%d — reintento en 5s\n", mqtt.state());
#if MQTT_TLS
      char sslErr[128];
      wifiClient.lastError(sslErr, sizeof(sslErr));
      Serial.printf("[TLS] mbedTLS: %s\n", sslErr);
      Serial.printf("[TLS] time()=%lu (esperado ~1775834000+)\n", (unsigned long)time(nullptr));
#endif
      for (uint8_t i = 0; i < 10; i++) { delay(500); esp_task_wdt_reset(); }
      attempts++;
    }
  }
}

// ─── Setup ───────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n════════════════════════════════");
  Serial.println(" CIMA IoT Gateway");
  Serial.printf(" Maquina: %s\n", MACHINE_ID);
  Serial.println("════════════════════════════════\n");

  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_CYCLE_BTN, INPUT_PULLUP);

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  // Calibrar DC offset antes de WiFi (WiFi interfiere con ADC1 en GPIO1)
  // Con LM358 single-supply (sin bias VCC/2) el offset debe ser ~0 sin carga.
  // Si es alto (carga activa en boot), forzar 0 para evitar DC espurio en sumSq.
  {
    int32_t s = 0;
    for (int i = 0; i < 1000; i++) { s += analogRead(PIN_SCT); delayMicroseconds(100); }
    g_dcOffset = s / 1000;
    if (g_dcOffset > 300) {
      Serial.printf("[SCT] Offset=%d > 300 — carga activa en boot? Forzando offset=0\n", g_dcOffset);
      g_dcOffset = 0;
    } else {
      Serial.printf("[SCT] DC offset calibrado: %d\n", g_dcOffset);
    }
  }
  SPI.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_RFID_SS);
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);
  Serial.println("[RFID] RC522 inicializado");

  // Diagnóstico RC522: leer VersionReg para confirmar SPI OK
  byte ver = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("[RFID] VersionReg: 0x%02X\n", ver);
  if (ver == 0x91 || ver == 0x92) {
    Serial.println("[RFID] ✅ RC522 OK");
  } else if (ver == 0x00 || ver == 0xFF) {
    Serial.println("[RFID] ❌ SPI no responde — verificar cableado");
  } else {
    Serial.printf("[RFID] ⚠️ Valor inesperado: 0x%02X\n", ver);
  }

  // WiFi
  wifiBegin();
  Serial.print("[WiFi] Conectando");
  uint8_t attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500); Serial.print('.'); attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] OK → IP: %s\n", WiFi.localIP().toString().c_str());
    ledBlink(5, 80);
  } else {
    Serial.println("\n[WiFi] Sin conexión — verificar credenciales en .env");
  }

  // Si WiFi aún no conectó, esperar hasta 15s más antes de NTP
  if (WiFi.status() != WL_CONNECTED) {
    Serial.print("[WiFi] Esperando");
    uint32_t wStart = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - wStart < 15000) {
      delay(500); Serial.print('.');
    }
    if (WiFi.status() == WL_CONNECTED)
      Serial.printf(" OK → IP: %s\n", WiFi.localIP().toString().c_str());
    else
      Serial.println(" TIMEOUT");
  }

  // NTP — esperar sincronización antes de validar certificados TLS
  configTime(NTP_UTC_OFFSET_SEC, 0, NTP_SERVER);
  Serial.print("[NTP] Sincronizando");
  {
    uint32_t ntpStart = millis();
    time_t now = 0;
    while (now < 1000000000UL && millis() - ntpStart < 15000) {
      delay(200);
      Serial.print('.');
      now = time(nullptr);
    }
    if (now >= 1000000000UL) {
      struct tm t;
      gmtime_r(&now, &t);
      char buf[32];
      strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
      Serial.printf("\n[NTP] OK → %s\n", buf);
    } else {
      Serial.println("\n[NTP] TIMEOUT — se reintentará antes de conectar MQTT");
    }
  }

  // OTA
  ArduinoOTA.setHostname(CLIENT_ID);
  ArduinoOTA.begin();

  // MQTT — TLS
#if MQTT_TLS
  wifiClient.setHandshakeTimeout(30);
  // TODO: setCACert() falla en ESP32 Arduino 3.x / ESP-IDF 5.x con CA custom
  // (bug conocido de mbedTLS: comparación estricta ASN.1 de nombres)
  // La conexión TLS sigue cifrada; auth via usuario/contraseña MQTT
  wifiClient.setInsecure();
  Serial.println("[TLS] Modo: cifrado TLS sin verificación CA (ver TODO)");
#endif
  // Usar IPAddress en lugar de string para evitar bug de IP SAN en mbedTLS
  // (ESP32 Arduino 3.x / ESP-IDF 5.x no reconoce IP strings para SAN matching)
  IPAddress mqttIp;
  if (!mqttIp.fromString(MQTT_BROKER)) {
    WiFi.hostByName(MQTT_BROKER, mqttIp);
  }
  mqtt.setServer(mqttIp, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(512);
  mqtt.setKeepAlive(30);

  Serial.println("[READY] Sistema listo\n");

  delay(2000);
  testAmperage();
}

// ─── Loop ────────────────────────────────────────────────────────────────────
void loop() {
  ArduinoOTA.handle();
  if (WiFi.status() != WL_CONNECTED) reconnectWiFi();
  if (WiFi.status() == WL_CONNECTED && !mqtt.connected()) reconnectMQTT();
  mqtt.loop();

  uint32_t now = millis();

  if (mqtt.connected()) {
    if (now - lastPublish >= PUBLISH_INTERVAL_MS) {
      lastPublish = now;
      auto p = measurePower();
      publishEnergy(p.irmsA, p.powerW, p.energyKwh);
    }
    if (now - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
      lastHeartbeat = now;
      publishHeartbeat();
    }
  }

  // RFID — toggle inicio/fin de ciclo productivo
  {
    String uid = readRFID();
    if (!uid.isEmpty()) {
      uint32_t nowMs = millis();
      // Anti-debounce: ignorar misma tarjeta dentro de 2s
      if (!(uid == lastRfidUid && (nowMs - lastRfidMs) < 2000)) {
        lastRfidUid = uid;
        lastRfidMs  = nowMs;

        if (!cycle.active) {
          // INICIO — primer scan
          cycle.active   = true;
          cycle.startMs  = nowMs;
          cycle.energyWh = 0.0f;
          cycle.partId   = uid;  // guardar UID para comparar en stop

          // Publicar evento START
          JsonDocument doc;
          doc["uid"]        = uid;
          doc["event"]      = "start";
          doc["part_id"]    = "PIEZA-" + uid + "-" + String(nowMs);
          doc["machine_id"] = MACHINE_ID;
          doc["ts"]         = isoTimestamp();
          char payload[256];
          serializeJson(doc, payload);
          if (mqtt.connected()) mqtt.publish(TOPIC_RFID, payload);
          ledBlink(2, 400);
          Serial.printf("[RFID] INICIO pieza: %s\n", uid.c_str());

        } else if (uid == cycle.partId) {
          // FIN — segunda lectura misma tarjeta
          uint32_t durMs = nowMs - cycle.startMs;

          // Publicar evento STOP
          JsonDocument doc;
          doc["uid"]        = uid;
          doc["event"]      = "stop";
          doc["part_id"]    = "PIEZA-" + uid + "-" + String(cycle.startMs);
          doc["machine_id"] = MACHINE_ID;
          doc["duration_s"] = durMs / 1000.0f;
          doc["energy_wh"]  = cycle.energyWh;
          doc["ts"]         = isoTimestamp();
          char payload[256];
          serializeJson(doc, payload);
          if (mqtt.connected()) mqtt.publish(TOPIC_RFID, payload);
          cycle.active = false;
          ledBlink(4, 100);
          Serial.printf("[RFID] FIN pieza: %s — %.1fs — %.2fWh\n",
            uid.c_str(), durMs / 1000.0f, cycle.energyWh);

        } else {
          // Tarjeta diferente mientras hay ciclo activo → ignorar
          Serial.printf("[RFID] Tarjeta diferente ignorada: %s\n", uid.c_str());
        }
      }
    }
  }
}
