-- MariaDB migration: home automation schema v1.52 -> v1.53
-- Purpose: retain 72-hour Open-Meteo forecasts and their collection audit

USE home_automation;

CREATE TABLE outdoor_weather_forecast_runs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_id BIGINT UNSIGNED NOT NULL,
  fetched_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  forecast_from DATETIME(3) NOT NULL,
  forecast_until DATETIME(3) NOT NULL,
  point_count SMALLINT UNSIGNED NOT NULL,
  raw_payload JSON NULL,
  PRIMARY KEY (id),
  KEY idx_weather_forecast_run_source_time (source_id,fetched_at),
  CONSTRAINT fk_weather_forecast_run_source FOREIGN KEY (source_id)
    REFERENCES outdoor_temperature_sources(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE outdoor_weather_forecast_points (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id BIGINT UNSIGNED NOT NULL,
  valid_at DATETIME(3) NOT NULL,
  lead_hours DECIMAL(7,3) NOT NULL,
  temperature_c DECIMAL(7,3) NOT NULL,
  apparent_temperature_c DECIMAL(7,3) NULL,
  cloud_cover_percent DECIMAL(6,2) NULL,
  shortwave_radiation_wm2 DECIMAL(9,3) NULL,
  wind_speed_10m_kmh DECIMAL(8,3) NULL,
  precipitation_mm DECIMAL(9,3) NULL,
  weather_code SMALLINT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_weather_forecast_run_valid (run_id,valid_at),
  KEY idx_weather_forecast_valid_time (valid_at),
  CONSTRAINT fk_weather_forecast_point_run FOREIGN KEY (run_id)
    REFERENCES outdoor_weather_forecast_runs(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE outdoor_weather_forecast_poll_attempts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_id BIGINT UNSIGNED NOT NULL,
  attempted_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  completed_at DATETIME(3) NULL,
  success TINYINT(1) NOT NULL,
  error_code VARCHAR(64) NULL,
  error_message TEXT NULL,
  duration_ms INT UNSIGNED NULL,
  run_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  KEY idx_weather_forecast_attempt_source_time (source_id,attempted_at),
  CONSTRAINT fk_weather_forecast_attempt_source FOREIGN KEY (source_id)
    REFERENCES outdoor_temperature_sources(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_weather_forecast_attempt_run FOREIGN KEY (run_id)
    REFERENCES outdoor_weather_forecast_runs(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

