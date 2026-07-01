import sqlite3
from pathlib import Path

from durability import DurabilityMaintenance


def make_db(path: Path, value: str):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE sample(value TEXT)")
        db.execute("INSERT INTO sample(value) VALUES (?)", (value,))


def test_sqlite_backup_is_consistent_and_readable(tmp_path):
    first = tmp_path / "agency.db"
    second = tmp_path / "prospecting.db"
    make_db(first, "mission durable")
    make_db(second, "prospect public")
    maintenance = DurabilityMaintenance(
        [first, second], tmp_path / "backups", interval_hours=24, keep_per_database=3)
    status = maintenance.backup_now()
    assert status["last_ok"] is True
    assert len(status["files"]) == 2
    for item in status["files"]:
        backup = Path(item["backup"])
        assert backup.exists()
        assert len(item["sha256"]) == 64
        with sqlite3.connect(backup) as db:
            assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            assert db.execute("SELECT value FROM sample").fetchone()[0]


def test_backup_retention_keeps_recent_files(tmp_path):
    db_path = tmp_path / "agency.db"
    make_db(db_path, "ok")
    backup_dir = tmp_path / "backups"
    maintenance = DurabilityMaintenance(
        [db_path], backup_dir, interval_hours=24, keep_per_database=2)
    for idx in range(5):
        fake = backup_dir / f"agency_2026010{idx}T000000Z.db"
        backup_dir.mkdir(exist_ok=True)
        fake.write_bytes(b"old")
        fake.touch()
    maintenance._prune("agency")
    assert len(list(backup_dir.glob("agency_*.db"))) == 2
