-- MariaDB migration: home automation schema v1.7 -> v1.8
-- Purpose: authenticated dashboard users with viewer/editor roles
USE home_automation;

CREATE TABLE app_users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('viewer','editor') NOT NULL DEFAULT 'viewer',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  last_login_at DATETIME(3) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_app_users_username (username),
  KEY idx_app_users_active_role (is_active,role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
