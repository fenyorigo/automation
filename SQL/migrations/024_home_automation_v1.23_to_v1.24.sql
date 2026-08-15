-- MariaDB migration: home automation schema v1.23 -> v1.24
-- Purpose: per-user measurement-history presets
USE home_automation;

CREATE TABLE history_presets (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  name VARCHAR(80) NOT NULL,
  device_ids JSON NOT NULL,
  range_key VARCHAR(8) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_history_presets_user_name (user_id, name),
  KEY idx_history_presets_user (user_id, id),
  CONSTRAINT fk_history_presets_user
    FOREIGN KEY (user_id) REFERENCES app_users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT chk_history_presets_range
    CHECK (range_key IN ('1h','2h','6h','12h','24h','7d','30d'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
