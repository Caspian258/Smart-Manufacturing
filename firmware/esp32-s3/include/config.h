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

// SCT-013 30A/1V — salida de voltaje, burden interno
#define SCT_RATIO        30.0f  // 30A por cada 1V de salida
#define SCT_CALIBRATION     0.0938f // Empírico: 6.80A torno / 72.48A medido (CAL=1.0), semiciclo ×√2
#define SCT_SAMPLE_MS       500
#define SCT_MIN_CURRENT     0.50f   // Umbral: ruido ADC ~0A real; torno nominal=6.80A >> 0.50A

// Red industrial
#define GRID_VOLTAGE        220.0f
#define POWER_FACTOR        0.85f

// RC522 RFID — SPI2 explícito
#define PIN_SPI_MOSI    11
#define PIN_SPI_MISO    13
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
