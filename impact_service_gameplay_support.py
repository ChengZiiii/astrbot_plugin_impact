from __future__ import annotations

import random
import time
from typing import Sequence

from astrbot.api.event import AstrMessageEvent

from .impact_copy_bank import (
    COOLDOWN_DAJIAO,
    COOLDOWN_PK,
    COOLDOWN_SUO,
    COOLDOWN_YINPA,
    DAJIAO_GROWTH,
    DAJIAO_SHRINK,
    PK_LOSE_BOTH,
    PK_LOSE_BOTH_SAFE,
    PK_LOSE_NEGATIVE,
    PK_LOSE_NEGATIVE_SAFE,
    PK_WIN_NEGATIVE,
    PK_WIN_NEGATIVE_SAFE,
    PK_WIN_POSITIVE,
    PK_WIN_POSITIVE_SAFE,
    SUO_GROWTH,
    SUO_SHRINK,
    pick,
)
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

    def _cs(self, normal, safe):
        """Select copy pool based on safe_mode config.
        Returns safe pool when safe_mode is enabled, otherwise normal pool."""
        return safe if self._config.safe_mode else normal

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

    def _resolve_target_name(self, group_id: int | None, target_id: int, is_self: bool) -> str:
        """解析被作用方的展示名。

        - self → "你"（主句里已经以"你"开头的玩法用）
        - other → 群内 display_name；缺则按配置 fallback（user_id 或 "群友"）

        通用：被 SUO/MINE 等 need-target_name 的玩法共用。
        """
        if is_self:
            return "你"
        if group_id is not None:
            display_name = self._store.get_group_display_name(group_id, target_id)
            if display_name:
                return display_name
        return str(target_id) if self._config.nickname_fallback_to_user_id else "群友"

    def _record_group_query(self, group_id: int | None, sender_id: int) -> None:
        if group_id is None:
            return
        self._store.record_weekly_query(get_current_week_key(), group_id, sender_id, self._store.get_length(sender_id))

    @staticmethod
    def _compute_target_length_factor(
        target_length: float,
        min_length: float,
        max_length: float,
        factor_min: float,
        factor_max: float,
    ) -> float:
        """Linear mapping from target owner's jj_length to NTR success multiplier.

        Args:
            target_length: target owner's jj_length (cm).
            min_length: lower bound; below this clamps to factor_min.
            max_length: upper bound; above this clamps to factor_max.
            factor_min: multiplier when target_length == min_length.
            factor_max: multiplier when target_length == max_length.

        Returns:
            Multiplier in [factor_min, factor_max] (clamped). Returns factor_max
            when min_length == max_length to avoid division-by-zero.
        """
        if max_length == min_length:
            return factor_max
        clamped = max(min_length, min(max_length, target_length))
        ratio = (clamped - min_length) / (max_length - min_length)
        return factor_min + (factor_max - factor_min) * ratio

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

    def _format_single_change(self, growth_pool: tuple[str, ...], shrink_pool: tuple[str, ...], delta_cm: float, current_length: float, is_critical: bool, *, current_subject: str = "", **extra_fmt: object) -> str:
        """拼「涨/跌 + 现在多少」的标准句。

        `extra_fmt` 允许文案池携带额外占位符（例如挖矿的 {fluid} / {name}），
        既有调用方不传则行为完全不变。

        `current_subject`（keyword-only，默认空串）：为空时末尾用 `现在是Xcm。`，
        传非空时末尾用 `{current_subject}现在是Xcm。` —— 用于在 other 路径给当前
        长度补主语（避免与发送者混淆）。self 路径不传，行为与原版完全一致。
        """
        critical_prefix = "暴击。" if is_critical else ""
        jj = self._jj_name()
        suffix = f"{current_subject}现在是{current_length}cm。" if current_subject else f"现在是{current_length}cm。"
        if delta_cm >= 0:
            return critical_prefix + pick(growth_pool).format(delta=round(delta_cm, 3), jj=jj, **extra_fmt) + suffix
        return critical_prefix + pick(shrink_pool).format(delta=round(abs(delta_cm), 3), jj=jj, **extra_fmt) + suffix

    def _format_pk_result(self, is_sender_winner: bool, base_delta_cm: float, sender_delta_cm: float, target_delta_cm: float, is_critical: bool, sender_length: float = 0.0, target_length: float = 0.0) -> str:
        critical_prefix = "暴击。" if is_critical else ""
        jj = self._jj_name()
        if base_delta_cm >= 0:
            pool = self._cs(PK_WIN_POSITIVE, PK_WIN_POSITIVE_SAFE) if is_sender_winner else self._cs(PK_LOSE_NEGATIVE, PK_LOSE_NEGATIVE_SAFE)
        else:
            pool = self._cs(PK_WIN_NEGATIVE, PK_WIN_NEGATIVE_SAFE) if is_sender_winner else self._cs(PK_LOSE_BOTH, PK_LOSE_BOTH_SAFE)
        result = critical_prefix + pick(pool).format(delta=round(abs(sender_delta_cm), 3), jj=jj)
        if sender_length > 0 and target_length > 0:
            result += f"你{sender_length}cm，对方{target_length}cm。"
        return result

    def _format_pk_creation_reply(self, sender_created: bool, target_created: bool) -> str:
        if sender_created and target_created:
            return "你和对面都还没建档，已经顺手补上了。这把先不算，再发一次 pk。"
        if sender_created:
            return "你还没建档，已经先给你补上了。这把先不算，再发一次 pk。"
        return "对面还没建档，已经先给 TA 补上了。这把先不算，再发一次 pk。"

    @staticmethod
    def _cooldown_text(cache: dict[str, float], key: str, cooldown_seconds: int, cooldown_pool: tuple[str, ...], **fmt_kwargs: str | float) -> str | None:
        last_ts = cache.get(key)
        if last_ts is None:
            return None
        remaining = cooldown_seconds - (time.time() - last_ts)
        if remaining <= 0:
            return None
        return pick(cooldown_pool).format(cd=round(remaining, 3), **fmt_kwargs)
