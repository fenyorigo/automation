-- MariaDB migration: home automation schema v1.32 -> v1.33
-- Purpose: accept Zigbee2MQTT outdoor-temperature sources with local-source priority

USE home_automation;

ALTER TABLE outdoor_temperature_sources
  MODIFY COLUMN source_type
    ENUM('esp32','wunderground_pws','open_meteo','manual','zigbee2mqtt') NOT NULL;

UPDATE outdoor_temperature_sources
SET priority = priority + 9
WHERE priority < 10;
