-- MariaDB migration: home automation schema v1.56 -> v1.57
-- Purpose: durable non-blocking manual climate command queue and progress feedback
USE home_automation;

ALTER TABLE climate_control_attempts
  ADD COLUMN execution_phase VARCHAR(32) NULL AFTER status,
  ADD COLUMN started_at DATETIME(3) NULL AFTER requested_at,
  ADD COLUMN phase_updated_at DATETIME(3) NULL AFTER started_at,
  ADD KEY idx_climate_control_queue (status,execution_phase,requested_at);
