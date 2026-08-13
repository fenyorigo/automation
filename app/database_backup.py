from __future__ import annotations

import gzip
import getpass
import os
import shutil
import subprocess
from datetime import UTC, datetime, time
from pathlib import Path

from polling_lock import polling_cycle_lock


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_DIR = ROOT / "exports"


def export_directory() -> Path:
    configured = (
        os.getenv("DATABASE_BACKUP_DIR")
        or os.getenv("DATABASE_EXPORT_DIR")
        or str(DEFAULT_EXPORT_DIR)
    )
    path = Path(configured).expanduser()
    return (path if path.is_absolute() else ROOT / path).resolve()


def list_database_exports() -> list[dict[str, object]]:
    directory = export_directory()
    if not directory.exists():
        return []
    exports = []
    for path in directory.glob("home_automation_*.sql.gz"):
        stat = path.stat()
        exports.append({
            "name": path.name,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).replace(tzinfo=None),
        })
    return sorted(exports, key=lambda item: str(item["name"]), reverse=True)


def create_database_export(*, filename_prefix: str = "home_automation") -> Path:
    dump_binary = os.getenv("MARIADB_DUMP_BIN") or shutil.which("mariadb-dump")
    if dump_binary is None and Path("/opt/homebrew/bin/mariadb-dump").is_file():
        dump_binary = "/opt/homebrew/bin/mariadb-dump"
    if dump_binary is None:
        raise RuntimeError("A mariadb-dump nem található.")

    database_name = os.getenv("DB_NAME", "home_automation")
    directory = export_directory()
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    final_path = directory / f"{filename_prefix}_{timestamp}.sql.gz"
    temporary_path = directory / f".{final_path.name}.{os.getpid()}.tmp"
    command = [
        dump_binary,
        f"--user={os.getenv('DB_USER') or getpass.getuser()}",
        "--single-transaction",
        "--quick",
        "--skip-lock-tables",
        "--triggers",
        "--hex-blob",
        "--default-character-set=utf8mb4",
        "--databases",
        database_name,
    ]
    database_host = os.getenv("DB_HOST", "localhost")
    socket_path = os.getenv("DB_SOCKET")
    if not socket_path and database_host in {"localhost", "127.0.0.1"}:
        socket_path = next(
            (str(path) for path in (
                Path("/tmp/mysql.sock"),
                Path("/var/run/mysqld/mysqld.sock"),
                Path("/var/lib/mysql/mysql.sock"),
            ) if path.exists()),
            None,
        )
    if socket_path:
        command.insert(1, f"--socket={socket_path}")
    else:
        command[1:1] = [
            f"--host={database_host}", f"--port={os.getenv('DB_PORT', '3306')}"
        ]
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = os.environ["DB_PASSWORD"]

    try:
        with polling_cycle_lock(wait=True, operation="database_export"):
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment
            )
            assert process.stdout is not None
            with temporary_path.open("xb") as raw_output:
                os.chmod(temporary_path, 0o600)
                with gzip.GzipFile(fileobj=raw_output, mode="wb", mtime=0) as compressed:
                    shutil.copyfileobj(process.stdout, compressed)
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"A MariaDB export sikertelen: {stderr.strip()}")
            if temporary_path.stat().st_size == 0:
                raise RuntimeError("A MariaDB export üres fájlt készített.")
            temporary_path.replace(final_path)
        return final_path
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _scheduled_backup_time() -> time:
    raw_value = os.getenv("DATABASE_BACKUP_TIME", "03:00").strip()
    try:
        return datetime.strptime(raw_value, "%H:%M").time()
    except ValueError as error:
        raise RuntimeError(
            "A DATABASE_BACKUP_TIME értéke HH:MM formátumú legyen."
        ) from error


def scheduled_backup_due(now: datetime | None = None) -> bool:
    """Return whether today's automatic backup is due in local time."""
    now = now or datetime.now().astimezone()
    scheduled_at = datetime.combine(now.date(), _scheduled_backup_time(), now.tzinfo)
    if now < scheduled_at:
        return False
    directory = export_directory()
    return not any(
        datetime.fromtimestamp(path.stat().st_mtime, now.tzinfo) >= scheduled_at
        for path in directory.glob("home_automation_auto_*.sql.gz")
    ) if directory.exists() else True


def prune_scheduled_backups() -> list[Path]:
    try:
        keep = int(os.getenv("DATABASE_BACKUP_KEEP", "30"))
    except ValueError as error:
        raise RuntimeError("A DATABASE_BACKUP_KEEP egész szám legyen.") from error
    if keep < 1:
        raise RuntimeError("A DATABASE_BACKUP_KEEP legalább 1 legyen.")
    paths = sorted(
        export_directory().glob("home_automation_auto_*.sql.gz"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    removed = paths[keep:]
    for path in removed:
        path.unlink()
    return removed


def create_scheduled_database_backup() -> tuple[Path, list[Path]]:
    path = create_database_export(filename_prefix="home_automation_auto")
    return path, prune_scheduled_backups()
