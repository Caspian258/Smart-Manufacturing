#pragma once
#ifndef WIFI_SSID
  #define WIFI_SSID     "FALLBACK_SSID"
#endif
#ifndef WIFI_PASSWORD
  #define WIFI_PASSWORD "FALLBACK_PASS"
#endif
#ifndef MQTT_BROKER
  #define MQTT_BROKER   "192.168.1.100"
#endif
#ifndef MQTT_PORT
  #define MQTT_PORT     8883
#endif
#ifndef MQTT_TLS
  #define MQTT_TLS      1
#endif
#ifndef MQTT_USER
  #define MQTT_USER     "esp32_cima"
#endif
#ifndef MQTT_PASSWORD
  #define MQTT_PASSWORD "changeme"
#endif
#ifndef MACHINE_ID
  #define MACHINE_ID    "fresadora"
#endif
#define CLIENT_ID       "esp32-cima-" MACHINE_ID

// SCT-013 — ADC1_CH0 en ESP32-S3 (GPIO1, seguro con WiFi activo)
#define PIN_SCT                  1

// SCT-013-030 (30A/1V) — salida de voltaje, burden interno, compatible con circuito LM358 existente
#define SCT_RATIO        30.0f  // 30A por cada 1V de salida
#define SCT_CALIBRATION     1.333f  // Empírico: torno ROMI — pinza=6.80A ESP32=5.10A → factor=1.333
#define SCT_SAMPLE_MS       500
#define SCT_MIN_CURRENT     0.30f   // Umbral ruido ADC: cargas reales > 0.30A (~66W a 220V)
                                    // Foco 40W = 0.18A → no medible (por debajo del umbral)
                                    // Torno industrial = ~7A → medible ✅

// Red industrial
#define GRID_VOLTAGE        220.0f
#define POWER_FACTOR        0.85f

// RC522 RFID — SPI2 explícito
#define PIN_SPI_MOSI    13
#define PIN_SPI_MISO    11
#define PIN_SPI_SCK     12
#define PIN_RFID_SS     10
#define PIN_RFID_RST    9
#define PIN_LED         48
#define PIN_CYCLE_BTN   0

#define PUBLISH_INTERVAL_MS   5000
#define HEARTBEAT_INTERVAL_MS 30000
#define NTP_SERVER            "pool.ntp.org"
#define NTP_UTC_OFFSET_SEC    (-6 * 3600)
#define TOPIC_HEARTBEAT       "cima/system/heartbeat"
#define TOPIC_RFID            "cima/rfid/scan"
#define TOPIC_CMD_CYCLE       "cima/commands/cycle"
#define TOPIC_CMD_CALIBRATE   "cima/commands/calibrate"
#define TOPIC_CAL_RESULT      "cima/calibration/result"

#ifdef DEBUG_MODE
  #define LOG(fmt, ...) Serial.printf("[%lu] " fmt "\n", millis(), ##__VA_ARGS__)
#else
  #define LOG(fmt, ...)
#endif
