from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .impact_store_basic import BASIC_SCHEMA_SQL, ImpactStoreBasicMixin, InjectionEntry, RankEntry
from .impact_store_rivalry import ImpactStoreRivalryMixin, RIVALRY_SCHEMA_SQL
from .impact_store_weekly import ImpactStoreWeeklyReportsMixin, ImpactStoreWeeklyStatsMixin, WEEKLY_SCHEMA_SQL


class ImpactStore(
    ImpactStoreWeeklyReportsMixin,
    ImpactStoreWeeklyStatsMixin,
    ImpactStoreRivalryMixin,
    ImpactStoreBasicMixin,
):
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
            connection.executescript(BASIC_SCHEMA_SQL + WEEKLY_SCHEMA_SQL + RIVALRY_SCHEMA_SQL)

    @staticmethod
    def _now_ts() -> int:
        return int(time.time())

    @staticmethod
    def _today_text() -> str:
        return time.strftime("%Y-%m-%d", time.localtime())


__all__ = ["ImpactStore", "InjectionEntry", "RankEntry"]
