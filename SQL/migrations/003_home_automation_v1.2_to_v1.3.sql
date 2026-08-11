-- MariaDB migration: home automation schema v1.2 -> v1.3
-- Purpose: manually managed boiler state and service scheduling

USE home_automation;

ALTER TABLE devices
  ADD COLUMN managed_manually TINYINT(1) NOT NULL DEFAULT 0 AFTER model,
  ADD COLUMN manual_power_state TINYINT(1) NULL AFTER managed_manually,
  ADD COLUMN last_service_date DATE NULL AFTER manual_power_state,
  ADD COLUMN next_service_due DATE NULL AFTER last_service_date,
  ADD KEY idx_devices_next_service_due (next_service_due);

INSERT INTO devices (
  room_id, source_system, source_device_id, source_puid, hostname, expected_ip,
  mac_address, name, device_type, model, managed_manually, manual_power_state,
  is_active
) VALUES (
  NULL, 'manual', 'bosch-7000i', NULL, NULL, NULL,
  NULL, 'Bosch 7000i', 'boiler', 'Bosch Condens 7000i W', 1, 0,
  1
)
ON DUPLICATE KEY UPDATE
  name = VALUES(name), device_type = VALUES(device_type), model = VALUES(model),
  managed_manually = 1, is_active = 1;
