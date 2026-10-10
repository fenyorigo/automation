-- MariaDB migration: home automation schema v1.53 -> v1.54
-- Purpose: retain ENTSO-E Hungarian day-ahead electricity prices and collection audit

USE home_automation;

CREATE TABLE electricity_day_ahead_price_runs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_code VARCHAR(32) NOT NULL DEFAULT 'entsoe',
  fetched_at DATETIME(3) NOT NULL,
  delivery_date DATE NOT NULL,
  document_mrid VARCHAR(128) NULL,
  revision_number INT NULL,
  period_start DATETIME(3) NOT NULL,
  period_end DATETIME(3) NOT NULL,
  currency VARCHAR(8) NOT NULL,
  price_unit VARCHAR(32) NOT NULL,
  point_count SMALLINT UNSIGNED NOT NULL,
  payload_sha256 CHAR(64) NOT NULL,
  raw_payload MEDIUMTEXT NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_day_ahead_source_payload (source_code,payload_sha256),
  KEY idx_day_ahead_delivery_fetch (delivery_date,fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE electricity_day_ahead_price_points (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id BIGINT UNSIGNED NOT NULL,
  position SMALLINT UNSIGNED NOT NULL,
  interval_start DATETIME(3) NOT NULL,
  interval_end DATETIME(3) NOT NULL,
  resolution_minutes SMALLINT UNSIGNED NOT NULL,
  price_eur_mwh DECIMAL(12,4) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_day_ahead_run_interval (run_id,interval_start),
  KEY idx_day_ahead_interval_start (interval_start),
  CONSTRAINT fk_day_ahead_point_run FOREIGN KEY (run_id)
    REFERENCES electricity_day_ahead_price_runs(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE electricity_day_ahead_price_poll_attempts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  attempted_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  completed_at DATETIME(3) NULL,
  delivery_date DATE NOT NULL,
  success TINYINT(1) NOT NULL,
  http_status SMALLINT UNSIGNED NULL,
  error_code VARCHAR(64) NULL,
  error_message TEXT NULL,
  duration_ms INT UNSIGNED NULL,
  run_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  KEY idx_day_ahead_attempt_delivery_time (delivery_date,attempted_at),
  CONSTRAINT fk_day_ahead_attempt_run FOREIGN KEY (run_id)
    REFERENCES electricity_day_ahead_price_runs(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
