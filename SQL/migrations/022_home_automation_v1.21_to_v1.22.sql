-- MariaDB migration: home automation schema v1.21 -> v1.22
-- Purpose: auditable, read-only evidence packages and local LLM experiments
USE home_automation;

CREATE TABLE ai_analysis_experiments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  window_started_at DATETIME(3) NOT NULL,
  window_ended_at DATETIME(3) NOT NULL,
  prompt_version VARCHAR(32) NOT NULL,
  provider VARCHAR(32) NOT NULL DEFAULT 'ollama',
  model VARCHAR(100) NOT NULL,
  facts_json JSON NOT NULL,
  operator_observation TEXT NULL,
  prompt_text LONGTEXT NOT NULL,
  raw_response LONGTEXT NULL,
  parsed_response JSON NULL,
  validation_status ENUM('not_run','structurally_valid','rejected','failed') NOT NULL,
  generation_ms INT UNSIGNED NULL,
  error_message TEXT NULL,
  created_by BIGINT UNSIGNED NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id), KEY idx_ai_experiments_window (window_started_at,window_ended_at),
  CONSTRAINT fk_ai_experiments_user FOREIGN KEY (created_by) REFERENCES app_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
