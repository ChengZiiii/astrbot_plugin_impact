from __future__ import annotations

import time

from .impact_config import ImpactConfig
from .impact_service_gameplay import ImpactServiceGameplayMixin
from .impact_service_weekly import ImpactServiceWeeklyMixin
from .impact_store import ImpactStore


class ImpactService(ImpactServiceWeeklyMixin, ImpactServiceGameplayMixin):
    def __init__(self, store: ImpactStore, config: ImpactConfig) -> None:
        self._store = store
        self._config = config
        self._dj_cd_data: dict[str, float] = {}
        self._pk_cd_data: dict[str, float] = {}
        self._suo_cd_data: dict[str, float] = {}
        self._yinpa_cd_data: dict[str, float] = {}
        self._fuck_wife_cd_data: dict[str, float] = {}
        self._last_penalty_state_key = "last_inactive_penalty_day"
        self._weekly_title_map = {
            "length_top": {1: "长度第一"},
            "growth_top": {1: "涨得最多"},
            "pk_top": {1: "干得最猛"},
            "inject_out_top": {1: "输出最多"},
            "inject_in_top": {1: "最倒霉"},
            "worst_shrink": {1: "掉得最多"},
        }

    def run_daily_maintenance(self) -> None:
        current_day = time.strftime("%Y-%m-%d", time.localtime())
        last_penalty_day = self._store.get_state_value(self._last_penalty_state_key)
        if not self._config.enable_inactive_penalty or last_penalty_day == current_day:
            return
        self._store.punish_inactive_users(
            penalty_min=self._config.inactive_penalty_min,
            penalty_max=self._config.inactive_penalty_max,
            floor_length=self._config.inactive_penalty_floor,
        )
        self._store.set_state_value(self._last_penalty_state_key, current_day)
