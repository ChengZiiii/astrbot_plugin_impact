from __future__ import annotations

import sqlite3

from .impact_models import WeeklyResultEntry


WEEKLY_REPORT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS weekly_results (
    week_key TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    rank_no INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    metric_value REAL NOT NULL,
    title_text TEXT,
    generated_at INTEGER NOT NULL,
    PRIMARY KEY (week_key, group_id, category, rank_no)
);

CREATE TABLE IF NOT EXISTS weekly_reports (
    week_key TEXT NOT NULL,
    group_id INTEGER NOT NULL,
    report_text TEXT NOT NULL,
    generated_at INTEGER NOT NULL,
    settled_flag INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (week_key, group_id)
);

CREATE INDEX IF NOT EXISTS idx_weekly_results_group_week_category
ON weekly_results (group_id, week_key, category);
"""


class ImpactStoreWeeklyReportsMixin:
    def refresh_weekly_length_snapshots(self, week_key: str, group_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE weekly_stats SET current_length_snapshot = ("
                "SELECT jj_length FROM users WHERE users.user_id = weekly_stats.user_id"
                ") WHERE week_key = ? AND group_id = ?",
                (week_key, group_id),
            )

    def save_weekly_settlement(
        self,
        week_key: str,
        group_id: int,
        results: list[WeeklyResultEntry],
        report_text: str,
    ) -> None:
        now_ts = self._now_ts()
        with self._connect() as connection:
            for result in results:
                connection.execute(
                    "INSERT OR REPLACE INTO weekly_results(week_key, group_id, category, rank_no, user_id, metric_value, title_text, display_name_snapshot, generated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        week_key,
                        group_id,
                        result.category,
                        result.rank_no,
                        result.user_id,
                        result.metric_value,
                        result.title_text,
                        result.display_name_snapshot,
                        now_ts,
                    ),
                )
            connection.execute(
                "INSERT OR REPLACE INTO weekly_reports(week_key, group_id, report_text, generated_at, settled_flag) VALUES (?, ?, ?, ?, 1)",
                (week_key, group_id, report_text, now_ts),
            )

    def get_weekly_results(self, week_key: str, group_id: int) -> list[sqlite3.Row]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM weekly_results WHERE week_key = ? AND group_id = ? ORDER BY category ASC, rank_no ASC",
                (week_key, group_id),
            ).fetchall()
        return rows

    def get_weekly_report(self, week_key: str, group_id: int) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT report_text FROM weekly_reports WHERE week_key = ? AND group_id = ?",
                (week_key, group_id),
            ).fetchone()
        return None if row is None else str(row["report_text"])

    def get_latest_settled_report(self, group_id: int) -> tuple[str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT week_key, report_text FROM weekly_reports WHERE group_id = ? AND settled_flag = 1 ORDER BY week_key DESC LIMIT 1",
                (group_id,),
            ).fetchone()
        if row is None:
            return None
        return str(row["week_key"]), str(row["report_text"])
