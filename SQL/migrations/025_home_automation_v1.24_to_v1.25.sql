-- MariaDB migration: home automation schema v1.24 -> v1.25
-- Purpose: searchable, auditable deterministic reports
USE home_automation;

CREATE TABLE deterministic_reports (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  window_started_at DATETIME(3) NOT NULL,
  window_ended_at DATETIME(3) NOT NULL,
  generator_version VARCHAR(32) NOT NULL,
  severity ENUM('info','warning','critical') NOT NULL DEFAULT 'info',
  title VARCHAR(255) NOT NULL,
  report_text LONGTEXT NOT NULL,
  findings_json JSON NOT NULL,
  facts_json JSON NOT NULL,
  operator_observation TEXT NULL,
  created_by BIGINT UNSIGNED NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_deterministic_reports_created (created_at),
  KEY idx_deterministic_reports_severity_created (severity,created_at),
  KEY idx_deterministic_reports_window (window_started_at,window_ended_at),
  CONSTRAINT fk_deterministic_reports_user
    FOREIGN KEY (created_by) REFERENCES app_users(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
