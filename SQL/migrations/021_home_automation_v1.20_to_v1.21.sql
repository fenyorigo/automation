-- MariaDB migration: home automation schema v1.20 -> v1.21
-- Purpose: integration role and structured optional device features
USE home_automation;

ALTER TABLE devices ADD COLUMN integration_role ENUM('direct','gateway') NOT NULL DEFAULT 'direct'
  AFTER capability_mode;

CREATE TABLE device_supported_features (
  device_id BIGINT UNSIGNED NOT NULL,
  feature_code VARCHAR(32) NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  PRIMARY KEY (device_id,feature_code),
  CONSTRAINT fk_supported_features_device FOREIGN KEY (device_id) REFERENCES devices(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO device_supported_features SELECT id,'swing','Hinta' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_features SELECT id,'super','Gyors üzem' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_features SELECT id,'quiet','Csendes' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_features SELECT id,'sleep','Alvás' FROM devices WHERE source_system='connectlife';
