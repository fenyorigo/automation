-- MariaDB migration: home automation schema v1.19 -> v1.20
-- Purpose: editable zone, room, device and capability registry with per-device polling
USE home_automation;

ALTER TABLE zones
  ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1,
  ADD COLUMN created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  ADD COLUMN updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3);

INSERT INTO zones (name) VALUES ('Zónán kívüli')
  ON DUPLICATE KEY UPDATE name=VALUES(name);
UPDATE rooms SET zone_id=(SELECT id FROM zones WHERE name='Zónán kívüli')
  WHERE name='Kültéri' AND zone_id IS NULL;

ALTER TABLE rooms ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 AFTER name;

CREATE TABLE device_types (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code VARCHAR(50) NOT NULL,
  name VARCHAR(100) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id), UNIQUE KEY uq_device_types_code (code), UNIQUE KEY uq_device_types_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE manufacturers (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code VARCHAR(50) NOT NULL,
  name VARCHAR(100) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id), UNIQUE KEY uq_manufacturers_code (code), UNIQUE KEY uq_manufacturers_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO device_types (code,name) VALUES
 ('climate','Klíma'),('thermostat','Termosztát'),('temperature_sensor','Hőmérő'),
 ('power_meter','Teljesítménymérő'),('boiler','Kazán'),('other','Egyéb');
INSERT INTO manufacturers (code,name) VALUES
 ('hisense','Hisense'),('esp32','ESP32'),('computherm','Computherm'),
 ('bosch','Bosch'),('shelly','Shelly'),('other','Egyéb');

ALTER TABLE devices
  ADD COLUMN zone_id BIGINT UNSIGNED NULL AFTER room_id,
  ADD COLUMN device_type_id BIGINT UNSIGNED NULL AFTER device_type,
  ADD COLUMN manufacturer_id BIGINT UNSIGNED NULL AFTER device_type_id,
  ADD COLUMN access_mode ENUM('manual_visual','network') NOT NULL DEFAULT 'network' AFTER manufacturer_id,
  ADD COLUMN capability_mode ENUM('read_only','controllable','manual_read','manual_control') NOT NULL DEFAULT 'read_only' AFTER access_mode,
  ADD COLUMN ip_assignment ENUM('dhcp','dhcp_reservation','static','not_applicable') NOT NULL DEFAULT 'dhcp_reservation' AFTER expected_ip,
  ADD COLUMN polling_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER ip_assignment,
  ADD COLUMN control_enabled TINYINT(1) NOT NULL DEFAULT 0 AFTER polling_enabled,
  ADD COLUMN poll_interval_seconds INT UNSIGNED NOT NULL DEFAULT 600 AFTER control_enabled,
  ADD COLUMN min_target_temperature_c DECIMAL(5,2) NULL AFTER poll_interval_seconds,
  ADD COLUMN max_target_temperature_c DECIMAL(5,2) NULL AFTER min_target_temperature_c,
  ADD KEY idx_devices_zone (zone_id), ADD KEY idx_devices_type_id (device_type_id),
  ADD KEY idx_devices_manufacturer (manufacturer_id),
  ADD CONSTRAINT fk_devices_zone FOREIGN KEY (zone_id) REFERENCES zones(id),
  ADD CONSTRAINT fk_devices_type_id FOREIGN KEY (device_type_id) REFERENCES device_types(id),
  ADD CONSTRAINT fk_devices_manufacturer FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id),
  ADD CONSTRAINT chk_devices_poll_interval CHECK (poll_interval_seconds BETWEEN 60 AND 86400),
  ADD CONSTRAINT chk_devices_target_range CHECK (
    min_target_temperature_c IS NULL OR max_target_temperature_c IS NULL OR
    min_target_temperature_c <= max_target_temperature_c
  );

UPDATE devices SET device_type_id=(SELECT id FROM device_types WHERE code=CASE
  WHEN source_system='connectlife' THEN 'climate'
  WHEN source_system='computherm' THEN 'thermostat'
  WHEN source_system='esp32' THEN 'temperature_sensor'
  WHEN device_type='boiler' THEN 'boiler' ELSE 'other' END);
UPDATE devices SET manufacturer_id=(SELECT id FROM manufacturers WHERE code=CASE
  WHEN source_system='connectlife' THEN 'hisense'
  WHEN source_system='computherm' THEN 'computherm'
  WHEN source_system='esp32' THEN 'esp32'
  WHEN source_device_id='bosch-7000i' THEN 'bosch' ELSE 'other' END);
UPDATE devices SET zone_id=(SELECT zone_id FROM rooms WHERE rooms.id=devices.room_id);
UPDATE devices SET access_mode='manual_visual',polling_enabled=0,ip_assignment='not_applicable'
  WHERE source_system='manual';
UPDATE devices SET capability_mode='controllable',control_enabled=1,
  min_target_temperature_c=16,max_target_temperature_c=30 WHERE source_system='connectlife';
UPDATE devices SET capability_mode='controllable',control_enabled=0,
  min_target_temperature_c=5,max_target_temperature_c=22 WHERE source_system='computherm';
UPDATE devices SET capability_mode='manual_control',control_enabled=0 WHERE device_type='boiler';

CREATE TABLE device_supported_modes (
  device_id BIGINT UNSIGNED NOT NULL, mode_code VARCHAR(32) NOT NULL, display_name VARCHAR(100) NOT NULL,
  PRIMARY KEY (device_id,mode_code),
  CONSTRAINT fk_supported_modes_device FOREIGN KEY (device_id) REFERENCES devices(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE device_supported_fan_speeds (
  device_id BIGINT UNSIGNED NOT NULL, speed_code VARCHAR(32) NOT NULL, display_name VARCHAR(100) NOT NULL,
  PRIMARY KEY (device_id,speed_code),
  CONSTRAINT fk_supported_fans_device FOREIGN KEY (device_id) REFERENCES devices(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT INTO device_supported_modes SELECT id,'cool','Hűtés' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_modes SELECT id,'heat','Fűtés' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_modes SELECT id,'dry','Szárítás' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_modes SELECT id,'fan','Ventilátor' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_modes SELECT id,'auto','Automata' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_modes SELECT id,'heat','Fűtés' FROM devices WHERE source_system='computherm';
INSERT INTO device_supported_fan_speeds SELECT id,'auto','Automata' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_fan_speeds SELECT id,'low','Alacsony' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_fan_speeds SELECT id,'medium_low','Közepesen alacsony' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_fan_speeds SELECT id,'medium','Közepes' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_fan_speeds SELECT id,'medium_high','Középmagas' FROM devices WHERE source_system='connectlife';
INSERT INTO device_supported_fan_speeds SELECT id,'high','Magas' FROM devices WHERE source_system='connectlife';

CREATE TABLE registry_audit_log (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  entity_type ENUM('zone','room','device_type','manufacturer','device') NOT NULL,
  entity_id BIGINT UNSIGNED NOT NULL, action VARCHAR(32) NOT NULL,
  changes_json JSON NULL, changed_by BIGINT UNSIGNED NOT NULL,
  changed_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id), KEY idx_registry_audit_entity (entity_type,entity_id,changed_at),
  CONSTRAINT fk_registry_audit_user FOREIGN KEY (changed_by) REFERENCES app_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
