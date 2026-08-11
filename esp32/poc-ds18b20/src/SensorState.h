#pragma once

#include <Arduino.h>

struct SensorState {
  String sensorId;
  float temperatureC = 0.0F;
  bool available = false;
  bool valid = false;
  const char *errorCode = "sensor_not_found";
  uint32_t measuredAtMs = 0;
};
