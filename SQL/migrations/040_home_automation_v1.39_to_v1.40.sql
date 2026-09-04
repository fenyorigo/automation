-- MariaDB migration: home automation schema v1.39 -> v1.40
-- Purpose: effective-dated invoice charge defaults and tax treatment

USE home_automation;

CREATE TABLE energy_invoice_charge_defaults (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_id BIGINT UNSIGNED NOT NULL,
  template_key VARCHAR(64) NOT NULL,
  line_category ENUM('base_fee','service') NOT NULL,
  description VARCHAR(255) NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  quantity DECIMAL(16,3) NOT NULL DEFAULT 1,
  quantity_unit VARCHAR(32) NOT NULL DEFAULT 'hó',
  net_unit_price_huf DECIMAL(14,6) NULL,
  tax_treatment ENUM('rate','exempt') NOT NULL DEFAULT 'rate',
  vat_rate_percent DECIMAL(7,3) NULL,
  gross_unit_price_huf DECIMAL(14,2) NULL,
  auto_add TINYINT(1) NOT NULL DEFAULT 1,
  note VARCHAR(500) NULL,
  recorded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_charge_default_start (meter_id,template_key,valid_from),
  KEY idx_energy_charge_default_validity (meter_id,valid_from,valid_to),
  CONSTRAINT chk_energy_charge_default_dates CHECK (valid_to IS NULL OR valid_to >= valid_from),
  CONSTRAINT chk_energy_charge_default_values CHECK (
    quantity > 0 AND (net_unit_price_huf IS NOT NULL OR gross_unit_price_huf IS NOT NULL)
    AND (tax_treatment='exempt' OR vat_rate_percent IS NOT NULL)
  ),
  CONSTRAINT fk_energy_charge_default_meter FOREIGN KEY (meter_id) REFERENCES energy_meters(id),
  CONSTRAINT fk_energy_charge_default_user FOREIGN KEY (recorded_by) REFERENCES app_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE energy_invoice_charge_lines
  ADD COLUMN tax_treatment ENUM('rate','exempt') NOT NULL DEFAULT 'rate' AFTER vat_rate_percent,
  ADD COLUMN charge_default_id BIGINT UNSIGNED NULL AFTER tax_treatment,
  ADD KEY idx_energy_invoice_charge_default (charge_default_id),
  ADD CONSTRAINT fk_energy_invoice_charge_default FOREIGN KEY (charge_default_id)
    REFERENCES energy_invoice_charge_defaults(id) ON DELETE SET NULL;

UPDATE energy_invoice_charge_lines
SET tax_treatment='exempt',vat_rate_percent=NULL
WHERE line_category='service';

INSERT INTO energy_invoice_charge_defaults
  (meter_id,template_key,line_category,description,valid_from,quantity,quantity_unit,
   net_unit_price_huf,tax_treatment,vat_rate_percent,gross_unit_price_huf,auto_add,note)
SELECT id,'gas_base_fee','base_fee','Háztartási alapdíj','2025-11-06',1,'hó',
       766.000000,'rate',27.000,NULL,1,'MVM számlák alapján'
FROM energy_meters WHERE meter_code='gas_main';

INSERT INTO energy_invoice_charge_defaults
  (meter_id,template_key,line_category,description,valid_from,quantity,quantity_unit,
   net_unit_price_huf,tax_treatment,vat_rate_percent,gross_unit_price_huf,auto_add,note)
SELECT id,'otthonsos_komfort','service','OtthonSOS Komfort','2025-11-06',1,'hó',
       790.000000,'exempt',NULL,790.00,1,'Áfamentes havi szolgáltatás'
FROM energy_meters WHERE meter_code='gas_main';

INSERT INTO energy_invoice_charge_defaults
  (meter_id,template_key,line_category,description,valid_from,quantity,quantity_unit,
   net_unit_price_huf,tax_treatment,vat_rate_percent,gross_unit_price_huf,auto_add,note)
SELECT id,'otthonsos_garancia_medium','service','OtthonSOS Garancia Médium','2025-11-06',1,'hó',
       990.000000,'exempt',NULL,990.00,1,'Áfamentes havi szolgáltatás'
FROM energy_meters WHERE meter_code='gas_main';
