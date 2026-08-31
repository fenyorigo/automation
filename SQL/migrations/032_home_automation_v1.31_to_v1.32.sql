-- MariaDB migration: home automation schema v1.31 -> v1.32
-- Purpose: Zigbee2MQTT automatic device discovery and last-known property cache

USE home_automation;

INSERT INTO device_types (code,name) VALUES
  ('contact_sensor','Nyitásérzékelő'),
  ('zigbee_router','Zigbee router')
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO manufacturers (code,name) VALUES ('sonoff','SONOFF')
ON DUPLICATE KEY UPDATE name=VALUES(name);

CREATE TABLE zigbee2mqtt_devices (
  device_id BIGINT UNSIGNED NOT NULL,
  ieee_address VARCHAR(32) NOT NULL,
  friendly_name VARCHAR(255) NOT NULL,
  model_id VARCHAR(100) NULL,
  manufacturer VARCHAR(100) NULL,
  power_source VARCHAR(100) NULL,
  zigbee_type VARCHAR(32) NULL,
  supported TINYINT(1) NOT NULL DEFAULT 0,
  interview_completed TINYINT(1) NOT NULL DEFAULT 0,
  availability VARCHAR(20) NULL,
  definition_json JSON NULL,
  first_discovered_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  last_discovered_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  last_message_at DATETIME(3) NULL,
  removed_at DATETIME(3) NULL,
  PRIMARY KEY (device_id),
  UNIQUE KEY uq_zigbee2mqtt_ieee (ieee_address),
  UNIQUE KEY uq_zigbee2mqtt_friendly_name (friendly_name),
  CONSTRAINT fk_zigbee2mqtt_device FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE zigbee2mqtt_property_cache (
  device_id BIGINT UNSIGNED NOT NULL,
  property_name VARCHAR(100) NOT NULL,
  value_json JSON NOT NULL,
  numeric_value DECIMAL(16,4) NULL,
  text_value VARCHAR(255) NULL,
  source_observed_at DATETIME(3) NULL,
  received_at DATETIME(3) NOT NULL,
  mqtt_topic VARCHAR(512) NOT NULL,
  retained TINYINT(1) NOT NULL DEFAULT 0,
  raw_payload JSON NOT NULL,
  PRIMARY KEY (device_id,property_name),
  KEY idx_zigbee2mqtt_cache_received (received_at),
  KEY idx_zigbee2mqtt_cache_source_observed (source_observed_at),
  CONSTRAINT fk_zigbee2mqtt_cache_device FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
