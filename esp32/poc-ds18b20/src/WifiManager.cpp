#include "WifiManager.h"

#include <Preferences.h>
#include <WiFi.h>

namespace {
constexpr char PREFERENCES_NAMESPACE[] = "wifi-config";
constexpr uint32_t CONNECTION_TIMEOUT_MS = 15000;
constexpr uint32_t RETRY_DELAYS_MS[] = {60000, 60000, 120000, 180000, 300000};

bool isYes(const String &line) {
  return line.equalsIgnoreCase("yes") || line.equalsIgnoreCase("y") ||
         line.equalsIgnoreCase("igen") || line.equalsIgnoreCase("i");
}

bool isNo(const String &line) {
  return line.equalsIgnoreCase("no") || line.equalsIgnoreCase("n") ||
         line.equalsIgnoreCase("nem");
}

String maskedPassword(const String &password) {
  String masked;
  masked.reserve(password.length());
  for (size_t i = 0; i < password.length(); ++i) {
    masked += '*';
  }
  return masked;
}
}  // namespace

void WifiManager::begin() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);

  Serial.println();
  Serial.println("Wi-Fi configuration");
  Serial.println("=====================");
  Serial.print("ESP32 Wi-Fi MAC: ");
  Serial.println(WiFi.macAddress());
  Serial.println("Commands: status, configure, forget");

  configured_ = loadConfig();
  if (configured_) {
    startConnection();
  } else {
    Serial.println("No saved Wi-Fi configuration.");
    Serial.println("Type configure to start setup.");
  }
}

void WifiManager::update() {
  processSerial();
  updateConnection();
}

bool WifiManager::isConnected() const {
  return WiFi.status() == WL_CONNECTED;
}

bool WifiManager::isConfigured() const {
  return configured_;
}

bool WifiManager::shouldSuppressSensorOutput() const {
  return wizardStep_ != WizardStep::Inactive || connecting_;
}

const String &WifiManager::hostname() const {
  return config_.hostname;
}

void WifiManager::processSerial() {
  while (Serial.available() > 0) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\r') {
      continue;
    }
    if (value == '\n') {
      String line = serialBuffer_;
      serialBuffer_ = "";
      line.trim();
      handleLine(line);
      continue;
    }
    if (value == '\b' || value == 0x7f) {
      if (!serialBuffer_.isEmpty()) {
        serialBuffer_.remove(serialBuffer_.length() - 1);
      }
      continue;
    }
    if (serialBuffer_.length() < 128) {
      serialBuffer_ += value;
    }
  }
}

