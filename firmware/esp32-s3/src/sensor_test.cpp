/*
 * sensor_test.cpp — Modo de prueba de sensores sin WiFi ni MQTT
 * Compilar con: pio run -e sensor_test --target upload
 *
 * Muestra lecturas SCT-013 y RC522 por Serial cada 2s.
 */

#ifdef SENSOR_TEST_ONLY

#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include "config.h"

static MFRC522 rfid_test(PIN_RFID_SS, PIN_RFID_RST);

static float readIrms() {
  int64_t sumSq = 0;
  const int offset = 2048;
  for (int n = 0; n < 1480; n++) {
    int raw = analogRead(PIN_SCT) - offset;
    sumSq += (int64_t)raw * raw;
    delayMicroseconds(10);
  }
  float vrms = sqrtf((float)sumSq * 2.0f / 1480) / 4096.0f * 3.3f;
  float irms = vrms * SCT_RATIO * SCT_CALIBRATION;
  return irms < SCT_MIN_CURRENT ? 0.0f : irms;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n╔══════════════════════════════════╗");
  Serial.println("║  SENSOR TEST — Sin WiFi/MQTT     ║");
  Serial.printf( "║  SCT-013 → GPIO%-2d               ║\n", PIN_SCT);
  Serial.printf( "║  RC522   → SS=%-2d RST=%-2d          ║\n", PIN_RFID_SS, PIN_RFID_RST);
  Serial.printf( "║  SPI     → MOSI=%-2d MISO=%-2d SCK=%-2d║\n", PIN_SPI_MOSI, PIN_SPI_MISO, PIN_SPI_SCK);
  Serial.println("╚══════════════════════════════════╝\n");

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  SPI.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_RFID_SS);
  rfid_test.PCD_Init();
  delay(50);

  byte ver = rfid_test.PCD_ReadRegister(MFRC522::VersionReg);
  if (ver == 0x91 || ver == 0x92) {
    Serial.printf("[RC522] OK — versión: 0x%02X\n", ver);
  } else {
    Serial.printf("[RC522] ADVERTENCIA — respuesta inesperada: 0x%02X (revisar cableado)\n", ver);
  }
  Serial.println("[SCT-013] Leyendo cada 2s — acerca un cable con corriente al sensor");
  Serial.println("─────────────────────────────────────────\n");
}

void loop() {
  float irms  = readIrms();
  float power = irms * 220.0f * 0.85f;
  Serial.printf("[SCT-013]  Irms: %5.3f A  |  Potencia: %6.1f W\n", irms, power);

  if (rfid_test.PICC_IsNewCardPresent() && rfid_test.PICC_ReadCardSerial()) {
    String uid;
    for (byte i = 0; i < rfid_test.uid.size; i++) {
      if (i) uid += ':';
      if (rfid_test.uid.uidByte[i] < 0x10) uid += '0';
      uid += String(rfid_test.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();
    Serial.printf("[RC522]  *** Tarjeta detectada: %s ***\n", uid.c_str());
    rfid_test.PICC_HaltA();
    rfid_test.PCD_StopCrypto1();
  }

  delay(2000);
}

#endif  // SENSOR_TEST_ONLY
