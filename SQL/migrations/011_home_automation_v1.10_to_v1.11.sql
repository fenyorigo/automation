-- MariaDB migration: home automation schema v1.10 -> v1.11
-- Purpose: configurable outdoor-temperature sources and observations
USE home_automation;

CREATE TABLE outdoor_temperature_sources (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_code VARCHAR(64) NOT NULL,
  display_name VARCHAR(120) NOT NULL,
  source_type ENUM('esp32','wunderground_pws','open_meteo','manual') NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 0,
  priority SMALLINT UNSIGNED NOT NULL,
  max_age_minutes SMALLINT UNSIGNED NOT NULL DEFAULT 30,
  configuration JSON NULL,
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_outdoor_source_code (source_code),
  KEY idx_outdoor_source_priority (priority),
  CONSTRAINT chk_outdoor_source_priority CHECK (priority BETWEEN 1 AND 999),
  CONSTRAINT chk_outdoor_source_max_age CHECK (max_age_minutes BETWEEN 1 AND 1440)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE outdoor_temperature_observations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_id BIGINT UNSIGNED NOT NULL,
  observed_at DATETIME(3) NOT NULL,
  fetched_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  temperature_c DECIMAL(7,3) NOT NULL,
  quality VARCHAR(32) NOT NULL DEFAULT 'good',
  source_event_id VARCHAR(255) NOT NULL,
  raw_payload JSON NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_outdoor_observation_event (source_id,source_event_id),
  KEY idx_outdoor_observation_source_time (source_id,observed_at),
  CONSTRAINT fk_outdoor_observation_source FOREIGN KEY (source_id)
    REFERENCES outdoor_temperature_sources(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE outdoor_temperature_poll_attempts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_id BIGINT UNSIGNED NOT NULL,
  attempted_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  completed_at DATETIME(3) NULL,
  success TINYINT(1) NOT NULL,
  error_code VARCHAR(64) NULL,
  error_message TEXT NULL,
  duration_ms INT UNSIGNED NULL,
  PRIMARY KEY (id),
  KEY idx_outdoor_attempt_source_time (source_id,attempted_at),
  CONSTRAINT fk_outdoor_attempt_source FOREIGN KEY (source_id)
    REFERENCES outdoor_temperature_sources(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO outdoor_temperature_sources
  (source_code,display_name,source_type,is_active,priority,max_age_minutes,configuration)
VALUES
  ('esp32_ext','Saját kültéri ESP32','esp32',0,1,30,JSON_OBJECT('device_id','esp32-ext')),
  ('wunderground_pws','Weather Underground PWS','wunderground_pws',0,2,30,JSON_OBJECT('station_id','CONFIGURE_ME')),
  ('open_meteo','Open-Meteo','open_meteo',0,3,30,JSON_OBJECT('latitude',0.0,'longitude',0.0)),
  ('manual','Kézi külső hőmérséklet','manual',0,4,180,NULL);
