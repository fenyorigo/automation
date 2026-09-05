-- MariaDB migration: home automation schema v1.41 -> v1.42
-- Purpose: registry metadata for network-monitored printers

USE home_automation;

INSERT INTO device_types (code,name) VALUES ('printer','Nyomtató')
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO manufacturers (code,name) VALUES ('xerox','Xerox')
ON DUPLICATE KEY UPDATE name=VALUES(name);
