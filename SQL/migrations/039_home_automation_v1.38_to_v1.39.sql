-- MariaDB migration: home automation schema v1.38 -> v1.39
-- Purpose: support gross-only late-interest invoice lines

USE home_automation;

ALTER TABLE energy_invoice_charge_lines
  MODIFY COLUMN line_category ENUM(
    'discounted_energy','market_energy','base_fee','service','support','other',
    'settled_energy_offset','settled_base_fee_offset','late_interest'
  ) NOT NULL;
