#pragma once

#include <Arduino.h>
#include <IPAddress.h>

enum class NetworkMode : uint8_t {
  Dhcp = 1,
  DhcpReservation = 2,
  Static = 3,
};

struct WifiConfig {
  String hostname;
  String ssid;
  String password;
  NetworkMode mode = NetworkMode::Dhcp;
  IPAddress expectedIp;
  IPAddress subnet;
  IPAddress gateway;
  IPAddress dns1;
  IPAddress dns2;
};

class WifiManager {
 public:
  void begin();
  void update();

  bool isConnected() const;
  bool isConfigured() const;
  bool shouldSuppressSensorOutput() const;
  const String &hostname() const;

 private:
  enum class WizardStep : uint8_t {
    Inactive,
    Hostname,
    Ssid,
    Password,
    Mode,
    ExpectedIp,
    ReservationSubnet,
    ReservationGateway,
    ReservationDns,
    StaticIp,
    StaticSubnet,
    StaticGateway,
    StaticDns1,
    StaticDns2,
    Confirm,
    ConfirmReservation,
  };

  void processSerial();
  void handleLine(String line);
  void startWizard();
  void cancelWizard();
  void showPrompt() const;
  void showSummary() const;

  bool loadConfig();
  bool saveConfig(const WifiConfig &config);
  void clearConfig();

  void startConnection();
  void updateConnection();
  void scheduleRetry();
  void resetWifiRadio();
  void printConnectionDetails() const;

  static bool parseRequiredIp(const String &text, IPAddress &address);
  static bool parseOptionalIp(const String &text, IPAddress &address);
  static bool isValidHostname(const String &hostname);
  static bool validateNetwork(const WifiConfig &config);
  static uint32_t addressValue(const IPAddress &address);
  static const char *modeName(NetworkMode mode);

  WifiConfig config_;
  WifiConfig candidate_;
  WizardStep wizardStep_ = WizardStep::Inactive;
  String serialBuffer_;

  bool configured_ = false;
  bool connecting_ = false;
  bool wasConnected_ = false;
  bool disconnectedTimerActive_ = false;
  uint8_t retryIndex_ = 0;
  uint8_t consecutiveFailures_ = 0;
  uint32_t connectionStartedAt_ = 0;
  uint32_t nextRetryAt_ = 0;
  uint32_t disconnectedSince_ = 0;
};
