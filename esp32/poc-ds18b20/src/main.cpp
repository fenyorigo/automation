#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#include "HttpApi.h"
#include "SensorState.h"
#include "WifiManager.h"

constexpr uint8_t DS18B20_PIN = 16;
constexpr uint32_t MEASUREMENT_INTERVAL_MS = 2000;
constexpr uint8_t DS18B20_RESOLUTION_BITS = 12;

OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);
WifiManager wifiManager;
SensorState sensorState;
HttpApi httpApi(wifiManager, sensorState);
DeviceAddress sensorAddress = {};

bool sensorAvailable = false;
uint32_t lastMeasurementStartedAt = 0;

void printDeviceError(const char *message) {
  Serial.println(message);
}

void printAddress(const DeviceAddress address) {
  for (uint8_t i = 0; i < sizeof(DeviceAddress); ++i) {
    if (address[i] < 0x10) {
      Serial.print('0');
    }
    Serial.print(address[i], HEX);
  }
}

String addressString(const DeviceAddress address) {
  String result;
  result.reserve(sizeof(DeviceAddress) * 2);
  for (uint8_t i = 0; i < sizeof(DeviceAddress); ++i) {
    if (address[i] < 0x10) {
      result += '0';
    }
    result += String(address[i], HEX);
  }
  result.toUpperCase();
  return result;
}

bool discoverSensor() {
  if (!sensors.getAddress(sensorAddress, 0)) {
    sensorAvailable = false;
    sensorState.available = false;
    sensorState.valid = false;
    sensorState.errorCode = "sensor_not_found";
    return false;
  }

  if (!sensors.validAddress(sensorAddress) ||
      !sensors.validFamily(sensorAddress)) {
    printDeviceError("Invalid DS18B20 address.");
    sensorAvailable = false;
    sensorState.available = false;
    sensorState.valid = false;
    sensorState.errorCode = "invalid_sensor_address";
    return false;
  }

  sensors.setResolution(sensorAddress, DS18B20_RESOLUTION_BITS);
  sensorAvailable = true;
  sensorState.sensorId = addressString(sensorAddress);
  sensorState.available = true;
  sensorState.valid = false;
  sensorState.errorCode = "no_measurement";

  Serial.print("Sensor found at address: ");
  printAddress(sensorAddress);
  Serial.println();
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("ESP32 DS18B20 PoC");
  Serial.println("================");
  Serial.println("Reading temperature every 2 seconds...");

  sensors.begin();
  if (!discoverSensor()) {
    printDeviceError("No DS18B20 sensor detected. Waiting for sensor...");
  }

  // Allow the first measurement attempt to run immediately.
  lastMeasurementStartedAt = millis() - MEASUREMENT_INTERVAL_MS;
  wifiManager.begin();
}

void loop() {
  wifiManager.update();
  httpApi.update();

  const uint32_t now = millis();
  if (now - lastMeasurementStartedAt < MEASUREMENT_INTERVAL_MS) {
    delay(10);
    return;
  }
  lastMeasurementStartedAt = now;

  if (!sensorAvailable && !discoverSensor()) {
    printDeviceError("No DS18B20 sensor detected. Waiting for sensor...");
    return;
  }

  sensors.requestTemperaturesByAddress(sensorAddress);
  const float tempC = sensors.getTempC(sensorAddress);

  if (tempC == DEVICE_DISCONNECTED_C) {
    if (!wifiManager.shouldSuppressSensorOutput()) {
      printDeviceError("Sensor disconnected or read failed.");
    }
    sensorAvailable = false;
    sensorState.available = false;
    sensorState.valid = false;
    sensorState.errorCode = "sensor_read_failed";
  } else if (!wifiManager.shouldSuppressSensorOutput()) {
    Serial.print("Temperature: ");
    Serial.print(tempC, 4);
    Serial.println(" C");
  }

  if (tempC != DEVICE_DISCONNECTED_C) {
    sensorState.temperatureC = tempC;
    sensorState.available = true;
    sensorState.valid = true;
    sensorState.errorCode = nullptr;
    sensorState.measuredAtMs = millis();
  }
}
