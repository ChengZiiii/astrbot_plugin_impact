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
        self._last_penalty_state_key = "last_inactive_penalty_day"
        self._weekly_title_map = {
            "length_top": {1: "本周牛王", 2: "本周二当家", 3: "本周牛界名流"},
            "growth_top": {1: "本周最强发育", 2: "成长型选手", 3: "潜力股"},
            "pk_top": {1: "本周决斗恶霸", 2: "本周单挑王", 3: "群内约架冠军"},
            "inject_out_top": {1: "本周银趴之神", 2: "输出核心", 3: "注入达人"},
            "inject_in_top": {1: "本周人形输液架", 2: "重点关照对象", 3: "高危受害者"},
            "worst_shrink": {1: "本周最惨选手"},
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
