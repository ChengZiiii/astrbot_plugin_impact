from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RankEntry:
    user_id: int
    length_cm: float


@dataclass(frozen=True, slots=True)
class InjectionEntry:
    date_text: str
    volume_ml: float


class ImpactStore:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._data_dir / "impact.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    jj_length REAL NOT NULL,
                    last_active_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY,
                    enabled INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS injections (
                    user_id INTEGER NOT NULL,
                    date_text TEXT NOT NULL,
                    volume_ml REAL NOT NULL,
                    PRIMARY KEY (user_id, date_text)
                );
                """
            )

    @staticmethod
    def _now_ts() -> int:
        return int(time.time())

    @staticmethod
    def _today_text() -> str:
        return time.strftime("%Y-%m-%d", time.localtime())

    def has_user(self, user_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM users WHERE user_id = ? LIMIT 1", (user_id,)
            ).fetchone()
        return row is not None

    def ensure_user(self, user_id: int, initial_length: float = 10.0) -> bool:
        if self.has_user(user_id):
            return False

        with self._connect() as connection:
            connection.execute(
                "INSERT INTO users(user_id, jj_length, last_active_at) VALUES (?, ?, ?)",
                (user_id, round(initial_length, 3), self._now_ts()),
            )
        return True

    def get_length(self, user_id: int) -> float:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT jj_length FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"user {user_id} not found")
        return round(float(row["jj_length"]), 3)

    def change_length(self, user_id: int, delta_cm: float) -> float:
        new_length = round(self.get_length(user_id) + delta_cm, 3)
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET jj_length = ?, last_active_at = ? WHERE user_id = ?",
                (new_length, self._now_ts(), user_id),
            )
        return new_length

    def touch_user(self, user_id: int, initial_length: float = 10.0) -> None:
        self.ensure_user(user_id, initial_length)
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET last_active_at = ? WHERE user_id = ?",
                (self._now_ts(), user_id),
            )

    def is_group_enabled(self, group_id: int, default_enabled: bool = False) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT enabled FROM groups WHERE group_id = ?", (group_id,)
            ).fetchone()
        return bool(row["enabled"]) if row is not None else default_enabled

    def set_group_enabled(self, group_id: int, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO groups(group_id, enabled) VALUES (?, ?) "
                "ON CONFLICT(group_id) DO UPDATE SET enabled = excluded.enabled",
                (group_id, int(enabled)),
            )

    def add_injection(self, user_id: int, volume_ml: float) -> float:
        today_text = self._today_text()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT volume_ml FROM injections WHERE user_id = ? AND date_text = ?",
                (user_id, today_text),
            ).fetchone()
            total_volume = round(
                volume_ml + (float(row["volume_ml"]) if row is not None else 0.0), 3
            )
            connection.execute(
                "INSERT INTO injections(user_id, date_text, volume_ml) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, date_text) DO UPDATE SET volume_ml = excluded.volume_ml",
                (user_id, today_text, total_volume),
            )
        return total_volume

    def get_today_injection(self, user_id: int) -> float:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT volume_ml FROM injections WHERE user_id = ? AND date_text = ?",
                (user_id, self._today_text()),
            ).fetchone()
        return round(float(row["volume_ml"]), 3) if row is not None else 0.0

    def get_injection_history(self, user_id: int) -> list[InjectionEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT date_text, volume_ml FROM injections WHERE user_id = ? ORDER BY date_text ASC",
                (user_id,),
            ).fetchall()
        return [
            InjectionEntry(date_text=str(row["date_text"]), volume_ml=float(row["volume_ml"]))
            for row in rows
        ]

    def punish_inactive_users(self, penalty_min: float, penalty_max: float, floor_length: float) -> None:
        cutoff_ts = self._now_ts() - 86400
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT user_id, jj_length FROM users WHERE last_active_at < ? AND jj_length > 0",
                (cutoff_ts,),
            ).fetchall()
            for row in rows:
                current_length = float(row["jj_length"])
                penalty = round(random.uniform(penalty_min, penalty_max), 3)
                new_length = round(max(0.0, floor_length, current_length - penalty), 3)
                connection.execute(
                    "UPDATE users SET jj_length = ? WHERE user_id = ?",
                    (new_length, int(row["user_id"])),
                )

    def get_rankings(self) -> list[RankEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT user_id, jj_length FROM users ORDER BY jj_length DESC, user_id ASC"
            ).fetchall()
        return [
            RankEntry(user_id=int(row["user_id"]), length_cm=float(row["jj_length"]))
            for row in rows
        ]