void WifiManager::handleLine(String line) {
  if (line.equalsIgnoreCase("configure")) {
    startWizard();
    return;
  }

  if (wizardStep_ == WizardStep::Inactive) {
    if (line.equalsIgnoreCase("status")) {
      Serial.print("MAC: ");
      Serial.println(WiFi.macAddress());
      Serial.print("Wi-Fi status: ");
      Serial.println(isConnected() ? "connected" : "disconnected");
      if (configured_) {
        showSummary();
      }
      if (isConnected()) {
        printConnectionDetails();
      }
    } else if (line.equalsIgnoreCase("forget")) {
      clearConfig();
      startWizard();
    } else if (!line.isEmpty()) {
      Serial.println("Unknown command. Commands: status, configure, forget");
    }
    return;
  }

  if (line.equalsIgnoreCase("cancel")) {
    cancelWizard();
    return;
  }

  switch (wizardStep_) {
    case WizardStep::Hostname:
      line.toLowerCase();
      if (!isValidHostname(line)) {
        Serial.println("Name must contain 1-63 letters, digits, or hyphens; it cannot start or end with a hyphen.");
        break;
      }
      candidate_.hostname = line;
      wizardStep_ = WizardStep::Ssid;
      break;

    case WizardStep::Ssid:
      if (line.isEmpty() || line.length() > 32) {
        Serial.println("SSID must contain 1-32 characters.");
        break;
      }
      candidate_.ssid = line;
      wizardStep_ = WizardStep::Password;
      break;

    case WizardStep::Password:
      if (line.length() < 8 || line.length() > 63) {
        Serial.println("Password must contain 8-63 characters.");
        break;
      }
      candidate_.password = line;
      wizardStep_ = WizardStep::Mode;
      break;

    case WizardStep::Mode:
      if (line == "1") {
        candidate_.mode = NetworkMode::Dhcp;
        wizardStep_ = WizardStep::Confirm;
      } else if (line == "2") {
        candidate_.mode = NetworkMode::DhcpReservation;
        wizardStep_ = WizardStep::ExpectedIp;
      } else if (line == "3") {
        candidate_.mode = NetworkMode::Static;
        wizardStep_ = WizardStep::StaticIp;
      } else {
        Serial.println("Select 1, 2, or 3.");
      }
      break;

    case WizardStep::ExpectedIp:
      if (parseRequiredIp(line, candidate_.expectedIp)) {
        wizardStep_ = WizardStep::ReservationSubnet;
      }
      break;

    case WizardStep::ReservationSubnet:
      if (parseRequiredIp(line, candidate_.subnet)) {
        wizardStep_ = WizardStep::ReservationGateway;
      }
      break;

    case WizardStep::ReservationGateway:
      if (parseRequiredIp(line, candidate_.gateway)) {
        wizardStep_ = WizardStep::ReservationDns;
      }
      break;

    case WizardStep::ReservationDns:
      if (parseOptionalIp(line, candidate_.dns1)) {
        if (!validateNetwork(candidate_)) {
          wizardStep_ = WizardStep::ExpectedIp;
          break;
        }
        wizardStep_ = WizardStep::ConfirmReservation;
        showSummary();
      }
      break;

    case WizardStep::StaticIp:
      if (parseRequiredIp(line, candidate_.expectedIp)) {
        wizardStep_ = WizardStep::StaticSubnet;
      }
      break;

    case WizardStep::StaticSubnet:
      if (parseRequiredIp(line, candidate_.subnet)) {
        wizardStep_ = WizardStep::StaticGateway;
      }
      break;

    case WizardStep::StaticGateway:
      if (parseRequiredIp(line, candidate_.gateway)) {
        wizardStep_ = WizardStep::StaticDns1;
      }
      break;

    case WizardStep::StaticDns1:
      if (parseRequiredIp(line, candidate_.dns1)) {
        wizardStep_ = WizardStep::StaticDns2;
      }
      break;

    case WizardStep::StaticDns2:
      if (parseOptionalIp(line, candidate_.dns2)) {
        if (!validateNetwork(candidate_)) {
          wizardStep_ = WizardStep::StaticIp;
          break;
        }
        wizardStep_ = WizardStep::Confirm;
        showSummary();
      }
      break;

    case WizardStep::ConfirmReservation:
      if (isYes(line)) {
        wizardStep_ = WizardStep::Confirm;
      } else if (isNo(line)) {
        Serial.println("Configure the reservation, then answer yes. Type cancel to stop.");
      } else {
        Serial.println("Answer yes or no.");
      }
      break;

    case WizardStep::Confirm:
      if (isYes(line)) {
        if (!saveConfig(candidate_)) {
          Serial.println("Failed to save Wi-Fi configuration.");
          break;
        }
        config_ = candidate_;
        configured_ = true;
        wizardStep_ = WizardStep::Inactive;
        Serial.println("Configuration saved. Starting connection attempt.");
        startConnection();
      } else if (isNo(line)) {
        startWizard();
        return;
      } else {
        Serial.println("Answer yes or no.");
      }
      break;

    case WizardStep::Inactive:
      break;
  }

  showPrompt();
}

void WifiManager::startWizard() {
  candidate_ = WifiConfig{};
  wizardStep_ = WizardStep::Hostname;
  Serial.println();
  Serial.println("Wi-Fi setup started. Type cancel at any prompt to stop.");
  Serial.print("ESP32 Wi-Fi MAC: ");
  Serial.println(WiFi.macAddress());
  showPrompt();
}

