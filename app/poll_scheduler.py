#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

from database import Database
from database_backup import create_scheduled_database_backup, scheduled_backup_due
from poll_devices import DEFAULT_CONFIG, load_devices, poll_all
from polling_lock import PollCycleBusy, polling_cycle_lock
from outdoor_weather import poll_active_outdoor_sources
from scheduled_climate import process_due_climate_schedules


async def run_cycle(
    timeout: float,
    *,
    due_only: bool = False,
    poll_outdoor: bool = True,
    poll_origin: str = "automatic",
) -> tuple[int, int, int]:
    if poll_origin not in {"automatic", "manual"}:
        raise ValueError(f"Unsupported poll origin: {poll_origin}")
    with polling_cycle_lock():
        configured = load_devices(DEFAULT_CONFIG)
        selector = Database()
        try:
            devices = selector.polling_configs(configured, due_only=due_only)
        finally:
            selector.close()
        if not devices and not poll_outdoor:
            return 0, 0, 0
        configs = {(item.source_system, item.device_id): item for item in devices}
        results = await poll_all(devices, timeout)
        database = Database()
        stored = 0
        try:
            for result in results:
                try:
                    database.persist(
                        configs[(result.source_system, result.device_id)],
                        result,
                        result.duration_ms,
                        poll_origin=poll_origin,
                    )
                    stored += 1
                except Exception as error:
                    print(
                        f"{datetime.now().isoformat(timespec='seconds')} "
                        f"database error for {result.device_id}: {error}",
                        flush=True,
                    )
        finally:
            database.close()
        outdoor_successful, outdoor_attempted = (0, 0)
        if poll_outdoor:
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

    loop = asyncio.get_running_loop()
    next_poll = loop.time()
    next_outdoor_poll = loop.time()
    while True:
        load_dotenv(DEFAULT_CONFIG.parents[1] / ".env", override=True)
        configured_interval = max(10, int(os.getenv("POLL_INTERVAL_SECONDS", str(args.interval))))
        configured_timeout = float(os.getenv("POLL_TIMEOUT_SECONDS", str(args.timeout)))
        if loop.time() >= next_poll:
            started = loop.time()
            try:
                include_outdoor = loop.time() >= next_outdoor_poll
                successful, stored, total = await run_cycle(
                    configured_timeout, due_only=True, poll_outdoor=include_outdoor
                )
                if include_outdoor:
                    next_outdoor_poll = started + configured_interval
                if total:
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
            # Wake frequently; each device's own interval determines whether it is due.
            next_poll = started + min(configured_interval, 10)
        if args.once:
            return
        try:
            processed = await process_due_climate_schedules()
            if processed:
                print(
                    f"{datetime.now().isoformat(timespec='seconds')} "
                    f"scheduled climate commands complete: {processed}", flush=True,
                )
        except Exception as error:
            print(
                f"{datetime.now().isoformat(timespec='seconds')} "
                f"scheduled climate command failed: {error}", flush=True,
            )
        try:
            if scheduled_backup_due():
                backup_path, removed = await asyncio.to_thread(
                    create_scheduled_database_backup
                )
                print(
                    f"{datetime.now().isoformat(timespec='seconds')} "
                    f"database backup complete: {backup_path} "
                    f"({len(removed)} old automatic backup(s) removed)",
                    flush=True,
                )
        except Exception as error:
            print(
                f"{datetime.now().isoformat(timespec='seconds')} "
                f"database backup failed: {error}",
                flush=True,
            )
        await asyncio.sleep(max(1, min(10, next_poll - loop.time())))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
