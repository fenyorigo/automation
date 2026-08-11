#pragma once

#include <WebServer.h>

#include "SensorState.h"
#include "WifiManager.h"

class HttpApi {
 public:
  HttpApi(const WifiManager &wifiManager, const SensorState &sensorState);

  void update();

 private:
  void start();
  void sendJson(int statusCode, const String &payload);
  void handleHealth();
  void handleDevice();
  void handleMeasurements();
  void handleNotFound();

  static String jsonString(const String &value);

  const WifiManager &wifiManager_;
  const SensorState &sensorState_;
  WebServer server_{80};
  bool started_ = false;
};
