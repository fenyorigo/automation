#include "HttpApi.h"

#include <WiFi.h>

namespace {
constexpr char FIRMWARE_VERSION[] = "0.2.0";
}

HttpApi::HttpApi(const WifiManager &wifiManager,
                 const SensorState &sensorState)
    : wifiManager_(wifiManager), sensorState_(sensorState) {}

void HttpApi::update() {
  if (!wifiManager_.isConnected()) {
    return;
  }
  if (!started_) {
    start();
  }
  server_.handleClient();
}

void HttpApi::start() {
  server_.on("/api/v1/health", HTTP_GET, [this]() { handleHealth(); });
  server_.on("/api/v1/device", HTTP_GET, [this]() { handleDevice(); });
  server_.on("/api/v1/measurements", HTTP_GET,
             [this]() { handleMeasurements(); });
  server_.onNotFound([this]() { handleNotFound(); });
  server_.begin();
  started_ = true;

  Serial.println("HTTP API started:");
  Serial.print("  http://");
  Serial.print(WiFi.localIP());
  Serial.println("/api/v1/measurements");
}

void HttpApi::sendJson(int statusCode, const String &payload) {
  server_.sendHeader("Cache-Control", "no-store");
  server_.send(statusCode, "application/json; charset=utf-8", payload);
}

void HttpApi::handleHealth() {
  String payload;
  payload.reserve(180);
  payload += "{\"status\":\"ok\",\"device_id\":";
  payload += jsonString(wifiManager_.hostname());
  payload += ",\"uptime_seconds\":";
  payload += millis() / 1000;
  payload += ",\"wifi_rssi_dbm\":";
  payload += WiFi.RSSI();
  payload += ",\"sensor_ok\":";
  payload += sensorState_.valid ? "true" : "false";
  payload += '}';
  sendJson(200, payload);
}

void HttpApi::handleDevice() {
  String payload;
  payload.reserve(300);
  payload += "{\"schema_version\":1,\"device_id\":";
  payload += jsonString(wifiManager_.hostname());
  payload += ",\"mac_address\":";
  payload += jsonString(WiFi.macAddress());
  payload += ",\"ip_address\":";
  payload += jsonString(WiFi.localIP().toString());
  payload += ",\"firmware_version\":";
  payload += jsonString(FIRMWARE_VERSION);
  payload += ",\"uptime_seconds\":";
  payload += millis() / 1000;
  payload += ",\"wifi_rssi_dbm\":";
  payload += WiFi.RSSI();
  payload += '}';
  sendJson(200, payload);
}

void HttpApi::handleMeasurements() {
  String payload;
  payload.reserve(420);
  payload += "{\"schema_version\":1,\"device_id\":";
  payload += jsonString(wifiManager_.hostname());
  payload += ",\"readings\":[{\"sensor_id\":";
  payload += jsonString(sensorState_.sensorId);
  payload += ",\"sensor_type\":\"temperature\",\"unit\":\"celsius\",\"value\":";
  if (sensorState_.valid) {
    payload += String(sensorState_.temperatureC, 4);
  } else {
    payload += "null";
  }
  payload += ",\"quality\":\"";
  payload += sensorState_.valid ? "good" : "invalid";
  payload += "\",\"error_code\":";
  if (sensorState_.valid) {
    payload += "null";
  } else {
    payload += jsonString(sensorState_.errorCode);
  }
  payload += ",\"age_ms\":";
  payload += sensorState_.valid ? millis() - sensorState_.measuredAtMs : 0;
  payload += ",\"available\":";
  payload += sensorState_.available ? "true" : "false";
  payload += "}]}";
  sendJson(200, payload);
}

void HttpApi::handleNotFound() {
  sendJson(404, "{\"error\":\"not_found\"}");
}

String HttpApi::jsonString(const String &value) {
  String escaped;
  escaped.reserve(value.length() + 2);
  escaped += '"';
  for (size_t i = 0; i < value.length(); ++i) {
    const char character = value[i];
    if (character == '"' || character == '\\') {
      escaped += '\\';
    }
    escaped += character;
  }
  escaped += '"';
  return escaped;
}
