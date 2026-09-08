#!/usr/bin/env python3
"""Import the verified 2024-2026 electricity invoices into home_automation.

The source documents are the NKM/MVM PDF invoices kept by the operator.  The
dataset below intentionally contains invoice values, not values recalculated
from tariffs: invoice-level and line-level rounding must remain reproducible.

The command is a dry run unless --apply is supplied.  It never replaces or
deletes an existing invoice.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from typing import Any

from dashboard import connect_database, recalculate_installment_cumulative_consumption


D = Decimal


def line(
    category: str,
    description: str,
    start: str | None,
    end: str | None,
    quantity: int | None,
    unit: str | None,
    unit_price: str | None,
    net: int | None,
    gross: int,
    *,
    link: int | None = 0,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "category": category,
        "description": description,
        "start": start,
        "end": end,
        "quantity": quantity,
        "unit": unit,
        "unit_price": D(unit_price) if unit_price is not None else None,
        "net": net,
        "gross": gross,
        "vat_rate": None if category in {"support", "late_interest", "other"} and net is None else D("27"),
        "link": link,
        "note": note,
    }


def energy_lines(
    category: str,
    description: str,
    parts: list[tuple[str, str, int, int, int]],
    unit_price: str,
    *,
    link: int | None = 0,
) -> list[dict[str, Any]]:
    return [
        line(category, description, start, end, quantity, "kWh", unit_price, net, gross, link=link)
        for start, end, quantity, net, gross in parts
    ]


def old_installment(
    number: str,
    sequence: int,
    start: str,
    end: str,
    issued: str,
    due: str,
    totals: tuple[int, int, int],
    rounding: int,
    counterfactual: int,
    readings: tuple[int, int, int],
    discounted: list[tuple[str, str, int, int, int]],
    market: list[tuple[str, str, int, int, int]],
    network: tuple[int, int, int],
    cycle_start: str,
    last_settled: tuple[str, int],
) -> dict[str, Any]:
    start_reading, end_reading, consumption = readings
    network_quantity, network_net, network_gross = network
    charges = energy_lines(
        "discounted_energy", "ESZ Lakossági A1 kedvezményes árszabás ára",
        discounted, "5.1100",
    )
    charges += energy_lines(
        "market_energy", "ESZ Lakossági A1 lakossági piaci ár",
        market, "31.8000",
    )
    charges += [
        line(
            "network_usage_fee", "Rendszerhasználati-üzemeltetési díj",
            start, end, network_quantity, "kWh", "23.4000", network_net, network_gross,
        ),
        line("base_fee", "Elosztói alapdíj", start, end, 1, "db", "120.5000", 121, 154, link=None),
        line(
            "base_fee", "Használaton kívüli vezérelt mérő alapdíja",
            start, end, 1, "db", "39.5000", 40, 51, link=None,
            note="A 9900460152 vezérelt mérő fogyasztása 0 kWh, állása 30 395 kWh.",
        ),
    ]
    return {
        "number": number,
        "type": "installment",
        "sequence": sequence,
        "start": start,
        "end": end,
        "issued": issued,
        "performance": due,
        "due": due,
        "net": totals[0],
        "vat": totals[1],
        "gross": totals[2],
        "rounding": rounding,
        "payable": totals[2],
        "balance": totals[2],
        "counterfactual": counterfactual,
        "provider": "MVM Next / NKM",
        "customer": "1000929648",
        "account": "110001175368",
        "cycle_start": cycle_start,
        "consumption": [{
            "start": start,
            "end": end,
            "start_reading": start_reading,
            "end_reading": end_reading,
            "method": "estimated",
            "quantity": consumption,
            "last_settled_date": last_settled[0],
            "last_settled_value": last_settled[1],
        }],
        "charges": charges,
        "settled_installments": [],
    }


INVOICES: list[dict[str, Any]] = [
    old_installment(
        "11510893719", 1, "2024-12-17", "2025-01-24", "2025-01-27", "2025-02-11",
        (58202, 15715, 73917), -1, 438988, (207017, 208199, 1182),
        [("2024-12-17", "2025-01-24", 270, 1380, 1753)],
        [("2024-12-17", "2025-01-24", 912, 29002, 36833)],
        (1182, 27659, 35127), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "12510489802", 2, "2025-01-25", "2025-02-26", "2025-02-27", "2025-03-14",
        (41934, 11322, 53256), -1, 322053, (208199, 209066, 867),
        [("2025-01-25", "2025-02-26", 228, 1165, 1480)],
        [("2025-01-25", "2025-02-26", 639, 20320, 25806)],
        (867, 20288, 25766), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "12510568222", 3, "2025-02-27", "2025-03-26", "2025-03-27", "2025-04-11",
        (33899, 9153, 43052), -1, 261916, (209066, 209771, 705),
        [("2025-02-27", "2025-03-26", 194, 991, 1259)],
        [("2025-02-27", "2025-03-26", 511, 16250, 20638)],
        (705, 16497, 20951), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "11024989160", 4, "2025-03-27", "2025-04-24", "2025-04-25", "2025-05-12",
        (34291, 9259, 43550), 0, 265628, (209771, 210486, 715),
        [("2025-03-27", "2025-04-24", 200, 1022, 1298)],
        [("2025-03-27", "2025-04-24", 515, 16377, 20799)],
        (715, 16731, 21248), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "12510720236", 5, "2025-04-25", "2025-05-26", "2025-05-27", "2025-06-11",
        (37925, 10240, 48165), 0, 293840, (210486, 211277, 791),
        [("2025-04-25", "2025-05-26", 221, 1129, 1434)],
        [("2025-04-25", "2025-05-26", 570, 18126, 23020)],
        (791, 18509, 23506), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "13510610896", 6, "2025-05-27", "2025-06-25", "2025-06-26", "2025-07-11",
        (37747, 10192, 47939), 0, 290128, (211277, 212058, 781),
        [("2025-05-27", "2025-06-25", 207, 1058, 1344)],
        [("2025-05-27", "2025-06-25", 574, 18253, 23181)],
        (781, 18275, 23209), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "12510878007", 7, "2025-06-26", "2025-07-24", "2025-07-25", "2025-08-11",
        (37934, 10242, 48176), -1, 290128, (212058, 212839, 781),
        [("2025-06-26", "2025-07-24", 200, 1022, 1298)],
        [("2025-06-26", "2025-07-24", 581, 18476, 23465)],
        (781, 18275, 23209), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "11511527713", 8, "2025-07-25", "2025-08-26", "2025-08-27", "2025-09-11",
        (44031, 11889, 55920), 0, 121162, (212839, 213744, 905),
        [("2025-07-25", "2025-07-31", 48, 245, 311), ("2025-08-01", "2025-08-26", 180, 920, 1168)],
        [("2025-07-25", "2025-07-31", 143, 4547, 5775), ("2025-08-01", "2025-08-26", 534, 16981, 21566)],
        (905, 21177, 26895), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "11511608189", 9, "2025-08-27", "2025-09-24", "2025-09-25", "2025-10-10",
        (34788, 9393, 44181), 0, 50960, (213744, 214468, 724),
        [("2025-08-27", "2025-09-24", 200, 1022, 1298)],
        [("2025-08-27", "2025-09-24", 524, 16663, 21162)],
        (724, 16942, 21516), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "12511110795", 10, "2025-09-25", "2025-10-28", "2025-10-29", "2025-11-13",
        (40698, 10989, 51687), 0, 59652, (214468, 215316, 848),
        [("2025-09-25", "2025-10-28", 235, 1201, 1525)],
        [("2025-09-25", "2025-10-28", 613, 19493, 24756)],
        (848, 19843, 25201), "2024-12-17", ("2024-12-16", 207017),
    ),
    old_installment(
        "12511188501", 11, "2025-10-29", "2025-11-26", "2025-11-27", "2025-12-12",
        (36886, 9959, 46845), 0, 53625, (215316, 216078, 762),
        [("2025-10-29", "2025-11-26", 200, 1022, 1298)],
        [("2025-10-29", "2025-11-26", 562, 17872, 22697)],
        (762, 17831, 22645), "2024-12-17", ("2024-12-16", 207017),
    ),
]


def settlement_invoices() -> list[dict[str, Any]]:
    first_charges = (
        energy_lines("discounted_energy", "ESZ Lakossági A1 kedvezményes árszabás ára", [
            ("2024-12-17", "2025-07-31", 1569, 8018, 10183),
            ("2025-08-01", "2025-12-20", 982, 5018, 6373),
        ], "5.1100")
        + energy_lines("market_energy", "ESZ Lakossági A1 lakossági piaci ár", [
            ("2024-12-17", "2025-07-31", 4344, 138139, 175437),
            ("2025-08-01", "2025-12-20", 2717, 86401, 109729),
        ], "31.8000")
        + [
            line("settled_energy_offset", "Részszámlákban elszámolt energiadíj", "2024-12-17", "2025-11-26", None, None, None, -224537, -285164, link=None),
            line("network_usage_fee", "Rendszerhasználati-üzemeltetési díj", "2024-12-17", "2025-12-20", 9612, "kWh", "23.4000", 224921, 285650),
            line("base_fee", "Elosztói alapdíj", "2024-12-17", "2025-12-20", 1, "db", "120.5000", 121, 154, link=None),
            line("settled_network_fee_offset", "Részszámlákban elszámolt rendszerhasználati díjak", "2024-12-17", "2025-11-26", None, None, None, -212027, -269273, link=None),
            line("base_fee", "Használaton kívüli vezérelt mérő alapdíja", "2024-12-17", "2025-12-20", 1, "db", "39.5000", 40, 51, link=None, note="A 9900460152 vezérelt mérő fogyasztása 0 kWh, állása 30 395 kWh."),
        ]
    )
    second_charges = (
        energy_lines("discounted_energy", "ESZ Lakossági A1 kedvezményes árszabás ára", [
            ("2025-12-21", "2026-05-31", 1120, 5723, 7268),
        ], "5.1100")
        + energy_lines("market_energy", "ESZ Lakossági A1 lakossági piaci ár", [
            ("2025-12-21", "2026-05-31", 3126, 99407, 126247),
        ], "31.8000")
        + [
            line("settled_energy_offset", "Részszámlákban elszámolt energiadíj", "2025-12-21", "2026-05-27", None, None, None, -99771, -126711, link=None),
            line("network_usage_fee", "Rendszerhasználati-üzemeltetési díj", "2025-12-21", "2026-05-31", 4246, "kWh", "23.4000", 99356, 126182),
            line("settled_network_fee_offset", "Részszámlákban elszámolt rendszerhasználati díjak", "2025-12-21", "2026-05-27", None, None, None, -94863, -120477, link=None),
        ]
    )
    return [
        {
            "number": "13025320761", "type": "settlement", "sequence": None,
            "start": "2024-12-17", "end": "2025-12-20", "issued": "2026-01-07",
            "performance": "2026-01-22", "due": "2026-01-22",
            "net": 26094, "vat": 7046, "gross": 33140, "rounding": 0,
            "payable": 33140, "balance": 33140, "counterfactual": 2454550,
            "provider": "MVM Next / NKM", "customer": "1000929648", "account": "110001175368",
            "cycle_start": "2024-12-17",
            "consumption": [{"start": "2024-12-17", "end": "2025-12-20", "start_reading": 207017, "end_reading": 216629, "method": "actual", "quantity": 9612, "last_settled_date": None, "last_settled_value": None}],
            "charges": first_charges,
            "settled_installments": [
                ("11510893719", 73917), ("12510489802", 53256), ("12510568222", 43052),
                ("11024989160", 43550), ("12510720236", 48165), ("13510610896", 47939),
                ("12510878007", 48176), ("11511527713", 55920), ("11511608189", 44181),
                ("12511110795", 51687), ("12511188501", 46845),
            ],
        },
        {
            "number": "11512318276", "type": "settlement", "sequence": None,
            "start": "2025-12-21", "end": "2026-05-31", "issued": "2026-06-12",
            "performance": "2026-06-29", "due": "2026-06-29",
            "net": 9852, "vat": 2660, "gross": 12512, "rounding": 3,
            "payable": 12512, "balance": 12512, "counterfactual": 297661,
            "provider": "MVM Next / NKM", "customer": "1000929648", "account": "110001175368",
            "cycle_start": "2025-12-21",
            "consumption": [{"start": "2025-12-21", "end": "2026-05-31", "start_reading": 216629, "end_reading": 220875, "method": "estimated", "quantity": 4246, "last_settled_date": None, "last_settled_value": None}],
            "charges": second_charges,
            "settled_installments": [
                ("13511141824", 63594), ("14510917691", 48711), ("12511475586", 42560),
                ("11512190527", 44714), ("12511628329", 48629),
            ],
        },
    ]


INVOICES += [
    old_installment(
        "13511141824", 1, "2025-12-21", "2026-01-26", "2026-02-02", "2026-02-17",
        (50074, 13520, 63594), -1, 72271, (216629, 217657, 1028),
        [("2025-12-21", "2026-01-26", 256, 1308, 1661)],
        [("2025-12-21", "2026-01-26", 772, 24550, 31179)],
        (1028, 24055, 30550), "2025-12-21", ("2025-12-20", 216629),
    ),
    old_installment(
        "14510917691", 2, "2026-01-27", "2026-02-25", "2026-03-02", "2026-03-17",
        (38355, 10356, 48711), -1, 55728, (217657, 218449, 792),
        [("2026-01-27", "2026-02-25", 207, 1058, 1344)],
        [("2026-01-27", "2026-02-25", 585, 18603, 23626)],
        (792, 18533, 23537), "2025-12-21", ("2025-12-20", 216629),
    ),
    old_installment(
        "12511475586", 3, "2026-02-26", "2026-03-25", "2026-03-26", "2026-04-10",
        (33512, 9048, 42560), -1, 49137, (218449, 219147, 698),
        [("2026-02-26", "2026-03-25", 194, 991, 1259)],
        [("2026-02-26", "2026-03-25", 504, 16027, 20354)],
        (698, 16333, 20743), "2025-12-21", ("2025-12-20", 216629),
    ),
    old_installment(
        "11512190527", 4, "2026-03-26", "2026-04-24", "2026-04-27", "2026-05-12",
        (35208, 9506, 44714), -1, 51731, (219147, 219882, 735),
        [("2026-03-26", "2026-04-24", 207, 1058, 1344)],
        [("2026-03-26", "2026-04-24", 528, 16790, 21323)],
        (735, 17199, 21843), "2025-12-21", ("2025-12-20", 216629),
    ),
    old_installment(
        "12511628329", 5, "2026-04-25", "2026-05-27", "2026-05-28", "2026-06-12",
        (38290, 10339, 48629), -1, 56358, (219882, 220683, 801),
        [("2026-04-25", "2026-05-27", 228, 1165, 1480)],
        [("2026-04-25", "2026-05-27", 573, 18221, 23141)],
        (801, 18743, 23804), "2025-12-21", ("2025-12-20", 216629),
    ),
]


INVOICES += settlement_invoices()


def current_mvm_invoices() -> list[dict[str, Any]]:
    first = {
        "number": "848702722680", "type": "installment", "sequence": 1,
        "start": "2026-06-01", "end": "2026-07-22", "issued": "2026-08-19",
        "performance": "2026-09-03", "due": "2026-09-03",
        "net": 64792, "vat": 17494, "gross": 82286, "rounding": 0,
        "payable": 69774, "balance": 69774, "counterfactual": 94455,
        "provider": "MVM Next", "customer": "26138012", "account": "2607026584",
        "cycle_start": "2026-06-01",
        "consumption": [{"start": "2026-06-01", "end": "2026-07-22", "start_reading": 220875, "end_reading": 222218, "method": "estimated", "quantity": 1343, "last_settled_date": "2026-05-31", "last_settled_value": 220875}],
        "charges": (
            energy_lines("discounted_energy", "ESZ Lakossági A1 kedvezményes árszabás ára", [("2026-06-01", "2026-07-22", 359, 1834, 2329)], "5.1100")
            + energy_lines("market_energy", "ESZ Lakossági A1 lakossági piaci ár", [("2026-06-01", "2026-07-22", 984, 31291, 39740)], "31.8000")
            + [
                line("transmission_fee", "Átviteli forgalmi díj A1", "2026-06-01", "2026-07-22", 1343, "kWh", "3.3900", 4553, 5782),
                line("distribution_fee", "Elosztói forgalmi díj A1", "2026-06-01", "2026-07-22", 1343, "kWh", "20.0100", 26873, 34129),
                line("base_fee", "Elosztói alapdíj A1", "2026-06-01", "2026-07-22", 2, "hó", "120.5000", 241, 306, link=None),
                line("support", "Túlfizetés", None, None, None, None, None, None, -12512, link=None, note="A 11512318276 számú záró elszámolás túlfizetése."),
            ]
        ),
        "settled_installments": [],
    }
    second = {
        "number": "849702246699", "type": "installment", "sequence": 2,
        "start": "2026-07-23", "end": "2026-08-22", "issued": "2026-08-26",
        "performance": "2026-09-10", "due": "2026-09-10",
        "net": 37742, "vat": 10190, "gross": 47932, "rounding": 0,
        "payable": 47932, "balance": 117706, "counterfactual": 55187,
        "provider": "MVM Next", "customer": "26138012", "account": "2607026584",
        "cycle_start": "2026-06-01",
        "consumption": [
            {"start": "2026-07-23", "end": "2026-07-31", "start_reading": 222218, "end_reading": 222446, "method": "estimated", "quantity": 228, "last_settled_date": "2026-05-31", "last_settled_value": 220875},
            {"start": "2026-08-01", "end": "2026-08-22", "start_reading": 222446, "end_reading": 223003, "method": "estimated", "quantity": 557, "last_settled_date": None, "last_settled_value": None},
        ],
        "charges": (
            energy_lines("discounted_energy", "ESZ Lakossági A1 kedvezményes árszabás ára", [("2026-07-23", "2026-07-31", 62, 317, 403)], "5.1100", link=0)
            + energy_lines("market_energy", "ESZ Lakossági A1 lakossági piaci ár", [("2026-07-23", "2026-07-31", 166, 5279, 6704)], "31.8000", link=0)
            + energy_lines("discounted_energy", "ESZ Lakossági A1 kedvezményes árszabás ára", [("2026-08-01", "2026-08-22", 152, 777, 987)], "5.1100", link=1)
            + energy_lines("market_energy", "ESZ Lakossági A1 lakossági piaci ár", [("2026-08-01", "2026-08-22", 405, 12879, 16356)], "31.8000", link=1)
            + [
                line("transmission_fee", "Átviteli forgalmi díj A1", "2026-07-23", "2026-08-22", 785, "kWh", "3.3900", 2661, 3379, link=None),
                line("distribution_fee", "Elosztói forgalmi díj A1", "2026-07-23", "2026-08-22", 785, "kWh", "20.0100", 15708, 19949, link=None),
                line("base_fee", "Elosztói alapdíj A1", "2026-07-23", "2026-08-22", 1, "hó", "120.5000", 121, 154, link=None),
            ]
        ),
        "settled_installments": [],
    }
    return [first, second]


INVOICES += current_mvm_invoices()


CYCLES = [
    ("2024-12-17", "2025-12-20", "settled", "Éves NKM villanyszámla-ciklus"),
    ("2025-12-21", "2026-05-31", "settled", "Számlázási átállással lezárt NKM villanyszámla-ciklus"),
    ("2026-06-01", None, "open", "Nyitott MVM villanyszámla-ciklus"),
]


def validate_dataset() -> None:
    numbers = [invoice["number"] for invoice in INVOICES]
    if len(numbers) != 20 or len(numbers) != len(set(numbers)):
        raise ValueError("Exactly 20 unique invoice numbers are required.")
    known_numbers = set(numbers)
    for invoice in INVOICES:
        if invoice["start"] > invoice["end"]:
            raise ValueError(f"Invalid invoice dates: {invoice['number']}")
        if sum(item["quantity"] for item in invoice["consumption"]) <= 0:
            raise ValueError(f"Missing consumption: {invoice['number']}")
        charge_total = sum(item["gross"] for item in invoice["charges"]) + invoice["rounding"]
        expected = invoice["payable"] if any(item["category"] == "support" for item in invoice["charges"]) else invoice["gross"]
        if charge_total != expected:
            raise ValueError(f"Charge total mismatch for {invoice['number']}: {charge_total} != {expected}")
        if invoice["net"] + invoice["vat"] != invoice["gross"]:
            raise ValueError(f"Invoice VAT total mismatch: {invoice['number']}")
        for number, _amount in invoice["settled_installments"]:
            if number not in known_numbers:
                raise ValueError(f"Unresolved installment {number} on {invoice['number']}")


def apply_import() -> None:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM energy_meters WHERE meter_code='electricity_main' AND energy_type='electricity'")
        meter = cursor.fetchone()
        if meter is None:
            raise RuntimeError("The electricity_main meter is missing.")
        meter_id = int(meter[0])

        placeholders = ",".join("?" for _ in INVOICES)
        cursor.execute(
            f"SELECT invoice_number FROM energy_invoices WHERE invoice_number IN ({placeholders})",
            tuple(invoice["number"] for invoice in INVOICES),
        )
        existing = sorted(row[0] for row in cursor.fetchall())
        if existing:
            raise RuntimeError("Import stopped; target invoices already exist: " + ", ".join(existing))

        cycle_ids: dict[str, int] = {}
        for start, end, status, note in CYCLES:
            cursor.execute(
                "SELECT id,cycle_end,status FROM energy_billing_cycles WHERE meter_id=? AND cycle_start=?",
                (meter_id, start),
            )
            existing_cycle = cursor.fetchone()
            if existing_cycle is None:
                cursor.execute(
                    """INSERT INTO energy_billing_cycles
                       (meter_id,cycle_start,cycle_end,status,note)
                       VALUES (?,?,?,?,?)""",
                    (meter_id, start, end, status, note),
                )
                cycle_ids[start] = int(cursor.lastrowid)
            elif str(existing_cycle[1] or "") == str(end or "") and existing_cycle[2] == status:
                cycle_ids[start] = int(existing_cycle[0])
            else:
                raise RuntimeError(f"Conflicting billing cycle already exists at {start}.")

        invoice_ids: dict[str, int] = {}
        for invoice in INVOICES:
            cursor.execute(
                """INSERT INTO energy_invoices
                   (meter_id,billing_cycle_id,invoice_number,provider_name,provider_customer_id,
                    contract_account_id,invoice_type,sequence_no,period_start_date,period_end_date,
                    issued_at,performance_at,due_at,net_amount_huf,vat_amount_huf,gross_amount_huf,
                    rounding_amount_huf,payable_amount_huf,account_balance_huf,
                    counterfactual_market_amount_huf,note)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    meter_id, cycle_ids[invoice["cycle_start"]], invoice["number"], invoice["provider"],
                    invoice["customer"], invoice["account"], invoice["type"], invoice["sequence"],
                    invoice["start"], invoice["end"], invoice["issued"], invoice["performance"],
                    invoice["due"], invoice["net"], invoice["vat"], invoice["gross"],
                    invoice["rounding"], invoice["payable"], invoice["balance"],
                    invoice["counterfactual"], "PDF-számlából ellenőrzötten importálva.",
                ),
            )
            invoice_id = int(cursor.lastrowid)
            invoice_ids[invoice["number"]] = invoice_id
            consumption_ids: list[int] = []
            for item in invoice["consumption"]:
                cursor.execute(
                    """INSERT INTO energy_invoice_consumption
                       (invoice_id,period_start_date,period_end_date,provider_start_reading,
                        provider_end_reading,reading_method,billed_consumption,quantity_unit,
                        correction_factor,corrected_consumption,heating_value_mj_m3,heat_quantity_mj,
                        last_settled_reading_date,last_settled_reading_value,
                        installment_consumption_since_settlement,note)
                       VALUES (?,?,?,?,?,?,?,'kWh',NULL,NULL,NULL,NULL,?,?,NULL,?)""",
                    (
                        invoice_id, item["start"], item["end"], item["start_reading"],
                        item["end_reading"], item["method"], item["quantity"],
                        item["last_settled_date"], item["last_settled_value"],
                        "A számlán szereplő szolgáltatói fogyasztás.",
                    ),
                )
                consumption_ids.append(int(cursor.lastrowid))
            for sort_order, item in enumerate(invoice["charges"], start=1):
                linked_id = consumption_ids[item["link"]] if item["link"] is not None else None
                cursor.execute(
                    """INSERT INTO energy_invoice_charge_lines
                       (invoice_id,invoice_consumption_id,line_category,description,
                        period_start_date,period_end_date,quantity,quantity_unit,
                        net_unit_price_huf,net_amount_huf,vat_rate_percent,tax_treatment,
                        gross_amount_huf,sort_order,note)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,'rate',?,?,?)""",
                    (
                        invoice_id, linked_id, item["category"], item["description"],
                        item["start"], item["end"], item["quantity"], item["unit"],
                        item["unit_price"], item["net"], item["vat_rate"], item["gross"],
                        sort_order, item["note"],
                    ),
                )

        for invoice in INVOICES:
            settlement_id = invoice_ids[invoice["number"]]
            for sort_order, (number, amount) in enumerate(invoice["settled_installments"], start=1):
                cursor.execute(
                    """INSERT INTO energy_invoice_settled_installments
                       (settlement_invoice_id,settled_invoice_id,provider_invoice_number,
                        gross_amount_huf,sort_order,note)
                       VALUES (?,?,?,?,?,?)""",
                    (settlement_id, invoice_ids[number], number, amount, sort_order, "A PDF elszámolószámla listája alapján."),
                )

        for cycle_id in cycle_ids.values():
            recalculate_installment_cumulative_consumption(cursor, cycle_id)

        cursor.execute(
            """SELECT COUNT(*),COUNT(DISTINCT i.invoice_number),
                      COALESCE(SUM(c.billed_consumption),0)
               FROM energy_invoices i
               LEFT JOIN energy_invoice_consumption c ON c.invoice_id=i.id
               WHERE i.meter_id=?""",
            (meter_id,),
        )
        counts = cursor.fetchone()
        if counts[0] != 21 or counts[1] != 20:
            # Twenty invoices and one extra joined row for the split August invoice.
            raise RuntimeError(f"Unexpected imported row counts: {counts}")
        connection.commit()
        print(f"Imported 20 invoices into 3 billing cycles; joined consumption rows: {counts[0]}.")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def verify_import() -> None:
    """Verify the imported target set without modifying the database."""
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM energy_meters WHERE meter_code='electricity_main'")
        meter = cursor.fetchone()
        if meter is None:
            raise RuntimeError("The electricity_main meter is missing.")
        meter_id = int(meter[0])
        expected = {invoice["number"]: invoice for invoice in INVOICES}
        placeholders = ",".join("?" for _ in expected)
        cursor.execute(
            f"""SELECT id,invoice_number,invoice_type,sequence_no,period_start_date,period_end_date,
                       net_amount_huf,vat_amount_huf,gross_amount_huf,rounding_amount_huf,
                       payable_amount_huf,account_balance_huf,counterfactual_market_amount_huf
                FROM energy_invoices WHERE meter_id=? AND invoice_number IN ({placeholders})""",
            (meter_id, *expected),
        )
        rows = cursor.fetchall()
        if len(rows) != len(expected):
            raise RuntimeError(f"Expected {len(expected)} imported invoices, found {len(rows)}.")
        invoice_ids: dict[str, int] = {}
        for row in rows:
            invoice = expected[row[1]]
            invoice_ids[row[1]] = int(row[0])
            actual = (
                row[2], row[3], str(row[4]), str(row[5]),
                int(row[6]), int(row[7]), int(row[8]), int(row[9]),
                int(row[10]), int(row[11]), int(row[12]),
            )
            wanted = (
                invoice["type"], invoice["sequence"], invoice["start"], invoice["end"],
                invoice["net"], invoice["vat"], invoice["gross"], invoice["rounding"],
                invoice["payable"], invoice["balance"], invoice["counterfactual"],
            )
            if actual != wanted:
                raise RuntimeError(f"Header mismatch for {row[1]}: {actual} != {wanted}")

        for number, invoice in expected.items():
            invoice_id = invoice_ids[number]
            cursor.execute(
                "SELECT COUNT(*),COALESCE(SUM(billed_consumption),0),COUNT(DISTINCT quantity_unit) "
                "FROM energy_invoice_consumption WHERE invoice_id=? AND quantity_unit='kWh'",
                (invoice_id,),
            )
            consumption = cursor.fetchone()
            wanted_quantity = sum(item["quantity"] for item in invoice["consumption"])
            if consumption[0] != len(invoice["consumption"]) or int(consumption[1]) != wanted_quantity or consumption[2] != 1:
                raise RuntimeError(f"Consumption mismatch for {number}: {consumption}")
            cursor.execute(
                "SELECT COUNT(*),COALESCE(SUM(gross_amount_huf),0) FROM energy_invoice_charge_lines WHERE invoice_id=?",
                (invoice_id,),
            )
            charges = cursor.fetchone()
            if charges[0] != len(invoice["charges"]) or int(charges[1]) != sum(item["gross"] for item in invoice["charges"]):
                raise RuntimeError(f"Charge mismatch for {number}: {charges}")
            cursor.execute(
                "SELECT COUNT(*),SUM(settled_invoice_id IS NULL) FROM energy_invoice_settled_installments WHERE settlement_invoice_id=?",
                (invoice_id,),
            )
            settlements = cursor.fetchone()
            if settlements[0] != len(invoice["settled_installments"]) or int(settlements[1] or 0) != 0:
                raise RuntimeError(f"Settlement-link mismatch for {number}: {settlements}")

        cursor.execute(
            """SELECT COUNT(*) FROM energy_invoice_charge_lines l
               JOIN energy_invoices i ON i.id=l.invoice_id
               WHERE i.meter_id=? AND l.line_category='support' AND l.vat_rate_percent IS NOT NULL""",
            (meter_id,),
        )
        if cursor.fetchone()[0] != 0:
            raise RuntimeError("A plain support/overpayment line has a VAT rate.")
        cursor.execute(
            """SELECT COUNT(*),SUM(quantity_unit<>'m3')
               FROM energy_invoice_consumption c
               JOIN energy_invoices i ON i.id=c.invoice_id
               JOIN energy_meters m ON m.id=i.meter_id
               WHERE m.meter_code='gas_main'"""
        )
        gas_rows = cursor.fetchone()
        if int(gas_rows[1] or 0) != 0:
            raise RuntimeError(f"Existing gas consumption rows changed unexpectedly: {gas_rows}")
        print(
            "Database verification passed: 20 invoices, 21 consumption rows, "
            f"109 charge lines, 16 linked installments; {gas_rows[0]} gas rows remain m3 records."
        )
    finally:
        cursor.close()
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit the verified invoice dataset.")
    parser.add_argument("--verify", action="store_true", help="Verify an already imported dataset.")
    arguments = parser.parse_args()
    validate_dataset()
    charge_count = sum(len(invoice["charges"]) for invoice in INVOICES)
    consumption_count = sum(len(invoice["consumption"]) for invoice in INVOICES)
    settlement_links = sum(len(invoice["settled_installments"]) for invoice in INVOICES)
    print(
        f"Verified dataset: {len(INVOICES)} invoices, {consumption_count} consumption rows, "
        f"{charge_count} charge lines, {settlement_links} settlement links."
    )
    if arguments.apply:
        apply_import()
        verify_import()
    elif arguments.verify:
        verify_import()
    else:
        print("Dry run only; use --apply to write the database.")


if __name__ == "__main__":
    main()
