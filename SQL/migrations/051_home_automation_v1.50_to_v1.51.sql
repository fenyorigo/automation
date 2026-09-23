-- MariaDB migration: home automation schema v1.50 -> v1.51
-- Purpose: generic network-infrastructure monitoring metadata

USE home_automation;

INSERT INTO device_types (code,name) VALUES ('network_node','Hálózati infrastruktúra')
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT INTO manufacturers (code,name) VALUES ('tp_link','TP-Link')
ON DUPLICATE KEY UPDATE name=VALUES(name);
