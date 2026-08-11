-- MariaDB migration: home automation schema v1.9 -> v1.10
-- Purpose: deterministic daily analytics, anomaly events and local-AI summaries
USE home_automation;

CREATE TABLE analysis_runs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_date DATE NOT NULL,
  pipeline_version VARCHAR(32) NOT NULL,
  status ENUM('queued','running','success','failed') NOT NULL DEFAULT 'queued',
  started_at DATETIME(3) NULL,
  completed_at DATETIME(3) NULL,
  error_message TEXT NULL,
  run_metadata JSON NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_analysis_run_date_version (analysis_date,pipeline_version),
  KEY idx_analysis_runs_status_date (status,analysis_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE daily_sensor_metrics (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  sensor_id BIGINT UNSIGNED NOT NULL,
  metric_date DATE NOT NULL,
  sample_count INT UNSIGNED NOT NULL,
  minimum_value DECIMAL(10,4) NULL,
  maximum_value DECIMAL(10,4) NULL,
  average_value DECIMAL(10,4) NULL,
  standard_deviation DECIMAL(10,4) NULL,
  heating_rate_per_hour DECIMAL(10,4) NULL,
  cooling_rate_per_hour DECIMAL(10,4) NULL,
  target_mean_absolute_error DECIMAL(10,4) NULL,
  switching_count INT UNSIGNED NULL,
  metric_details JSON NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_daily_sensor_metric (analysis_run_id,sensor_id),
  KEY idx_daily_sensor_metrics_date (metric_date,sensor_id),
  CONSTRAINT fk_daily_metrics_run FOREIGN KEY (analysis_run_id)
    REFERENCES analysis_runs(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_daily_metrics_sensor FOREIGN KEY (sensor_id)
    REFERENCES sensors(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE anomaly_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  sensor_id BIGINT UNSIGNED NULL,
  device_id BIGINT UNSIGNED NULL,
  room_id BIGINT UNSIGNED NULL,
  anomaly_type VARCHAR(64) NOT NULL,
  severity ENUM('info','warning','critical') NOT NULL DEFAULT 'warning',
  window_started_at DATETIME(3) NOT NULL,
  window_ended_at DATETIME(3) NOT NULL,
  localized_z_score DECIMAL(10,4) NULL,
  evidence JSON NOT NULL,
  status ENUM('open','acknowledged','resolved') NOT NULL DEFAULT 'open',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_anomalies_status_time (status,window_started_at),
  KEY idx_anomalies_sensor_time (sensor_id,window_started_at),
  CONSTRAINT fk_anomalies_run FOREIGN KEY (analysis_run_id)
    REFERENCES analysis_runs(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_anomalies_sensor FOREIGN KEY (sensor_id)
    REFERENCES sensors(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_anomalies_device FOREIGN KEY (device_id)
    REFERENCES devices(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_anomalies_room FOREIGN KEY (room_id)
    REFERENCES rooms(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE daily_ai_summaries (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  summary_date DATE NOT NULL,
  provider VARCHAR(32) NOT NULL DEFAULT 'ollama',
  model VARCHAR(100) NOT NULL,
  prompt_version VARCHAR(32) NOT NULL,
  validated_facts JSON NOT NULL,
  summary_text TEXT NOT NULL,
  validation_status ENUM('pending','valid','rejected','fallback') NOT NULL,
  generation_ms INT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_daily_ai_summary_run (analysis_run_id),
  KEY idx_daily_ai_summaries_date (summary_date),
  CONSTRAINT fk_ai_summaries_run FOREIGN KEY (analysis_run_id)
    REFERENCES analysis_runs(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
