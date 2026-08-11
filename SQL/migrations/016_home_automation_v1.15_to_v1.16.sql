-- MariaDB migration: home automation schema v1.15 -> v1.16
-- Purpose: explicit start and end snapshots for ventilation and climate events
USE home_automation;

ALTER TABLE ventilation_events
  ALGORITHM=INPLACE,
  CHANGE COLUMN outdoor_temperature_c started_outdoor_temperature_c DECIMAL(7,3) NULL,
  CHANGE COLUMN outdoor_source_id started_outdoor_source_id BIGINT UNSIGNED NULL;

ALTER TABLE ventilation_events
  ADD COLUMN ended_outdoor_temperature_c DECIMAL(7,3) NULL AFTER started_outdoor_source_id,
  ADD COLUMN ended_outdoor_source_id BIGINT UNSIGNED NULL AFTER ended_outdoor_temperature_c,
  ADD CONSTRAINT fk_ventilation_ended_outdoor_source FOREIGN KEY (ended_outdoor_source_id)
    REFERENCES outdoor_temperature_sources(id) ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE climate_operation_events
  CHANGE COLUMN target_temperature_c started_target_temperature_c DECIMAL(5,2) NULL,
  ADD COLUMN ended_target_temperature_c DECIMAL(5,2) NULL AFTER started_target_temperature_c;
