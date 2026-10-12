from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, date, datetime, time as datetime_time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import mariadb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://web-api.tp.entsoe.eu/api"
HUPX_ENDPOINT = "https://labs.hupx.hu/data/v1/dam_aggregated_trading_data_15min"
HUPX_EMBEDDING_ID = "cmrxlalno005y3m273etcyyt1"
HU_BIDDING_ZONE = "10YHU-MAVIR----U"
ENTSOE_SOURCE_CODE = "entsoe"
HUPX_SOURCE_CODE = "hupx"
LOCAL_TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/Budapest"))
MARKET_TIMEZONE = timezone(timedelta(hours=1), "CET")
FIRST_ATTEMPT = datetime_time(13, 5)
LAST_REVISION_CHECK = datetime_time(18, 30)
FAILED_RETRY_INTERVAL = timedelta(minutes=15)
SUCCESS_RETRY_INTERVAL = timedelta(hours=1)


class EntsoeResponseError(RuntimeError):
    def __init__(self, code: str, message: str, http_status: int | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class EntsoeNoData(EntsoeResponseError):
    pass


@dataclass(frozen=True)
class PricePoint:
    position: int
    interval_start: datetime
    interval_end: datetime
    resolution_minutes: int
    price_eur_mwh: Decimal


@dataclass(frozen=True)
class PriceDocument:
    document_mrid: str | None
    revision_number: int | None
    period_start: datetime
    period_end: datetime
    currency: str
    price_unit: str
    points: tuple[PricePoint, ...]


def connect_database() -> mariadb.Connection:
    return mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        autocommit=False,
    )


def delivery_window_utc(delivery_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(delivery_date, datetime_time.min, LOCAL_TIMEZONE)
    end = datetime.combine(delivery_date + timedelta(days=1), datetime_time.min, LOCAL_TIMEZONE)
    return start.astimezone(UTC), end.astimezone(UTC)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if _local_name(item.tag) == name), None)


def _text(element: ET.Element, name: str) -> str | None:
    child = _child(element, name)
    return child.text.strip() if child is not None and child.text else None


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolution_minutes(value: str) -> int:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?", value)
    if not match:
        raise ValueError(f"Unsupported ENTSO-E resolution: {value}")
    minutes = int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    if minutes <= 0:
        raise ValueError(f"Invalid ENTSO-E resolution: {value}")
    return minutes


def _acknowledgement_error(root: ET.Element) -> EntsoeResponseError:
    reasons = [item for item in root.iter() if _local_name(item.tag) == "Reason"]
    code = _text(reasons[0], "code") if reasons else None
    message = _text(reasons[0], "text") if reasons else None
    safe_code = code or "acknowledgement"
    safe_message = message or "ENTSO-E rejected the request"
    if safe_code == "999" and "No matching data" in safe_message:
        return EntsoeNoData("no_data_yet", safe_message)
    return EntsoeResponseError(safe_code, safe_message)


