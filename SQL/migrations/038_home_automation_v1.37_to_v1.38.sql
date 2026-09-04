-- MariaDB migration: home automation schema v1.37 -> v1.38
-- Purpose: settlement-invoice offsets and the list of reconciled installments

USE home_automation;

ALTER TABLE energy_invoice_charge_lines
  MODIFY COLUMN line_category ENUM(
    'discounted_energy','market_energy','base_fee','service','support','other',
    'settled_energy_offset','settled_base_fee_offset'
  ) NOT NULL;

CREATE TABLE energy_invoice_settled_installments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  settlement_invoice_id BIGINT UNSIGNED NOT NULL,
  settled_invoice_id BIGINT UNSIGNED NULL,
  provider_invoice_number VARCHAR(64) NOT NULL,
  gross_amount_huf DECIMAL(14,2) NOT NULL,
  sort_order SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  note VARCHAR(500) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_settlement_installment_number
    (settlement_invoice_id,provider_invoice_number),
  KEY idx_energy_settlement_installment_link (settled_invoice_id),
  CONSTRAINT chk_energy_settlement_installment_amount CHECK (gross_amount_huf >= 0),
  CONSTRAINT fk_energy_settlement_installment_parent FOREIGN KEY (settlement_invoice_id)
    REFERENCES energy_invoices(id) ON DELETE CASCADE,
  CONSTRAINT fk_energy_settlement_installment_invoice FOREIGN KEY (settled_invoice_id)
    REFERENCES energy_invoices(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
