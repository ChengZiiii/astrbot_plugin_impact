from __future__ import annotations

from datetime import datetime, timedelta


def get_week_key_by_timestamp(ts: int) -> str:
    dt_value = datetime.fromtimestamp(ts)
    iso_year, iso_week, _ = dt_value.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def get_current_week_key() -> str:
    return get_week_key_by_timestamp(int(datetime.now().timestamp()))


def get_previous_week_key(week_key: str) -> str:
    year_text, week_text = week_key.split("-W", maxsplit=1)
    dt_value = datetime.fromisocalendar(int(year_text), int(week_text), 1) - timedelta(days=7)
    iso_year, iso_week, _ = dt_value.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def get_current_month_key() -> str:
    return datetime.now().strftime("%Y-%m")
