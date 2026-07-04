from .impact_store_weekly_reports import ImpactStoreWeeklyReportsMixin, WEEKLY_REPORT_SCHEMA_SQL
from .impact_store_weekly_stats import ImpactStoreWeeklyStatsMixin, WEEKLY_STATS_SCHEMA_SQL

WEEKLY_SCHEMA_SQL = WEEKLY_STATS_SCHEMA_SQL + WEEKLY_REPORT_SCHEMA_SQL

__all__ = ["ImpactStoreWeeklyReportsMixin", "ImpactStoreWeeklyStatsMixin", "WEEKLY_SCHEMA_SQL"]
