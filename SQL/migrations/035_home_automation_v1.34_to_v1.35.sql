-- MariaDB migration: home automation schema v1.34 -> v1.35
-- Purpose: gas discounted-entitlement years independent from billing cycles

USE home_automation;

CREATE TABLE energy_entitlement_periods (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_id BIGINT UNSIGNED NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NOT NULL,
  discounted_limit_mj DECIMAL(16,3) NOT NULL,
  reference_volume_m3 DECIMAL(16,3) NULL,
  allocation_method ENUM('time_and_consumption_prorated') NOT NULL,
  source_url VARCHAR(500) NULL,
  note VARCHAR(500) NULL,
  recorded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_entitlement_start (meter_id,valid_from),
  CONSTRAINT chk_energy_entitlement_dates CHECK (valid_to >= valid_from),
  CONSTRAINT chk_energy_entitlement_values CHECK (
    discounted_limit_mj > 0 AND (reference_volume_m3 IS NULL OR reference_volume_m3 > 0)
  ),
  CONSTRAINT fk_energy_entitlement_meter FOREIGN KEY (meter_id) REFERENCES energy_meters(id),
  CONSTRAINT fk_energy_entitlement_user FOREIGN KEY (recorded_by)
    REFERENCES app_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO energy_entitlement_periods
  (meter_id,valid_from,valid_to,discounted_limit_mj,reference_volume_m3,
   allocation_method,source_url,note)
SELECT id,'2025-08-01','2026-07-31',63645.000,1729.000,
       'time_and_consumption_prorated',
       'https://www.mvmnext.hu/lakossagirezsi/legfontosabb-informaciok-gaz',
       'A számlázási ciklustól független kedvezményes jogosultsági év'
FROM energy_meters WHERE meter_code='gas_main';

INSERT INTO energy_entitlement_periods
  (meter_id,valid_from,valid_to,discounted_limit_mj,reference_volume_m3,
   allocation_method,source_url,note)
SELECT id,'2026-08-01','2027-07-31',63645.000,1729.000,
       'time_and_consumption_prorated',
       'https://www.mvmnext.hu/lakossagirezsi/legfontosabb-informaciok-gaz',
       'A számlázási ciklustól független kedvezményes jogosultsági év'
FROM energy_meters WHERE meter_code='gas_main';
