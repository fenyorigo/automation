#!/usr/bin/env python3

import os

import broadlink

DEVICES = [
    {
        "name": "Computherm-26",
        "ip": os.environ["COMPUTHERM_1_IP"],
        "mac": "a043b0366316",
    },
    {
        "name": "Computherm-27",
        "ip": os.environ["COMPUTHERM_2_IP"],
        "mac": "a043b0364e7a",
    },
]

for cfg in DEVICES:
    dev = broadlink.gendevice(
        0x4EAD,
        (cfg["ip"], 80),
        bytes.fromhex(cfg["mac"]),
        name=cfg["name"],
    )

    dev.auth()
    status = dev.get_full_status()

    print(
        f"{cfg['name']}: "
        f"{status['room_temp']:.1f} °C, "
        f"target {status['thermostat_temp']:.1f} °C, "
        f"active={status['active']}, "
        f"power={status['power']}"
    )
