-- MariaDB migration: home automation schema v1.11 -> v1.12
-- Purpose: room ventilation events with attributed outdoor temperature
USE home_automation;

INSERT INTO outdoor_temperature_sources
  (source_code,display_name,source_type,is_active,priority,max_age_minutes,configuration)
VALUES
  ('idokep_manual','Időkép – kézi leolvasás','manual',0,5,180,NULL),
  ('weather_com_manual','weather.com – kézi leolvasás','manual',0,6,180,NULL);

CREATE TABLE ventilation_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  room_id BIGINT UNSIGNED NOT NULL,
  started_at DATETIME(3) NOT NULL,
  ended_at DATETIME(3) NULL,
  outdoor_temperature_c DECIMAL(7,3) NULL,
  outdoor_source_id BIGINT UNSIGNED NULL,
  note VARCHAR(500) NULL,
  created_by BIGINT UNSIGNED NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_ventilation_room_time (room_id,started_at),
  KEY idx_ventilation_open (ended_at,started_at),
  CONSTRAINT chk_ventilation_interval CHECK (ended_at IS NULL OR ended_at > started_at),
  CONSTRAINT fk_ventilation_room FOREIGN KEY (room_id)
    REFERENCES rooms(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_ventilation_outdoor_source FOREIGN KEY (outdoor_source_id)
    REFERENCES outdoor_temperature_sources(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_ventilation_user FOREIGN KEY (created_by)
    REFERENCES app_users(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
