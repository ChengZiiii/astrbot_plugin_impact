from __future__ import annotations

import random
import time

from astrbot.api.event import AstrMessageEvent

from .impact_models import ActionMediaRequest
from .impact_time import get_current_week_key


class ImpactServiceGameplaySupportMixin:
    @staticmethod
    def is_admin(event: AstrMessageEvent) -> bool:
        try:
            return bool(event.is_admin())
        except Exception:
            return False

    def is_sender_admin(self, event: AstrMessageEvent) -> bool:
        sender_id = str(event.get_sender_id())
        if sender_id in self._config.admin_list:
            return True
        if self._config.admin_only_toggle:
            return self.is_admin(event)
        return True

    def _random_delta(self) -> tuple[float, bool]:
        base_value = random.random()
        if base_value > self._config.lucky_growth_probability:
            delta_cm = random.uniform(self._config.random_growth_min, self._config.random_growth_max)
            is_critical = False
        else:
            delta_cm = random.uniform(self._config.lucky_growth_min, self._config.lucky_growth_max)
            is_critical = True
        return round(delta_cm, 3), is_critical

    def _jj_name(self) -> str:
        return random.choice(self._config.jj_names)

    def _record_group_query(self, group_id: int | None, sender_id: int) -> None:
        if group_id is None:
            return
        self._store.record_weekly_query(get_current_week_key(), group_id, sender_id, self._store.get_length(sender_id))

    def _record_group_length_change(self, group_id: int | None, user_id: int, delta_cm: float, current_length: float, action_column: str | None, increment_total_action: bool) -> None:
        if group_id is None:
            return
        self._store.record_weekly_single_length_change(get_current_week_key(), group_id, user_id, delta_cm, current_length, action_column, increment_total_action)

    def _record_group_pk(self, group_id: int | None, winner_id: int, loser_id: int, winner_delta_cm: float, loser_delta_cm: float, winner_current_length: float, loser_current_length: float) -> None:
        if group_id is None:
            return
        week_key = get_current_week_key()
        self._store.record_weekly_pk_result(week_key, group_id, winner_id, loser_id, winner_delta_cm, loser_delta_cm, winner_current_length, loser_current_length)
        self._store.record_rivalry_pk(week_key, group_id, winner_id, loser_id)

    @staticmethod
    def _build_media_request(action: str, mode: str, negative: bool, sender_id: int | None, target_id: int | None) -> ActionMediaRequest | None:
        if mode == "none":
            return None
        return ActionMediaRequest(action=action, mode=mode, negative=negative, sender_id=sender_id, target_id=target_id)

    def _format_single_change(self, prefix_text: str, subject_text: str, delta_cm: float, current_length: float, is_critical: bool) -> str:
        critical_prefix = "暴击。" if is_critical else ""
        if delta_cm >= 0:
            return f"{critical_prefix}{prefix_text}，{subject_text}涨了{round(delta_cm, 3)}cm，今天还算没白忙。现在是{current_length}cm。"
        return f"{critical_prefix}{prefix_text}，{subject_text}掉了{round(abs(delta_cm), 3)}cm，这把多少有点丢人。现在只剩{current_length}cm。"

    def _format_pk_result(self, is_sender_winner: bool, base_delta_cm: float, sender_delta_cm: float, target_delta_cm: float, is_critical: bool) -> str:
        critical_prefix = "暴击。" if is_critical else ""
        if base_delta_cm >= 0:
            if is_sender_winner:
                return f"{critical_prefix}这把你赢了，你的{self._jj_name()}加了{round(sender_delta_cm, 3)}cm，对面掉了{round(abs(target_delta_cm), 3)}cm。场面算你撑住了。"
            return f"{critical_prefix}这把你输了，你的{self._jj_name()}掉了{round(abs(sender_delta_cm), 3)}cm，对面反而加了{round(target_delta_cm, 3)}cm。脸基本是送出去了。"
        if is_sender_winner:
            return f"{critical_prefix}这把虽然是你赢，但状态也够烂。你的{self._jj_name()}掉了{round(abs(sender_delta_cm), 3)}cm，对面也跟着掉了{round(abs(target_delta_cm), 3)}cm。"
        return f"{critical_prefix}这把你没赢，场面也没多体面。你的{self._jj_name()}掉了{round(abs(sender_delta_cm), 3)}cm，对面也只掉了{round(abs(target_delta_cm), 3)}cm。"

    def _format_pk_creation_reply(self, sender_created: bool, target_created: bool) -> str:
        if sender_created and target_created:
            return f"你和对面都还没建档，已经顺手补上了。这把先不算，再发一次 pk。"
        if sender_created:
            return f"你还没建档，已经先给你补上了。这把先不算，再发一次 pk。"
        return f"对面还没建档，已经先给 TA 补上了。这把先不算，再发一次 pk。"

    @staticmethod
    def _cooldown_text(cache: dict[str, float], key: str, cooldown_seconds: int, prefix: str) -> str | None:
        last_ts = cache.get(key)
        if last_ts is None:
            return None
        remaining = cooldown_seconds - (time.time() - last_ts)
        if remaining <= 0:
            return None
        return f"{prefix}，{round(remaining, 3)}秒后再来。"
