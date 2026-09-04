-- MariaDB migration: home automation schema v1.36 -> v1.37
-- Purpose: store invoice-level rounding separately from charge lines

USE home_automation;

ALTER TABLE energy_invoices
  ADD COLUMN rounding_amount_huf DECIMAL(14,2) NOT NULL DEFAULT 0.00
  AFTER gross_amount_huf;
