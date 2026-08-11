-- MariaDB migration: home automation schema v1.8 -> v1.9
-- Purpose: Bosch boiler room and initial device assignment
USE home_automation;

INSERT INTO rooms (zone_id,name)
SELECT z.id,'Kazánház' FROM zones z
WHERE z.name='Földszint'
  AND NOT EXISTS (SELECT 1 FROM rooms r WHERE r.name='Kazánház');

UPDATE device_room_history h
JOIN devices d ON d.id=h.device_id
SET h.valid_to=CURRENT_TIMESTAMP(3)
WHERE d.source_system='manual' AND d.source_device_id='bosch-7000i'
  AND h.valid_to IS NULL;

UPDATE devices
SET room_id=(SELECT id FROM rooms WHERE name='Kazánház')
WHERE source_system='manual' AND source_device_id='bosch-7000i';

INSERT INTO device_room_history (device_id,room_id,change_reason)
SELECT d.id,r.id,'Kazánház kezdeti hozzárendelése'
FROM devices d JOIN rooms r ON r.name='Kazánház'
WHERE d.source_system='manual' AND d.source_device_id='bosch-7000i';
