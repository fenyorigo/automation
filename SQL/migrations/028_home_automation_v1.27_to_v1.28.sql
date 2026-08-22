-- MariaDB migration: home automation schema v1.27 -> v1.28
-- Purpose: allow transition as soon as the selected sensor reaches target
USE home_automation;

ALTER TABLE climate_program_steps
  DROP CONSTRAINT chk_climate_program_delta;

ALTER TABLE climate_program_steps
  ADD CONSTRAINT chk_climate_program_delta CHECK (
    (transition_type='duration' AND sensor_id IS NULL
      AND threshold_delta_c IS NULL AND threshold_operator IS NULL)
    OR
    (transition_type='sensor_below' AND sensor_id IS NOT NULL
      AND threshold_delta_c IN (0.0,0.5,1.0,1.5)
      AND threshold_operator IS NOT NULL)
  );
