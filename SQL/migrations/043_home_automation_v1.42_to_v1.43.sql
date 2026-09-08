-- MariaDB migration: home automation schema v1.42 -> v1.43
-- Purpose: electricity invoice consumption, network charges and provider-account history

USE home_automation;

ALTER TABLE energy_invoices
  ADD COLUMN provider_name VARCHAR(120) NULL AFTER invoice_number,
  ADD COLUMN provider_customer_id VARCHAR(64) NULL AFTER provider_name,
  ADD COLUMN contract_account_id VARCHAR(64) NULL AFTER provider_customer_id;

ALTER TABLE energy_invoice_consumption
  DROP CONSTRAINT chk_energy_invoice_consumption_values,
  CHANGE COLUMN provider_start_reading_m3 provider_start_reading DECIMAL(16,3) NULL,
  CHANGE COLUMN provider_end_reading_m3 provider_end_reading DECIMAL(16,3) NULL,
  CHANGE COLUMN billed_consumption_m3 billed_consumption DECIMAL(16,3) NOT NULL,
  ADD COLUMN quantity_unit ENUM('m3','kWh') NOT NULL DEFAULT 'm3' AFTER billed_consumption,
  MODIFY COLUMN correction_factor DECIMAL(10,6) NULL,
  CHANGE COLUMN corrected_consumption_m3 corrected_consumption DECIMAL(16,3) NULL,
  MODIFY COLUMN heating_value_mj_m3 DECIMAL(10,4) NULL,
  MODIFY COLUMN heat_quantity_mj DECIMAL(16,3) NULL,
  CHANGE COLUMN last_settled_reading_value_m3 last_settled_reading_value DECIMAL(16,3) NULL,
  CHANGE COLUMN installment_volume_since_settlement_m3 installment_consumption_since_settlement DECIMAL(16,3) NULL,
  ADD CONSTRAINT chk_energy_invoice_consumption_values CHECK (
    billed_consumption >= 0
    AND (provider_start_reading IS NULL OR provider_start_reading >= 0)
    AND (provider_end_reading IS NULL OR provider_end_reading >= 0)
    AND (last_settled_reading_value IS NULL OR last_settled_reading_value >= 0)
    AND (installment_consumption_since_settlement IS NULL OR installment_consumption_since_settlement >= 0)
    AND (
      (quantity_unit='kWh' AND correction_factor IS NULL AND corrected_consumption IS NULL
        AND heating_value_mj_m3 IS NULL AND heat_quantity_mj IS NULL)
      OR
      (quantity_unit='m3' AND correction_factor > 0 AND corrected_consumption >= 0
        AND heating_value_mj_m3 > 0 AND heat_quantity_mj >= 0)
    )
  );

ALTER TABLE energy_invoice_charge_lines
  MODIFY COLUMN line_category ENUM(
    'discounted_energy','market_energy','base_fee','service','support','other',
    'settled_energy_offset','settled_base_fee_offset','late_interest',
    'network_usage_fee','transmission_fee','distribution_fee','settled_network_fee_offset'
  ) NOT NULL;

ALTER TABLE energy_tariff_periods
  MODIFY COLUMN tariff_tier ENUM(
    'discounted','market','network_combined','transmission','distribution'
  ) NOT NULL;

INSERT INTO energy_tariff_periods
  (meter_id,tariff_tier,valid_from,valid_to,unit_price,price_unit,tax_basis,note)
SELECT id,'discounted','2024-12-17',NULL,5.110000,'HUF_KWH','net','Villanyszámlák alapján'
FROM energy_meters WHERE meter_code='electricity_main'
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price),price_unit=VALUES(price_unit),tax_basis=VALUES(tax_basis);

INSERT INTO energy_tariff_periods
  (meter_id,tariff_tier,valid_from,valid_to,unit_price,price_unit,tax_basis,note)
SELECT id,'market','2024-12-17',NULL,31.800000,'HUF_KWH','net','Villanyszámlák alapján'
FROM energy_meters WHERE meter_code='electricity_main'
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price),price_unit=VALUES(price_unit),tax_basis=VALUES(tax_basis);

INSERT INTO energy_tariff_periods
  (meter_id,tariff_tier,valid_from,valid_to,unit_price,price_unit,tax_basis,note)
SELECT id,'network_combined','2024-12-17','2026-05-31',23.400000,'HUF_KWH','net',
       'Régi számlaképen összevont rendszerhasználati-üzemeltetési díj'
FROM energy_meters WHERE meter_code='electricity_main'
ON DUPLICATE KEY UPDATE valid_to=VALUES(valid_to),unit_price=VALUES(unit_price),price_unit=VALUES(price_unit),tax_basis=VALUES(tax_basis);

INSERT INTO energy_tariff_periods
  (meter_id,tariff_tier,valid_from,valid_to,unit_price,price_unit,tax_basis,note)
SELECT id,'transmission','2026-06-01',NULL,3.390000,'HUF_KWH','net','Új MVM számlakép alapján'
FROM energy_meters WHERE meter_code='electricity_main'
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price),price_unit=VALUES(price_unit),tax_basis=VALUES(tax_basis);

INSERT INTO energy_tariff_periods
  (meter_id,tariff_tier,valid_from,valid_to,unit_price,price_unit,tax_basis,note)
SELECT id,'distribution','2026-06-01',NULL,20.010000,'HUF_KWH','net','Új MVM számlakép alapján'
FROM energy_meters WHERE meter_code='electricity_main'
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price),price_unit=VALUES(price_unit),tax_basis=VALUES(tax_basis);

INSERT INTO energy_invoice_charge_defaults
  (meter_id,template_key,line_category,description,valid_from,quantity,quantity_unit,
   net_unit_price_huf,tax_treatment,vat_rate_percent,gross_unit_price_huf,auto_add,note)
SELECT id,'electricity_main_base_fee','base_fee','Elosztói alapdíj','2024-12-17',1,'hó',
       120.500000,'rate',27.000,NULL,1,'A1 mérő havi alapdíja'
FROM energy_meters WHERE meter_code='electricity_main'
ON DUPLICATE KEY UPDATE description=VALUES(description),net_unit_price_huf=VALUES(net_unit_price_huf),
  tax_treatment=VALUES(tax_treatment),vat_rate_percent=VALUES(vat_rate_percent),auto_add=VALUES(auto_add);

INSERT INTO energy_invoice_charge_defaults
  (meter_id,template_key,line_category,description,valid_from,valid_to,quantity,quantity_unit,
   net_unit_price_huf,tax_treatment,vat_rate_percent,gross_unit_price_huf,auto_add,note)
SELECT id,'electricity_unused_controlled_meter_base_fee','base_fee',
       'Használaton kívüli vezérelt mérő alapdíja','2024-12-17','2026-05-31',1,'hó',
       39.500000,'rate',27.000,NULL,1,'Fogyasztás nélküli vezérelt mérő számlán szereplő díja'
FROM energy_meters WHERE meter_code='electricity_main'
ON DUPLICATE KEY UPDATE valid_to=VALUES(valid_to),description=VALUES(description),
  net_unit_price_huf=VALUES(net_unit_price_huf),tax_treatment=VALUES(tax_treatment),
  vat_rate_percent=VALUES(vat_rate_percent),auto_add=VALUES(auto_add);
