from __future__ import annotations

import hashlib
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, date, datetime, time as datetime_time, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import mariadb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "http://www.mnb.hu/arfolyamok.asmx"
SOAP_ACTION = "http://www.mnb.hu/webservices/MNBArfolyamServiceSoap/GetCurrentExchangeRates"
LOCAL_TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/Budapest"))
FIRST_ATTEMPT = datetime_time(11, 35)
FAILED_RETRY_INTERVAL = timedelta(minutes=30)

SOAP_REQUEST = b"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetCurrentExchangeRates xmlns="http://www.mnb.hu/webservices/"/>
  </soap:Body>
</soap:Envelope>"""


class MnbExchangeRateError(RuntimeError):
    def __init__(self, code: str, message: str, http_status: int | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


@dataclass(frozen=True)
class ExchangeRate:
    rate_date: date
    currency: str
    unit: int
    rate_huf: Decimal


def connect_database() -> mariadb.Connection:
    return mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        autocommit=False,
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_current_exchange_rates(payload: bytes, currency: str = "EUR") -> ExchangeRate:
    try:
        envelope = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError("MNB response is not valid XML") from error
    result = next(
        (
            element
            for element in envelope.iter()
            if _local_name(element.tag) == "GetCurrentExchangeRatesResult"
        ),
        None,
    )
    if result is None or not result.text:
        raise ValueError("MNB response contains no exchange-rate result")
    try:
        rates = ET.fromstring(result.text)
    except ET.ParseError as error:
        raise ValueError("MNB exchange-rate result is not valid XML") from error
    day = next((item for item in rates.iter() if _local_name(item.tag) == "Day"), None)
    if day is None or not day.attrib.get("date"):
        raise ValueError("MNB exchange-rate result contains no date")
    requested_currency = currency.upper()
    rate = next(
        (
            item
            for item in day
            if _local_name(item.tag) == "Rate"
            and item.attrib.get("curr", "").upper() == requested_currency
        ),
        None,
    )
    if rate is None or not rate.text:
        raise ValueError(f"MNB response contains no {requested_currency} rate")
    try:
        unit = int(rate.attrib.get("unit", "1"))
        quoted_rate = Decimal(rate.text.strip().replace(",", "."))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("MNB exchange rate is invalid") from error
    if unit <= 0 or quoted_rate <= 0:
        raise ValueError("MNB exchange rate and unit must be positive")
    return ExchangeRate(
        rate_date=date.fromisoformat(day.attrib["date"]),
        currency=requested_currency,
        unit=unit,
        rate_huf=quoted_rate / unit,
    )


def collection_due(
    now_local: datetime, latest_attempt: tuple[datetime, bool] | None
) -> bool:
    if now_local.timetz().replace(tzinfo=None) < FIRST_ATTEMPT:
        return False
    if latest_attempt is None:
        return True
    latest_attempted_at, success = latest_attempt
    latest_local = latest_attempted_at.replace(tzinfo=UTC).astimezone(LOCAL_TIMEZONE)
    if latest_local.date() < now_local.date():
        return True
    elapsed = now_local.astimezone(UTC).replace(tzinfo=None) - latest_attempted_at
    return not success and elapsed >= FAILED_RETRY_INTERVAL


def _request_payload(timeout: float) -> tuple[bytes, int]:
    request = urllib.request.Request(
        ENDPOINT,
        data=SOAP_REQUEST,
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": SOAP_ACTION,
            "User-Agent": "automation/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), int(response.status)
    except urllib.error.HTTPError as error:
        raise MnbExchangeRateError(
            "http_error", f"MNB HTTP {error.code}", error.code
        ) from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise MnbExchangeRateError(
            "network_error", "MNB exchange-rate request failed"
        ) from error


def poll_mnb_exchange_rate(
    timeout: float = 30.0, *, force: bool = False
) -> dict[str, object]:
    now_local = datetime.now(LOCAL_TIMEZONE)
    connection = connect_database()
    cursor = connection.cursor()
    started = time.monotonic()
    try:
        cursor.execute(
            "SELECT attempted_at,success FROM currency_exchange_rate_poll_attempts "
            "ORDER BY attempted_at DESC,id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        latest_attempt = (row[0], bool(row[1])) if row else None
        if not force and not collection_due(now_local, latest_attempt):
            return {"status": "not_due"}
        attempted_at = datetime.now(UTC)
        try:
            payload, http_status = _request_payload(timeout)
            rate = parse_current_exchange_rates(payload)
            payload_hash = hashlib.sha256(payload).hexdigest()
            cursor.execute(
                """SELECT id FROM currency_exchange_rate_observations
                    WHERE source_code='mnb' AND rate_date=? AND currency=?
                      AND payload_sha256=?""",
                (rate.rate_date, rate.currency, payload_hash),
            )
            existing = cursor.fetchone()
            stored = existing is None
            if existing is None:
                cursor.execute(
                    """INSERT INTO currency_exchange_rate_observations
                         (source_code,fetched_at,rate_date,currency,unit,rate_huf,
                          payload_sha256,raw_payload)
                       VALUES ('mnb',?,?,?,?,?,?,?)""",
                    (
                        attempted_at.replace(tzinfo=None),
                        rate.rate_date,
                        rate.currency,
                        rate.unit,
                        rate.rate_huf,
                        payload_hash,
                        payload.decode("utf-8"),
                    ),
                )
                observation_id = int(cursor.lastrowid)
            else:
                observation_id = int(existing[0])
            cursor.execute(
                """INSERT INTO currency_exchange_rate_poll_attempts
                     (attempted_at,completed_at,success,http_status,rate_date,
                      duration_ms,observation_id)
                   VALUES (?,?,1,?,?,?,?)""",
                (
                    attempted_at.replace(tzinfo=None),
                    datetime.now(UTC).replace(tzinfo=None),
                    http_status,
                    rate.rate_date,
                    round((time.monotonic() - started) * 1000),
                    observation_id,
                ),
            )
            connection.commit()
            return {
                "status": "stored" if stored else "unchanged",
                "rate_date": rate.rate_date.isoformat(),
                "currency": rate.currency,
                "rate_huf": str(rate.rate_huf),
            }
        except Exception as error:
            error_code = (
                error.code if isinstance(error, MnbExchangeRateError) else type(error).__name__
            )
            http_status = error.http_status if isinstance(error, MnbExchangeRateError) else None
            cursor.execute(
                """INSERT INTO currency_exchange_rate_poll_attempts
                     (attempted_at,completed_at,success,http_status,error_code,
                      error_message,duration_ms)
                   VALUES (?,?,0,?,?,?,?)""",
                (
                    attempted_at.replace(tzinfo=None),
                    datetime.now(UTC).replace(tzinfo=None),
                    http_status,
                    error_code[:64],
                    str(error)[:1000],
                    round((time.monotonic() - started) * 1000),
                ),
            )
            connection.commit()
            return {"status": "failed", "error_code": error_code}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    print("MNB EUR/HUF:", poll_mnb_exchange_rate(force=True))
