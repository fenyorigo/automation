-- MariaDB migration: home automation schema v1.33 -> v1.34
-- Purpose: versioned energy tariffs, gas conversion, billing cycles and invoices

USE home_automation;

CREATE TABLE energy_billing_cycles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_id BIGINT UNSIGNED NOT NULL,
  cycle_start DATE NOT NULL,
  cycle_end DATE NULL,
  baseline_reading_id BIGINT UNSIGNED NULL,
  settlement_reading_id BIGINT UNSIGNED NULL,
  status ENUM('open','settled') NOT NULL DEFAULT 'open',
  note VARCHAR(500) NULL,
  recorded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_billing_cycle_start (meter_id,cycle_start),
  CONSTRAINT chk_energy_billing_cycle_dates CHECK (cycle_end IS NULL OR cycle_end >= cycle_start),
  CONSTRAINT fk_energy_cycle_meter FOREIGN KEY (meter_id) REFERENCES energy_meters(id),
  CONSTRAINT fk_energy_cycle_baseline FOREIGN KEY (baseline_reading_id) REFERENCES energy_meter_readings(id),
  CONSTRAINT fk_energy_cycle_settlement FOREIGN KEY (settlement_reading_id) REFERENCES energy_meter_readings(id),
  CONSTRAINT fk_energy_cycle_user FOREIGN KEY (recorded_by) REFERENCES app_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE gas_conversion_periods (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_id BIGINT UNSIGNED NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  correction_factor DECIMAL(10,6) NOT NULL,
  heating_value_mj_m3 DECIMAL(10,4) NOT NULL,
  data_source ENUM('invoice','manual','provider') NOT NULL DEFAULT 'invoice',
  note VARCHAR(500) NULL,
  recorded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_gas_conversion_start (meter_id,valid_from),
  CONSTRAINT chk_gas_conversion_dates CHECK (valid_to IS NULL OR valid_to >= valid_from),
  CONSTRAINT chk_gas_conversion_values CHECK (correction_factor > 0 AND heating_value_mj_m3 > 0),
  CONSTRAINT fk_gas_conversion_meter FOREIGN KEY (meter_id) REFERENCES energy_meters(id),
  CONSTRAINT fk_gas_conversion_user FOREIGN KEY (recorded_by) REFERENCES app_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE energy_tariff_periods (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_id BIGINT UNSIGNED NOT NULL,
  tariff_tier ENUM('discounted','market') NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  unit_price DECIMAL(14,6) NOT NULL,
  price_unit ENUM('HUF_MJ','HUF_KWH') NOT NULL,
  tax_basis ENUM('net','gross') NOT NULL DEFAULT 'net',
  note VARCHAR(500) NULL,
  recorded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_tariff_start (meter_id,tariff_tier,valid_from),
  CONSTRAINT chk_energy_tariff_dates CHECK (valid_to IS NULL OR valid_to >= valid_from),
  CONSTRAINT chk_energy_tariff_price CHECK (unit_price >= 0),
  CONSTRAINT fk_energy_tariff_meter FOREIGN KEY (meter_id) REFERENCES energy_meters(id),
  CONSTRAINT fk_energy_tariff_user FOREIGN KEY (recorded_by) REFERENCES app_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE energy_allocation_rules (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  billing_cycle_id BIGINT UNSIGNED NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  discounted_share DECIMAL(12,9) NOT NULL,
  market_share DECIMAL(12,9) NOT NULL,
  rule_type ENUM('provider_installment_estimate','annual_entitlement') NOT NULL,
  note VARCHAR(500) NULL,
  recorded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_allocation_start (billing_cycle_id,rule_type,valid_from),
  CONSTRAINT chk_energy_allocation_dates CHECK (valid_to IS NULL OR valid_to >= valid_from),
  CONSTRAINT chk_energy_allocation_shares CHECK (
    discounted_share BETWEEN 0 AND 1 AND market_share BETWEEN 0 AND 1
    AND ABS(discounted_share + market_share - 1) < 0.000000002
  ),
  CONSTRAINT fk_energy_allocation_cycle FOREIGN KEY (billing_cycle_id) REFERENCES energy_billing_cycles(id),
  CONSTRAINT fk_energy_allocation_user FOREIGN KEY (recorded_by) REFERENCES app_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE energy_fixed_charge_periods (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_id BIGINT UNSIGNED NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  amount_huf DECIMAL(14,2) NOT NULL,
  period_type ENUM('monthly','invoice') NOT NULL DEFAULT 'monthly',
  description VARCHAR(255) NOT NULL,
  is_estimated TINYINT(1) NOT NULL DEFAULT 1,
  note VARCHAR(500) NULL,
  recorded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_fixed_charge_start (meter_id,description,valid_from),
  CONSTRAINT chk_energy_fixed_charge_dates CHECK (valid_to IS NULL OR valid_to >= valid_from),
  CONSTRAINT chk_energy_fixed_charge_amount CHECK (amount_huf >= 0),
  CONSTRAINT fk_energy_fixed_charge_meter FOREIGN KEY (meter_id) REFERENCES energy_meters(id),
  CONSTRAINT fk_energy_fixed_charge_user FOREIGN KEY (recorded_by) REFERENCES app_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE energy_invoices (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_id BIGINT UNSIGNED NOT NULL,
  billing_cycle_id BIGINT UNSIGNED NULL,
  invoice_number VARCHAR(64) NOT NULL,
  invoice_type ENUM('installment','settlement','correction') NOT NULL,
  sequence_no SMALLINT UNSIGNED NULL,
  period_start_date DATE NOT NULL,
  period_end_date DATE NOT NULL,
  issued_at DATE NULL,
  performance_at DATE NULL,
  due_at DATE NULL,
  net_amount_huf DECIMAL(14,2) NULL,
  vat_amount_huf DECIMAL(14,2) NULL,
  gross_amount_huf DECIMAL(14,2) NULL,
  payable_amount_huf DECIMAL(14,2) NOT NULL,
  account_balance_huf DECIMAL(14,2) NULL,
  counterfactual_market_amount_huf DECIMAL(14,2) NULL,
  note VARCHAR(500) NULL,
  recorded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_invoice_number (invoice_number),
  KEY idx_energy_invoice_period (meter_id,period_start_date,period_end_date),
  CONSTRAINT chk_energy_invoice_dates CHECK (period_end_date >= period_start_date),
  CONSTRAINT fk_energy_invoice_meter FOREIGN KEY (meter_id) REFERENCES energy_meters(id),
  CONSTRAINT fk_energy_invoice_cycle FOREIGN KEY (billing_cycle_id) REFERENCES energy_billing_cycles(id),
  CONSTRAINT fk_energy_invoice_user FOREIGN KEY (recorded_by) REFERENCES app_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE energy_invoice_consumption (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  invoice_id BIGINT UNSIGNED NOT NULL,
  period_start_date DATE NOT NULL,
  period_end_date DATE NOT NULL,
  provider_start_reading_m3 DECIMAL(16,3) NULL,
  provider_end_reading_m3 DECIMAL(16,3) NULL,
  reading_method ENUM('estimated','actual','dictated','inspection') NULL,
  billed_consumption_m3 DECIMAL(16,3) NOT NULL,
  correction_factor DECIMAL(10,6) NOT NULL,
  corrected_consumption_m3 DECIMAL(16,3) NOT NULL,
  heating_value_mj_m3 DECIMAL(10,4) NOT NULL,
  heat_quantity_mj DECIMAL(16,3) NOT NULL,
  last_settled_reading_date DATE NULL,
  last_settled_reading_value_m3 DECIMAL(16,3) NULL,
  installment_volume_since_settlement_m3 DECIMAL(16,3) NULL,
  note VARCHAR(500) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_energy_invoice_consumption_period (invoice_id,period_start_date),
  CONSTRAINT chk_energy_invoice_consumption_dates CHECK (period_end_date >= period_start_date),
  CONSTRAINT chk_energy_invoice_consumption_values CHECK (
    billed_consumption_m3 >= 0 AND correction_factor > 0
    AND corrected_consumption_m3 >= 0 AND heating_value_mj_m3 > 0 AND heat_quantity_mj >= 0
  ),
  CONSTRAINT fk_energy_invoice_consumption_invoice FOREIGN KEY (invoice_id)
    REFERENCES energy_invoices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE energy_invoice_charge_lines (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  invoice_id BIGINT UNSIGNED NOT NULL,
  invoice_consumption_id BIGINT UNSIGNED NULL,
  line_category ENUM('discounted_energy','market_energy','base_fee','service','support','other') NOT NULL,
  description VARCHAR(255) NOT NULL,
  period_start_date DATE NULL,
  period_end_date DATE NULL,
  quantity DECIMAL(16,3) NULL,
  quantity_unit VARCHAR(32) NULL,
  net_unit_price_huf DECIMAL(14,6) NULL,
  net_amount_huf DECIMAL(14,2) NULL,
  vat_rate_percent DECIMAL(7,3) NULL,
  gross_amount_huf DECIMAL(14,2) NOT NULL,
  sort_order SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  note VARCHAR(500) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_energy_invoice_charge_invoice (invoice_id,sort_order,id),
  CONSTRAINT chk_energy_invoice_charge_dates CHECK (
    period_end_date IS NULL OR period_start_date IS NULL OR period_end_date >= period_start_date
  ),
  CONSTRAINT fk_energy_invoice_charge_invoice FOREIGN KEY (invoice_id)
    REFERENCES energy_invoices(id) ON DELETE CASCADE,
  CONSTRAINT fk_energy_invoice_charge_consumption FOREIGN KEY (invoice_consumption_id)
    REFERENCES energy_invoice_consumption(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO energy_billing_cycles
  (meter_id,cycle_start,baseline_reading_id,status,note)
SELECT m.id,'2025-11-07',r.id,'open','Éves MVM-leolvasási ciklus'
FROM energy_meters m
LEFT JOIN energy_meter_readings r
  ON r.meter_id=m.id AND r.recorded_at='2025-11-05 08:00:00.000'
WHERE m.meter_code='gas_main';

INSERT INTO gas_conversion_periods
  (meter_id,valid_from,valid_to,correction_factor,heating_value_mj_m3,data_source,note)
SELECT id,'2025-11-07','2025-12-06',1.000000,35.3700,'invoice','MVM részszámla alapján'
FROM energy_meters WHERE meter_code='gas_main';

INSERT INTO gas_conversion_periods
  (meter_id,valid_from,valid_to,correction_factor,heating_value_mj_m3,data_source,note)
SELECT id,'2025-12-07',NULL,1.000000,35.4000,'invoice','MVM részszámla alapján'
FROM energy_meters WHERE meter_code='gas_main';

INSERT INTO energy_tariff_periods
  (meter_id,tariff_tier,valid_from,unit_price,price_unit,tax_basis,note)
SELECT id,'discounted','2025-11-07',2.256000,'HUF_MJ','net','MVM részszámla alapján'
FROM energy_meters WHERE meter_code='gas_main';

INSERT INTO energy_tariff_periods
  (meter_id,tariff_tier,valid_from,unit_price,price_unit,tax_basis,note)
SELECT id,'market','2025-11-07',17.324000,'HUF_MJ','net','MVM részszámla alapján'
FROM energy_meters WHERE meter_code='gas_main';

INSERT INTO energy_allocation_rules
  (billing_cycle_id,valid_from,discounted_share,market_share,rule_type,note)
SELECT c.id,'2025-11-07',0.777772822,0.222227178,'provider_installment_estimate',
       'Havi részszámlák alapján becsült megosztás'
FROM energy_billing_cycles c JOIN energy_meters m ON m.id=c.meter_id
WHERE m.meter_code='gas_main' AND c.cycle_start='2025-11-07';

INSERT INTO energy_fixed_charge_periods
  (meter_id,valid_from,amount_huf,period_type,description,is_estimated,note)
SELECT id,'2025-11-07',2800.00,'monthly','Becsült fix és egyéb havi díjak',1,
       'Tervezési közelítés, a tényleges számlatételek külön kerülnek rögzítésre'
FROM energy_meters WHERE meter_code='gas_main';
