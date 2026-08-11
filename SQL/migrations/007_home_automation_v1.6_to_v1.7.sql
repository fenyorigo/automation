-- MariaDB migration: home automation schema v1.6 -> v1.7
-- Purpose: zones, rooms, initial assignments and movable-device location history
USE home_automation;

CREATE TABLE zones (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  PRIMARY KEY (id), UNIQUE KEY uq_zones_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE rooms ADD COLUMN zone_id BIGINT UNSIGNED NULL AFTER id,
  ADD KEY idx_rooms_zone (zone_id),
  ADD CONSTRAINT fk_rooms_zone FOREIGN KEY (zone_id) REFERENCES zones(id);

CREATE TABLE device_room_history (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  room_id BIGINT UNSIGNED NOT NULL,
  valid_from DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  valid_to DATETIME(3) NULL,
  change_reason VARCHAR(255) NULL,
  PRIMARY KEY (id), KEY idx_device_room_history (device_id,valid_from),
  CONSTRAINT fk_room_history_device FOREIGN KEY (device_id) REFERENCES devices(id),
  CONSTRAINT fk_room_history_room FOREIGN KEY (room_id) REFERENCES rooms(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO zones (name) VALUES ('Emelet'),('Földszint');
INSERT INTO rooms (name) VALUES
  ('Dolgozó'),('Háló'),('Kristófék'),('Rita'),('Veronika'),('Kis nappali'),
  ('Nappali'),('Vendégszoba'),('Ebédlő-konyha'),('Kültéri');
UPDATE rooms SET zone_id=(SELECT id FROM zones WHERE name='Emelet')
WHERE name IN ('Dolgozó','Háló','Kristófék','Rita','Veronika','Kis nappali');
UPDATE rooms SET zone_id=(SELECT id FROM zones WHERE name='Földszint')
WHERE name IN ('Nappali','Vendégszoba','Ebédlő-konyha');

UPDATE devices SET room_id=(SELECT id FROM rooms WHERE name='Dolgozó') WHERE source_device_id IN ('hisense-office','iot-computherm-emelet');
UPDATE devices SET room_id=(SELECT id FROM rooms WHERE name='Háló') WHERE source_device_id='hisense-dorm';
UPDATE devices SET room_id=(SELECT id FROM rooms WHERE name='Kristófék') WHERE source_device_id='hisense-chris';
UPDATE devices SET room_id=(SELECT id FROM rooms WHERE name='Rita') WHERE source_device_id='hisense-rita';
UPDATE devices SET room_id=(SELECT id FROM rooms WHERE name='Veronika') WHERE source_device_id='hisense-veronica';
UPDATE devices SET room_id=(SELECT id FROM rooms WHERE name='Vendégszoba') WHERE source_device_id='iot-computherm-foldszint';
UPDATE devices SET room_id=(SELECT id FROM rooms WHERE name='Kültéri') WHERE source_device_id='esp32-ext';

UPDATE sensors s JOIN devices d ON d.id=s.device_id SET s.room_id=d.room_id WHERE d.room_id IS NOT NULL;
INSERT INTO device_room_history (device_id,room_id,change_reason)
SELECT id,room_id,'Kezdeti hozzárendelés' FROM devices WHERE room_id IS NOT NULL;
