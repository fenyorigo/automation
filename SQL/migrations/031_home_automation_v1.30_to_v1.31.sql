-- MariaDB migration: home automation schema v1.30 -> v1.31
-- Purpose: turn the registered thinkpad260x into a locally polled Linux system

USE home_automation;

UPDATE devices
SET source_system='linux_system',
    source_device_id='thinkpad260x',
    hostname='think260x',
    device_type='server',
    access_mode='network',
    capability_mode='read_only',
    polling_enabled=1,
    control_enabled=0,
    poll_interval_seconds=600,
    is_active=1
WHERE id=29705
  AND source_system='manual'
  AND source_device_id='thinkpad260x';