def parse_price_document(payload: bytes) -> PriceDocument:
    root = ET.fromstring(payload)
    if _local_name(root.tag) == "Acknowledgement_MarketDocument":
        raise _acknowledgement_error(root)

    document_mrid = _text(root, "mRID")
    revision_text = _text(root, "revisionNumber")
    revision_number = int(revision_text) if revision_text else None
    points: list[PricePoint] = []
    currency: str | None = None
    price_unit: str | None = None
    period_starts: list[datetime] = []
    period_ends: list[datetime] = []

    for series in _children(root, "TimeSeries"):
        series_currency = _text(series, "currency_Unit.name")
        series_unit = _text(series, "price_Measure_Unit.name")
        currency = currency or series_currency
        price_unit = price_unit or series_unit
        if currency != series_currency or price_unit != series_unit:
            raise ValueError("ENTSO-E response mixes currencies or price units")
        for period in _children(series, "Period"):
            interval = _child(period, "timeInterval")
            if interval is None:
                raise ValueError("ENTSO-E period has no time interval")
            start_text, end_text = _text(interval, "start"), _text(interval, "end")
            resolution_text = _text(period, "resolution")
            if not start_text or not end_text or not resolution_text:
                raise ValueError("ENTSO-E period metadata is incomplete")
            start, end = _parse_timestamp(start_text), _parse_timestamp(end_text)
            resolution = _resolution_minutes(resolution_text)
            period_starts.append(start)
            period_ends.append(end)
            period_points = _children(period, "Point")
            expected_points = round(
                (end - start).total_seconds() / (resolution * 60)
            )
            positions = {
                int(position_text)
                for point in period_points
                if (position_text := _text(point, "position")) is not None
            }
            if positions != set(range(1, expected_points + 1)):
                raise EntsoeResponseError(
                    "incomplete_data",
                    f"ENTSO-E period contains {len(positions)} of "
                    f"{expected_points} expected price points",
                )
            for point in period_points:
                position_text = _text(point, "position")
                price_text = _text(point, "price.amount")
                if not position_text or price_text is None:
                    raise ValueError("ENTSO-E point is incomplete")
                position = int(position_text)
                interval_start = start + timedelta(minutes=(position - 1) * resolution)
                points.append(PricePoint(
                    position=position,
                    interval_start=interval_start,
                    interval_end=interval_start + timedelta(minutes=resolution),
                    resolution_minutes=resolution,
                    price_eur_mwh=Decimal(price_text),
                ))

    if not points or currency is None or price_unit is None:
        raise ValueError("ENTSO-E response contains no day-ahead price points")
    points.sort(key=lambda item: item.interval_start)
    if len({item.interval_start for item in points}) != len(points):
        raise ValueError("ENTSO-E response contains duplicate price intervals")
    return PriceDocument(
        document_mrid=document_mrid,
        revision_number=revision_number,
        period_start=min(period_starts),
        period_end=max(period_ends),
        currency=currency,
        price_unit=price_unit,
        points=tuple(points),
    )