void WifiManager::cancelWizard() {
  wizardStep_ = WizardStep::Inactive;
  Serial.println(configured_ ? "Setup cancelled; saved configuration retained."
                             : "Setup cancelled; device remains unconfigured.");
}

void WifiManager::showPrompt() const {
  switch (wizardStep_) {
    case WizardStep::Hostname:
      Serial.print("Device name/hostname (for example esp32-1): ");
      break;
    case WizardStep::Ssid:
      Serial.print("SSID: ");
      break;
    case WizardStep::Password:
      Serial.print("Wi-Fi password (input is not printed by the device): ");
      break;
    case WizardStep::Mode:
      Serial.println("IP mode: 1=DHCP, 2=DHCP reservation, 3=static");
      Serial.print("Selection: ");
      break;
    case WizardStep::ExpectedIp:
      Serial.print("Desired DHCP-reserved IP: ");
      break;
    case WizardStep::ReservationSubnet:
      Serial.print("DHCP network netmask: ");
      break;
    case WizardStep::ReservationGateway:
      Serial.print("DHCP network gateway: ");
      break;
    case WizardStep::ReservationDns:
      Serial.print("Expected DNS (empty = supplied by DHCP): ");
      break;
    case WizardStep::StaticIp:
      Serial.print("Static IP: ");
      break;
    case WizardStep::StaticSubnet:
      Serial.print("Netmask: ");
      break;
    case WizardStep::StaticGateway:
      Serial.print("Gateway: ");
      break;
    case WizardStep::StaticDns1:
      Serial.print("Primary DNS: ");
      break;
    case WizardStep::StaticDns2:
      Serial.print("Secondary DNS (optional): ");
      break;
    case WizardStep::ConfirmReservation:
      Serial.println("Configure these values on the DHCP server before continuing.");
      Serial.print("Is the DHCP reservation configured? (yes/no): ");
      break;
    case WizardStep::Confirm:
      showSummary();
      Serial.print("Save and connect? (yes/no): ");
      break;
    case WizardStep::Inactive:
      break;
  }
}

void WifiManager::showSummary() const {
  const WifiConfig &shown =
      wizardStep_ == WizardStep::Inactive ? config_ : candidate_;
  Serial.println();
  Serial.println("Configuration summary");
  Serial.print("MAC:      ");
  Serial.println(WiFi.macAddress());
  Serial.print("Name:     ");
  Serial.println(shown.hostname);
  Serial.print("SSID:     ");
  Serial.println(shown.ssid);
  Serial.print("Password: ");
  Serial.println(maskedPassword(shown.password));
  Serial.print("IP mode:  ");
  Serial.println(modeName(shown.mode));
  if (shown.mode != NetworkMode::Dhcp) {
    Serial.print(shown.mode == NetworkMode::Static ? "IP:        " : "Desired IP:");
    Serial.println(shown.expectedIp);
    Serial.print("Netmask:   ");
    Serial.println(shown.subnet);
    Serial.print("Gateway:   ");
    Serial.println(shown.gateway);
    Serial.print("DNS 1:     ");
    Serial.println(shown.dns1);
  }
  if (shown.mode == NetworkMode::Static) {
    Serial.print("DNS 2:     ");
    Serial.println(shown.dns2);
  }
}

