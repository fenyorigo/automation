-- MariaDB migration: home automation schema v1.46 -> v1.47
-- Purpose: limit UI power switching to the dedicated Bosch boiler supply plug
USE home_automation;

UPDATE devices
SET capability_mode='read_only',control_enabled=0
WHERE (source_system='tasmota'
       AND source_device_id IN ('nous-auxit','nous-mainit'))
   OR (source_system='zigbee2mqtt'
       AND source_device_id IN
         ('0xa4c138115778ffff','0xa4c138115783ffff'));

UPDATE devices
SET capability_mode='controllable',control_enabled=1
WHERE source_system='tasmota' AND source_device_id='nous-kazan' AND is_active=1;
