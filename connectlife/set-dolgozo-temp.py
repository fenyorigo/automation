#!/usr/bin/env python3

import argparse
import asyncio
import os
from getpass import getpass

from connectlife.api import ConnectLifeApi, LifeConnectError


async def main(username: str, temperature: int) -> None:
    password = getpass("Password: ")
    api = ConnectLifeApi(username, password)

    try:
        appliances = await api.get_appliances()

        dolgozo = next(
            (
                appliance
                for appliance in appliances
                if appliance.device_nickname == "Dolgozó"
            ),
            None,
        )

        if dolgozo is None:
            raise RuntimeError("A Dolgozó nevű klíma nem található.")

        print(
            f"Eszköz: {dolgozo.device_nickname} "
            f"({dolgozo.device_type_code}-{dolgozo.device_feature_code})"
        )

        # Első körben csak a célhőmérsékletet írjuk.
        await api.update_appliance(
            dolgozo.puid,
            {"t_temp": str(temperature)},
        )

        print(f"Parancs elküldve: t_temp={temperature}")

    except LifeConnectError as exc:
        print(f"ConnectLife API-hiba: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A Dolgozó Hisense klíma célhőmérsékletének módosítása."
    )
    parser.add_argument(
        "temperature",
        type=int,
        choices=range(16, 33),
        metavar="16-32",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("CONNECTLIFE_USERNAME"),
    )
    args = parser.parse_args()

    asyncio.run(main(args.username, args.temperature))
