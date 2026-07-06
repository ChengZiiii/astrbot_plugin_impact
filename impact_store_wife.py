from __future__ import annotations


WIFE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wife_sex_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_uid TEXT NOT NULL,
    group_id TEXT NOT NULL,
    target_wid TEXT NOT NULL,
    target_owner_uid TEXT NOT NULL,
    is_ntr INTEGER NOT NULL,
    success INTEGER NOT NULL,
    volume_ml REAL DEFAULT 0,
    satisfaction INTEGER DEFAULT 0,
    ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wsr_sender ON wife_sex_records(sender_uid, ts);
CREATE INDEX IF NOT EXISTS idx_wsr_wid ON wife_sex_records(target_wid, group_id);

CREATE TABLE IF NOT EXISTS wife_sex_stats (
    group_id TEXT NOT NULL,
    wid TEXT NOT NULL,
    total_count INTEGER DEFAULT 0,
    total_volume REAL DEFAULT 0,
    sat_sum INTEGER DEFAULT 0,
    sat_count INTEGER DEFAULT 0,
    last_actor_uid TEXT DEFAULT '',
    last_ts INTEGER DEFAULT 0,
    PRIMARY KEY (group_id, wid)
);

CREATE TABLE IF NOT EXISTS wife_sex_daily (
    user_id TEXT NOT NULL,
    date_text TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date_text)
);
"""


class ImpactStoreWifeMixin:
    def record_wife_sex(
        self,
        sender_uid: str,
        group_id: str,
        target_wid: str,
        target_owner_uid: str,
        *,
        is_ntr: bool,
        success: bool,
        volume_ml: float = 0.0,
        satisfaction: int = 0,
        ts: int | None = None,
    ) -> None:
        ts = ts if ts is not None else self._now_ts()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO wife_sex_records"
                "(sender_uid, group_id, target_wid, target_owner_uid, is_ntr, success, volume_ml, satisfaction, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sender_uid, group_id, target_wid, target_owner_uid, int(is_ntr), int(success), volume_ml, satisfaction, ts),
            )
            connection.execute(
                "INSERT INTO wife_sex_stats(group_id, wid, total_count, total_volume, sat_sum, sat_count, last_actor_uid, last_ts) "
                "VALUES (?, ?, 1, ?, ?, ?, ?, ?) "
                "ON CONFLICT(group_id, wid) DO UPDATE SET "
                "total_count = total_count + 1, "
                "total_volume = total_volume + excluded.total_volume, "
                "sat_sum = sat_sum + excluded.sat_sum, "
                "sat_count = sat_count + excluded.sat_count, "
                "last_actor_uid = excluded.last_actor_uid, "
                "last_ts = excluded.last_ts",
                (group_id, target_wid, volume_ml, satisfaction, 1, sender_uid, ts),
            )

    def get_wife_stats(self, group_id: str, wid: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM wife_sex_stats WHERE group_id = ? AND wid = ?",
                (group_id, wid),
            ).fetchone()
        if row is None:
            return None
        return {
            "total_count": row["total_count"],
            "total_volume": row["total_volume"],
            "sat_sum": row["sat_sum"],
            "sat_count": row["sat_count"],
            "last_actor_uid": row["last_actor_uid"],
            "last_ts": row["last_ts"],
        }

    def get_wife_daily_injection(self, group_id: str, wid: str) -> tuple[float, int]:
        today = self._today_text()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(volume_ml), 0) AS vol, COUNT(*) AS cnt "
                "FROM wife_sex_records WHERE group_id = ? AND target_wid = ? AND success = 1 "
                "AND date(ts, 'unixepoch', 'localtime') = ?",
                (group_id, wid, today),
            ).fetchone()
        return (float(row["vol"]), int(row["cnt"]))

    def get_daily_fuck_wife_count(self, uid: str) -> int:
        today = self._today_text()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT count FROM wife_sex_daily WHERE user_id = ? AND date_text = ?",
                (uid, today),
            ).fetchone()
        return 0 if row is None else int(row["count"])

    def incr_daily_fuck_wife_count(self, uid: str) -> None:
        today = self._today_text()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO wife_sex_daily(user_id, date_text, count) VALUES (?, ?, 1) "
                "ON CONFLICT(user_id, date_text) DO UPDATE SET count = count + 1",
                (uid, today),
            )

    def was_ntrd_by(self, sender_uid: str, target_owner_uid: str) -> bool:
        """Check if target_owner has previously NTR'd sender (i.e. sender was a victim)."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM wife_sex_records "
                "WHERE sender_uid = ? AND target_owner_uid = ? AND is_ntr = 1 AND success = 1 "
                "LIMIT 1",
                (target_owner_uid, sender_uid),
            ).fetchone()
        return row is not None

    def get_same_target_fuck_streak(self, sender_uid: str, target_owner_uid: str) -> int:
        """Count consecutive most recent attempts against the same target owner (any outcome)."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT target_owner_uid FROM wife_sex_records "
                "WHERE sender_uid = ? ORDER BY ts DESC",
                (sender_uid,),
            ).fetchall()
        streak = 0
        for row in rows:
            if row["target_owner_uid"] == target_owner_uid:
                streak += 1
            else:
                break
        return streak