bool WifiManager::loadConfig() {
  Preferences preferences;
  if (!preferences.begin(PREFERENCES_NAMESPACE, true)) {
    return false;
  }
  const bool configured = preferences.getBool("configured", false);
  if (configured) {
    config_.hostname = preferences.getString("hostname", "");
    config_.ssid = preferences.getString("ssid", "");
    config_.password = preferences.getString("password", "");
    config_.mode = static_cast<NetworkMode>(preferences.getUChar("mode", 1));
    config_.expectedIp.fromString(preferences.getString("expected_ip", "0.0.0.0"));
    config_.subnet.fromString(preferences.getString("subnet", "0.0.0.0"));
    config_.gateway.fromString(preferences.getString("gateway", "0.0.0.0"));
    config_.dns1.fromString(preferences.getString("dns1", "0.0.0.0"));
    config_.dns2.fromString(preferences.getString("dns2", "0.0.0.0"));
  }
  preferences.end();
  if (configured && config_.hostname.isEmpty()) {
    config_.hostname = "esp32-";
    String suffix = WiFi.macAddress();
    suffix.replace(":", "");
    suffix = suffix.substring(suffix.length() - 6);
    suffix.toLowerCase();
    config_.hostname += suffix;
    Serial.print("No saved hostname; temporary hostname: ");
    Serial.println(config_.hostname);
    Serial.println("Run configure to choose a permanent device name.");
  }
  return configured && !config_.ssid.isEmpty() &&
         static_cast<uint8_t>(config_.mode) >= 1 &&
         static_cast<uint8_t>(config_.mode) <= 3;
}

bool WifiManager::saveConfig(const WifiConfig &config) {
  Preferences preferences;
  if (!preferences.begin(PREFERENCES_NAMESPACE, false)) {
    return false;
  }
  bool ok = true;
  ok &= preferences.putString("hostname", config.hostname) > 0;
  ok &= preferences.putString("ssid", config.ssid) > 0;
  preferences.putString("password", config.password);
  ok &= preferences.putUChar("mode", static_cast<uint8_t>(config.mode)) > 0;
  ok &= preferences.putString("expected_ip", config.expectedIp.toString()) > 0;
  ok &= preferences.putString("subnet", config.subnet.toString()) > 0;
  ok &= preferences.putString("gateway", config.gateway.toString()) > 0;
  ok &= preferences.putString("dns1", config.dns1.toString()) > 0;
  ok &= preferences.putString("dns2", config.dns2.toString()) > 0;
  if (ok) {
    ok = preferences.putBool("configured", true) > 0;
  }
  preferences.end();
  return ok;
}

void WifiManager::clearConfig() {
  Preferences preferences;
  if (preferences.begin(PREFERENCES_NAMESPACE, false)) {
    preferences.clear();
    preferences.end();
  }
  WiFi.disconnect(true, true);
  configured_ = false;
  connecting_ = false;
  wasConnected_ = false;
  config_ = WifiConfig{};
  Serial.println("Saved Wi-Fi configuration erased.");
}

void WifiManager::startConnection() {
  if (!configured_ || connecting_ || isConnected()) {
    return;
  }

  WiFi.disconnect(false, false);
  if (!WiFi.setHostname(config_.hostname.c_str())) {
    Serial.println("Failed to set Wi-Fi hostname.");
  }
  if (config_.mode == NetworkMode::Static) {
    if (!WiFi.config(config_.expectedIp, config_.gateway, config_.subnet,
                     config_.dns1, config_.dns2)) {
      Serial.println("Failed to apply static IP configuration.");
      scheduleRetry();
      return;
    }
  } else {
    WiFi.config(INADDR_NONE, INADDR_NONE, INADDR_NONE);
  }

  Serial.print("Connecting to Wi-Fi SSID '");
  Serial.print(config_.ssid);
  Serial.println("'...");
  WiFi.begin(config_.ssid.c_str(), config_.password.c_str());
  connecting_ = true;
  connectionStartedAt_ = millis();
}

void WifiManager::updateConnection() {
  const bool connected = isConnected();
  if (connected) {
    if (!wasConnected_) {
      Serial.println("Wi-Fi connected.");
      printConnectionDetails();
      if (config_.mode == NetworkMode::DhcpReservation &&
          WiFi.localIP() != config_.expectedIp) {
        Serial.print("WARNING: reserved IP expected ");
        Serial.print(config_.expectedIp);
        Serial.print(", but DHCP assigned ");
        Serial.println(WiFi.localIP());
      }
    }
    connecting_ = false;
    wasConnected_ = true;
    retryIndex_ = 0;
    return;
  }

  if (wasConnected_) {
    Serial.println("Wi-Fi connection lost.");
    wasConnected_ = false;
    connecting_ = false;
    scheduleRetry();
    return;
  }

  const uint32_t now = millis();
  if (connecting_ && now - connectionStartedAt_ >= CONNECTION_TIMEOUT_MS) {
    Serial.println("Wi-Fi connection attempt timed out.");
    WiFi.disconnect(false, false);
    connecting_ = false;
    scheduleRetry();
    return;
  }

  if (configured_ && !connecting_ && static_cast<int32_t>(now - nextRetryAt_) >= 0) {
    startConnection();
  }
}

