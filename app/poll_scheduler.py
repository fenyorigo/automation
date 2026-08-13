#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

from database import Database
from poll_devices import DEFAULT_CONFIG, load_devices, poll_all
from polling_lock import PollCycleBusy, polling_cycle_lock
from outdoor_weather import poll_active_outdoor_sources


async def run_cycle(timeout: float) -> tuple[int, int, int]:
    with polling_cycle_lock():
        devices = load_devices(DEFAULT_CONFIG)
        configs = {(item.source_system, item.device_id): item for item in devices}
        results = await poll_all(devices, timeout)
        database = Database()
        stored = 0
        try:
            for result in results:
                try:
                    database.persist(configs[(result.source_system, result.device_id)], result, result.duration_ms)
                    stored += 1
                except Exception as error:
                    print(
                        f"{datetime.now().isoformat(timespec='seconds')} "
                        f"database error for {result.device_id}: {error}",
                        flush=True,
                    )
        finally:
            database.close()
        outdoor_successful, outdoor_attempted = await asyncio.to_thread(
            poll_active_outdoor_sources, timeout
        )
        if outdoor_attempted:
            print(
                f"{datetime.now().isoformat(timespec='seconds')} "
                f"outdoor weather: {outdoor_successful}/{outdoor_attempted} successful",
                flush=True,
            )
        successful = sum(1 for item in results if item.success)
        return successful, stored, len(devices)


async def main() -> None:
    load_dotenv(DEFAULT_CONFIG.parents[1] / ".env")
    parser = argparse.ArgumentParser(description="Periodically poll and store every device.")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("POLL_INTERVAL_SECONDS", "600")),
        help="Seconds between polling cycle starts (default: 600)",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval < 10:
        parser.error("--interval must be at least 10 seconds")

    while True:
        started = asyncio.get_running_loop().time()
        try:
            successful, stored, total = await run_cycle(args.timeout)
            print(
                f"{datetime.now().isoformat(timespec='seconds')} "
                f"poll complete: {successful}/{total} successful, {stored}/{total} stored",
                flush=True,
            )
        except PollCycleBusy:
            print(
                f"{datetime.now().isoformat(timespec='seconds')} "
                "poll skipped: another polling cycle is already running",
                flush=True,
            )
        except Exception as error:
            print(
                f"{datetime.now().isoformat(timespec='seconds')} polling cycle failed: {error}",
                flush=True,
            )
        if args.once:
            return
        elapsed = asyncio.get_running_loop().time() - started
        await asyncio.sleep(max(0, args.interval - elapsed))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
