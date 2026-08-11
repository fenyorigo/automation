-- MariaDB migration: home automation schema v1.5 -> v1.6
-- Purpose: reusable daily profiles, weekly/date assignments and resolved plans
USE home_automation;

CREATE TABLE schedule_profiles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  profile_key VARCHAR(20) NOT NULL,
  name VARCHAR(50) NOT NULL,
  version INT UNSIGNED NOT NULL DEFAULT 1,
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id), UNIQUE KEY uq_schedule_profile (device_id,profile_key),
  CONSTRAINT fk_schedule_profile_device FOREIGN KEY (device_id) REFERENCES devices(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE schedule_windows (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  profile_id BIGINT UNSIGNED NOT NULL,
  slot_no TINYINT UNSIGNED NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  requested_settings JSON NOT NULL,
  PRIMARY KEY (id), UNIQUE KEY uq_schedule_window_slot (profile_id,slot_no),
  KEY idx_schedule_window_time (profile_id,start_time),
  CONSTRAINT fk_schedule_window_profile FOREIGN KEY (profile_id) REFERENCES schedule_profiles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE device_weekly_profile_assignments (
  device_id BIGINT UNSIGNED NOT NULL,
  weekday TINYINT UNSIGNED NOT NULL,
  profile_id BIGINT UNSIGNED NOT NULL,
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (device_id,weekday),
  CONSTRAINT fk_weekly_device FOREIGN KEY (device_id) REFERENCES devices(id),
  CONSTRAINT fk_weekly_profile FOREIGN KEY (profile_id) REFERENCES schedule_profiles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE device_date_profile_assignments (
  device_id BIGINT UNSIGNED NOT NULL,
  assignment_date DATE NOT NULL,
  profile_id BIGINT UNSIGNED NOT NULL,
  note VARCHAR(255) NULL,
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (device_id,assignment_date),
  CONSTRAINT fk_date_device FOREIGN KEY (device_id) REFERENCES devices(id),
  CONSTRAINT fk_date_profile FOREIGN KEY (profile_id) REFERENCES schedule_profiles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE resolved_daily_plans (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  plan_date DATE NOT NULL,
  version INT UNSIGNED NOT NULL,
  profile_id BIGINT UNSIGNED NOT NULL,
  profile_version INT UNSIGNED NOT NULL,
  assignment_source VARCHAR(30) NOT NULL,
  plan_snapshot JSON NOT NULL,
  generated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id), UNIQUE KEY uq_resolved_plan_version (device_id,plan_date,version),
  KEY idx_resolved_plan_latest (device_id,plan_date,generated_at),
  CONSTRAINT fk_resolved_device FOREIGN KEY (device_id) REFERENCES devices(id),
  CONSTRAINT fk_resolved_profile FOREIGN KEY (profile_id) REFERENCES schedule_profiles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO schedule_profiles (device_id,profile_key,name)
SELECT id,'workday1','Munkanap 1' FROM devices WHERE source_system IN ('connectlife','computherm');
INSERT INTO schedule_profiles (device_id,profile_key,name)
SELECT id,'workday2','Munkanap 2' FROM devices WHERE source_system IN ('connectlife','computherm');
INSERT INTO schedule_profiles (device_id,profile_key,name)
SELECT id,'workday3','Munkanap 3' FROM devices WHERE source_system IN ('connectlife','computherm');
INSERT INTO schedule_profiles (device_id,profile_key,name)
SELECT id,'holiday','Ünnepnap' FROM devices WHERE source_system IN ('connectlife','computherm');

INSERT INTO device_weekly_profile_assignments (device_id,weekday,profile_id)
SELECT d.id,w.weekday,p.id FROM devices d
CROSS JOIN (SELECT 0 weekday UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6) w
JOIN schedule_profiles p ON p.device_id=d.id AND p.profile_key=IF(w.weekday IN (5,6),'holiday','workday1')
WHERE d.source_system IN ('connectlife','computherm');
