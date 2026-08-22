-- MariaDB migration: home automation schema v1.26 -> v1.27
-- Purpose: explicit strict comparison for climate sensor transitions
USE home_automation;

ALTER TABLE climate_program_steps
  ADD COLUMN threshold_operator ENUM('at_least','greater_than')
    NULL AFTER threshold_delta_c;

UPDATE climate_program_steps
SET threshold_operator='at_least'
WHERE transition_type='sensor_below';

ALTER TABLE climate_program_steps
  DROP CONSTRAINT chk_climate_program_delta;

ALTER TABLE climate_program_steps
  ADD CONSTRAINT chk_climate_program_delta CHECK (
    (transition_type='duration' AND sensor_id IS NULL
      AND threshold_delta_c IS NULL AND threshold_operator IS NULL)
    OR
    (transition_type='sensor_below' AND sensor_id IS NOT NULL
      AND threshold_delta_c IN (0.5,1.0,1.5)
      AND threshold_operator IS NOT NULL)
  );
