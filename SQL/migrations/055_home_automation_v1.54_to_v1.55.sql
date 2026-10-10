-- MariaDB migration: home automation schema v1.54 -> v1.55
-- Purpose: retain official MNB EUR/HUF rates and effective-dated D tariff parameters

USE home_automation;

CREATE TABLE currency_exchange_rate_observations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_code VARCHAR(32) NOT NULL DEFAULT 'mnb',
  fetched_at DATETIME(3) NOT NULL,
  rate_date DATE NOT NULL,
  currency CHAR(3) NOT NULL,
  unit SMALLINT UNSIGNED NOT NULL,
  rate_huf DECIMAL(12,6) NOT NULL,
  payload_sha256 CHAR(64) NOT NULL,
  raw_payload MEDIUMTEXT NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_exchange_rate_payload (source_code,rate_date,currency,payload_sha256),
  KEY idx_exchange_rate_lookup (currency,rate_date,fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE currency_exchange_rate_poll_attempts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  attempted_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  completed_at DATETIME(3) NULL,
  success TINYINT(1) NOT NULL,
  http_status SMALLINT UNSIGNED NULL,
  rate_date DATE NULL,
  error_code VARCHAR(64) NULL,
  error_message TEXT NULL,
  duration_ms INT UNSIGNED NULL,
  observation_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  KEY idx_exchange_rate_attempt_time (attempted_at),
  CONSTRAINT fk_exchange_rate_attempt_observation FOREIGN KEY (observation_id)
    REFERENCES currency_exchange_rate_observations(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE electricity_dynamic_tariff_parameters (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  tariff_code VARCHAR(16) NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  merchant_fee_net_huf_kwh DECIMAL(10,4) NOT NULL,
  vat_rate_percent DECIMAL(5,2) NOT NULL DEFAULT 27.00,
  source_url VARCHAR(500) NULL,
  note VARCHAR(1000) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_dynamic_tariff_start (tariff_code,valid_from),
  KEY idx_dynamic_tariff_validity (tariff_code,valid_from,valid_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO electricity_dynamic_tariff_parameters
  (tariff_code,valid_from,valid_to,merchant_fee_net_huf_kwh,vat_rate_percent,source_url,note)
VALUES
  ('D','2026-09-10',NULL,13.7000,27.00,
   'https://www.mvmnext.hu/aram/servlet/download?type=file&id=16704',
   'MVM Next hirdetmény, közzétéve és hatályos 2026. szeptember 10-től.');
