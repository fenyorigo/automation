-- MariaDB migration: home automation schema v1.35 -> v1.36
-- Purpose: add the gas conversion values documented by the 2025-07-07--2025-08-06 invoice

USE home_automation;

INSERT INTO gas_conversion_periods
  (meter_id,valid_from,valid_to,correction_factor,heating_value_mj_m3,data_source,note)
SELECT id,'2025-07-07','2025-08-06',1.000000,35.3700,'invoice',
       'NKM Gáz 2025.07.07-2025.08.06 számla alapján'
FROM energy_meters
WHERE meter_code='gas_main'
  AND NOT EXISTS (
    SELECT 1 FROM gas_conversion_periods p
    WHERE p.meter_id=energy_meters.id AND p.valid_from='2025-07-07'
  );