def parse_hupx_price_document(payload: bytes, delivery_date: date) -> PriceDocument:
    try:
        response = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("HUPX response is not valid JSON") from error
    rows = response.get("data") if isinstance(response, dict) else None
    if not isinstance(rows, list) or not rows:
        raise EntsoeNoData("no_data_yet", "HUPX has no matching day-ahead price data yet")

    points: list[PricePoint] = []
    start, end = delivery_window_utc(delivery_date)
    expected_points = int((end - start).total_seconds() // (15 * 60))
    seen_positions: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("HUPX response contains an invalid row")
        if row.get("Region") != "HU" or row.get("Status") != "final":
            continue
        row_date = str(row.get("DeliveryDay", ""))[:10]
        if row_date != delivery_date.isoformat():
            continue
        try:
            position = int(row["ProductQH"])
            price = Decimal(str(row["Price"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("HUPX price row is incomplete") from error
        if position in seen_positions:
            raise ValueError("HUPX response contains duplicate quarter hours")
        seen_positions.add(position)
        interval_start = start + timedelta(minutes=(position - 1) * 15)
        points.append(PricePoint(
            position=position,
            interval_start=interval_start,
            interval_end=interval_start + timedelta(minutes=15),
            resolution_minutes=15,
            price_eur_mwh=price,
        ))

    points.sort(key=lambda item: item.position)
    if len(points) != expected_points or [point.position for point in points] != list(
        range(1, expected_points + 1)
    ):
        raise ValueError(
            f"HUPX response contains {len(points)} final quarter hours; expected {expected_points}"
        )
    return PriceDocument(
        document_mrid=f"hupx-dam-{delivery_date.isoformat()}",
        revision_number=None,
        period_start=start,
        period_end=end,
        currency="EUR",
        price_unit="MWH",
        points=tuple(points),
    )


def collection_due(
    now_local: datetime,
    latest_attempt: tuple[datetime, bool] | None,
) -> bool:
    market_now = now_local.astimezone(MARKET_TIMEZONE)
    if market_now.timetz().replace(tzinfo=None) < FIRST_ATTEMPT:
        return False
    if latest_attempt is None:
        return True
    attempted_at, success = latest_attempt
    elapsed = now_local.astimezone(UTC).replace(tzinfo=None) - attempted_at
    if not success:
        return elapsed >= FAILED_RETRY_INTERVAL
    return market_now.timetz().replace(tzinfo=None) <= LAST_REVISION_CHECK and elapsed >= SUCCESS_RETRY_INTERVAL


def _latest_attempt(cursor: mariadb.Cursor, delivery_date: date) -> tuple[datetime, bool] | None:
    cursor.execute(
        """SELECT attempted_at,success FROM electricity_day_ahead_price_poll_attempts
           WHERE delivery_date=? ORDER BY attempted_at DESC,id DESC LIMIT 1""",
        (delivery_date,),
    )
    row = cursor.fetchone()
    return (row[0], bool(row[1])) if row else None


def _request_payload(token: str, delivery_date: date, timeout: float) -> tuple[bytes, int]:
    start, end = delivery_window_utc(delivery_date)
    query = urllib.parse.urlencode({
        "securityToken": token,
        "documentType": "A44",
        "in_Domain": HU_BIDDING_ZONE,
        "out_Domain": HU_BIDDING_ZONE,
        "periodStart": start.strftime("%Y%m%d%H%M"),
        "periodEnd": end.strftime("%Y%m%d%H%M"),
    })
    request = urllib.request.Request(
        f"{ENDPOINT}?{query}", headers={"User-Agent": "automation/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), int(response.status)
    except urllib.error.HTTPError as error:
        body = error.read()
        try:
            parsed = ET.fromstring(body)
            acknowledgement = _acknowledgement_error(parsed)
            acknowledgement.http_status = error.code
            raise acknowledgement
        except ET.ParseError:
            raise EntsoeResponseError("http_error", f"ENTSO-E HTTP {error.code}", error.code) from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise EntsoeResponseError("network_error", "ENTSO-E network request failed") from error


def _request_hupx_payload(delivery_date: date, timeout: float) -> tuple[bytes, int]:
    filters = ",".join((
        f"DeliveryDay__gte__{delivery_date.isoformat()}",
        f"DeliveryDay__lte__{delivery_date.isoformat()}",
        "Region__in__HU",
    ))
    query = urllib.parse.urlencode({"filter": filters})
    request = urllib.request.Request(
        f"{HUPX_ENDPOINT}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "automation/1.0",
            "x-embedding-id": HUPX_EMBEDDING_ID,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), int(response.status)
    except urllib.error.HTTPError as error:
        raise EntsoeResponseError(
            "hupx_http_error", f"HUPX HTTP {error.code}", error.code
        ) from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise EntsoeResponseError("hupx_network_error", "HUPX network request failed") from error


def _store_document(
    cursor: mariadb.Cursor,
    source_code: str,
    delivery_date: date,
    fetched_at: datetime,
    payload: bytes,
    document: PriceDocument,
) -> tuple[int, bool]:
    # Hash the normalized market content, not response-only metadata such as a
    # generated document timestamp. The same published curve therefore stays
    # one run, while a changed revision or price produces a new auditable run.
    normalized = "\n".join([
        str(document.revision_number or ""),
        document.currency,
        document.price_unit,
        *(
            f"{point.interval_start.isoformat()}|{point.interval_end.isoformat()}|"
            f"{point.resolution_minutes}|{point.price_eur_mwh}"
            for point in document.points
        ),
    ])
    payload_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    cursor.execute(
        "SELECT id FROM electricity_day_ahead_price_runs WHERE source_code=? AND payload_sha256=?",
        (source_code, payload_hash),
    )
    row = cursor.fetchone()
    if row:
        return int(row[0]), False
    cursor.execute(
        """INSERT INTO electricity_day_ahead_price_runs
             (source_code,fetched_at,delivery_date,document_mrid,revision_number,
              period_start,period_end,currency,price_unit,point_count,payload_sha256,raw_payload)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source_code,
            fetched_at.astimezone(UTC).replace(tzinfo=None),
            delivery_date,
            document.document_mrid,
            document.revision_number,
            document.period_start.replace(tzinfo=None),
            document.period_end.replace(tzinfo=None),
            document.currency,
            document.price_unit,
            len(document.points),
            payload_hash,
            payload.decode("utf-8"),
        ),
    )
    run_id = int(cursor.lastrowid)
    cursor.executemany(
        """INSERT INTO electricity_day_ahead_price_points
             (run_id,position,interval_start,interval_end,resolution_minutes,price_eur_mwh)
           VALUES (?,?,?,?,?,?)""",
        [
            (
                run_id,
                point.position,
                point.interval_start.replace(tzinfo=None),
                point.interval_end.replace(tzinfo=None),
                point.resolution_minutes,
                point.price_eur_mwh,
            )
            for point in document.points
        ],
    )
    return run_id, True


def poll_day_ahead_prices(timeout: float = 30.0, *, force: bool = False) -> dict[str, object]:
    token = os.getenv("ENTSOE_API_TOKEN", "").strip()
    if not token:
        return {"status": "disabled", "reason": "missing_token"}
    now_local = datetime.now(LOCAL_TIMEZONE)
    delivery_date = now_local.date() + timedelta(days=1)
    connection = connect_database()
    cursor = connection.cursor()
    started = time.monotonic()
    try:
        if not force and not collection_due(now_local, _latest_attempt(cursor, delivery_date)):
            return {"status": "not_due", "delivery_date": delivery_date.isoformat()}
        fetched_at = datetime.now(UTC)
        try:
            payload, http_status = _request_payload(token, delivery_date, timeout)
            try:
                document = parse_price_document(payload)
            except EntsoeResponseError as error:
                error.http_status = http_status
                raise
            run_id, stored = _store_document(
                cursor, ENTSOE_SOURCE_CODE, delivery_date, fetched_at, payload, document
            )
            cursor.execute(
                """INSERT INTO electricity_day_ahead_price_poll_attempts
                     (attempted_at,completed_at,delivery_date,success,http_status,duration_ms,run_id)
                   VALUES (?,?,?,1,?,?,?)""",
                (
                    fetched_at.replace(tzinfo=None),
                    datetime.now(UTC).replace(tzinfo=None),
                    delivery_date,
                    http_status,
                    round((time.monotonic() - started) * 1000),
                    run_id,
                ),
            )
            connection.commit()
            return {
                "status": "stored" if stored else "unchanged",
                "delivery_date": delivery_date.isoformat(),
                "point_count": len(document.points),
                "run_id": run_id,
                "source": ENTSOE_SOURCE_CODE,
            }
        except EntsoeResponseError as error:
            try:
                payload, http_status = _request_hupx_payload(delivery_date, timeout)
                document = parse_hupx_price_document(payload, delivery_date)
                run_id, stored = _store_document(
                    cursor, HUPX_SOURCE_CODE, delivery_date, fetched_at, payload, document
                )
                cursor.execute(
                    """INSERT INTO electricity_day_ahead_price_poll_attempts
                         (attempted_at,completed_at,delivery_date,success,http_status,duration_ms,run_id)
                       VALUES (?,?,?,1,?,?,?)""",
                    (
                        fetched_at.replace(tzinfo=None),
                        datetime.now(UTC).replace(tzinfo=None),
                        delivery_date,
                        http_status,
                        round((time.monotonic() - started) * 1000),
                        run_id,
                    ),
                )
                connection.commit()
                return {
                    "status": "stored" if stored else "unchanged",
                    "delivery_date": delivery_date.isoformat(),
                    "point_count": len(document.points),
                    "run_id": run_id,
                    "source": HUPX_SOURCE_CODE,
                    "fallback_reason": error.code,
                }
            except Exception as hupx_error:
                hupx_code = (
                    hupx_error.code
                    if isinstance(hupx_error, EntsoeResponseError)
                    else type(hupx_error).__name__
                )
                combined_message = (
                    f"ENTSO-E: {error}; HUPX fallback: {str(hupx_error)[:700]}"
                )
            cursor.execute(
                """INSERT INTO electricity_day_ahead_price_poll_attempts
                     (attempted_at,completed_at,delivery_date,success,http_status,
                      error_code,error_message,duration_ms)
                   VALUES (?,?,?,0,?,?,?,?)""",
                (
                    fetched_at.replace(tzinfo=None),
                    datetime.now(UTC).replace(tzinfo=None),
                    delivery_date,
                    error.http_status,
                    f"{error.code}+{hupx_code}"[:100],
                    combined_message[:1000],
                    round((time.monotonic() - started) * 1000),
                ),
            )
            connection.commit()
            return {"status": error.code, "delivery_date": delivery_date.isoformat()}
        except Exception as error:
            cursor.execute(
                """INSERT INTO electricity_day_ahead_price_poll_attempts
                     (attempted_at,completed_at,delivery_date,success,error_code,error_message,duration_ms)
                   VALUES (?,?,?,0,?,?,?)""",
                (
                    fetched_at.replace(tzinfo=None),
                    datetime.now(UTC).replace(tzinfo=None),
                    delivery_date,
                    type(error).__name__,
                    str(error)[:1000],
                    round((time.monotonic() - started) * 1000),
                ),
            )
            connection.commit()
            return {"status": "invalid_response", "delivery_date": delivery_date.isoformat()}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    result = poll_day_ahead_prices(force=True)
    print("Day-ahead prices:", result)