void WifiManager::scheduleRetry() {
  const size_t delayCount = sizeof(RETRY_DELAYS_MS) / sizeof(RETRY_DELAYS_MS[0]);
  const size_t index = retryIndex_ < delayCount ? retryIndex_ : delayCount - 1;
  const uint32_t delayMs = RETRY_DELAYS_MS[index];
  if (retryIndex_ < delayCount - 1) {
    ++retryIndex_;
  }
  nextRetryAt_ = millis() + delayMs;
  Serial.print("Next Wi-Fi attempt in ");
  Serial.print(delayMs / 60000);
  Serial.println(" minute(s). Type configure to change settings.");
}

void WifiManager::printConnectionDetails() const {
  Serial.print("IP:      ");
  Serial.println(WiFi.localIP());
  Serial.print("Netmask: ");
  Serial.println(WiFi.subnetMask());
  Serial.print("Gateway: ");
  Serial.println(WiFi.gatewayIP());
  Serial.print("DNS 1:   ");
  Serial.println(WiFi.dnsIP(0));
  Serial.print("RSSI:    ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
}

bool WifiManager::parseRequiredIp(const String &text, IPAddress &address) {
  if (!address.fromString(text)) {
    Serial.println("Invalid IPv4 address.");
    return false;
  }
  return true;
}

bool WifiManager::parseOptionalIp(const String &text, IPAddress &address) {
  if (text.isEmpty()) {
    address = IPAddress();
    return true;
  }
  return parseRequiredIp(text, address);
}

bool WifiManager::isValidHostname(const String &hostname) {
  if (hostname.isEmpty() || hostname.length() > 63 || hostname[0] == '-' ||
      hostname[hostname.length() - 1] == '-') {
    return false;
  }
  for (size_t i = 0; i < hostname.length(); ++i) {
    const char value = hostname[i];
    if (!isAlphaNumeric(value) && value != '-') {
      return false;
    }
  }
  return true;
}

bool WifiManager::validateNetwork(const WifiConfig &config) {
  const uint32_t ip = addressValue(config.expectedIp);
  const uint32_t subnet = addressValue(config.subnet);
  const uint32_t gateway = addressValue(config.gateway);
  const uint32_t hostMask = ~subnet;

  if (subnet == 0 || (hostMask & (hostMask + 1)) != 0) {
    Serial.println("Invalid netmask: bits must be contiguous.");
    return false;
  }
  if ((ip & subnet) != (gateway & subnet)) {
    Serial.println("IP and gateway are not in the same subnet.");
    return false;
  }

  const uint32_t hostPart = ip & hostMask;
  if (hostPart == 0 || hostPart == hostMask) {
    Serial.println("IP cannot be the network or broadcast address.");
    return false;
  }
  if (ip == gateway) {
    Serial.println("IP cannot be identical to the gateway.");
    return false;
  }
  return true;
}

uint32_t WifiManager::addressValue(const IPAddress &address) {
  return (static_cast<uint32_t>(address[0]) << 24) |
         (static_cast<uint32_t>(address[1]) << 16) |
         (static_cast<uint32_t>(address[2]) << 8) |
         static_cast<uint32_t>(address[3]);
}

const char *WifiManager::modeName(NetworkMode mode) {
  switch (mode) {
    case NetworkMode::Dhcp:
      return "DHCP";
    case NetworkMode::DhcpReservation:
      return "DHCP reservation";
    case NetworkMode::Static:
      return "static";
  }
  return "unknown";
}
