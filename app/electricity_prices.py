from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


@dataclass(frozen=True)
class DynamicElectricityPrice:
    hupx_eur_mwh: Decimal
    market_net_huf_kwh: Decimal
    merchant_fee_net_huf_kwh: Decimal
    dynamic_net_huf_kwh: Decimal
    dynamic_gross_huf_kwh: Decimal


def calculate_dynamic_electricity_price(
    hupx_eur_mwh: Decimal,
    eur_huf: Decimal,
    merchant_fee_net_huf_kwh: Decimal,
    vat_rate_percent: Decimal,
) -> DynamicElectricityPrice:
    if eur_huf <= 0:
        raise ValueError("Az EUR/HUF árfolyamnak pozitívnak kell lennie.")
    if merchant_fee_net_huf_kwh < 0:
        raise ValueError("A kereskedői díj nem lehet negatív.")
    if vat_rate_percent < 0:
        raise ValueError("Az ÁFA-kulcs nem lehet negatív.")
    market_net = (hupx_eur_mwh * eur_huf / Decimal("1000")).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    dynamic_net = market_net + merchant_fee_net_huf_kwh
    dynamic_gross = (
        dynamic_net * (Decimal("1") + vat_rate_percent / Decimal("100"))
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    return DynamicElectricityPrice(
        hupx_eur_mwh=hupx_eur_mwh,
        market_net_huf_kwh=market_net,
        merchant_fee_net_huf_kwh=merchant_fee_net_huf_kwh,
        dynamic_net_huf_kwh=dynamic_net,
        dynamic_gross_huf_kwh=dynamic_gross,
    )
