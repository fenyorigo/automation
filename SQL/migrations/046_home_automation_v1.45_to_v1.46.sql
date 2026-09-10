-- MariaDB migration: home automation schema v1.45 -> v1.46
-- Purpose: auditable manual switching of Tasmota and Zigbee router plugs
USE home_automation;

CREATE TABLE device_power_control_attempts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  source_system VARCHAR(50) NOT NULL,
  requested_power TINYINT(1) NOT NULL,
  requested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  requested_by BIGINT UNSIGNED NOT NULL,
  status ENUM('pending','verified','unverified','failed') NOT NULL DEFAULT 'pending',
  preflight_power TINYINT(1) NULL,
  verified_power TINYINT(1) NULL,
  completed_at DATETIME(3) NULL,
  error_code VARCHAR(100) NULL,
  error_message VARCHAR(1000) NULL,
  PRIMARY KEY (id),
  KEY idx_power_control_device_time (device_id,requested_at),
  CONSTRAINT fk_power_control_device FOREIGN KEY (device_id) REFERENCES devices(id),
  CONSTRAINT fk_power_control_user FOREIGN KEY (requested_by) REFERENCES app_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

UPDATE devices d
LEFT JOIN zigbee2mqtt_devices zd ON zd.device_id=d.id
SET d.capability_mode='controllable',d.control_enabled=1
WHERE d.is_active=1
  AND ((d.source_system='tasmota'
        AND d.source_device_id IN ('nous-auxit','nous-mainit','nous-kazan'))
       OR (d.source_system='zigbee2mqtt'
           AND d.device_type='power_meter'
           AND LOWER(COALESCE(zd.zigbee_type,''))='router'
           AND d.source_device_id IN
             ('0xa4c138115778ffff','0xa4c138115783ffff')));
