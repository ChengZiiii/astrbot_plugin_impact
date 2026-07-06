from __future__ import annotations

import random
import time

from .impact_copy_bank import (
    COOLDOWN_DAJIAO,
    COOLDOWN_FUCK_WIFE,
    COOLDOWN_PK,
    COOLDOWN_SUO,
    COOLDOWN_YINPA,
    DAJIAO_GROWTH,
    DAJIAO_SHRINK,
    INJECTION_HISTORY,
    INJECTION_TODAY,
    NEW_USER_REPLY,
    PK_NO_TARGET,
    PK_SELF_TARGET,
    QUERY_SELF_HIGH,
    QUERY_SELF_LOW,
    QUERY_SELF_MID,
    QUERY_TARGET_HIGH,
    QUERY_TARGET_LOW,
    QUERY_TARGET_MID,
    SUO_GROWTH,
    SUO_SHRINK,
    TOGGLE_ADMIN_ONLY,
    pick,
)

from astrbot.api.event import AstrMessageEvent

from .impact_models import FuckWifeResult, PlainReply
from .impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
from .impact_time import get_current_week_key


class ImpactServiceGameplayMixin(ImpactServiceGameplaySupportMixin):
    def handle_dajiao(self, group_enabled: bool, sender_id: int, group_id: int | None = None) -> PlainReply:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        if not self._store.has_user(sender_id):
            self._store.ensure_user(sender_id, self._config.user_initial_length)
            return PlainReply(pick(NEW_USER_REPLY).format(length=self._config.user_initial_length), mention_sender=True)
        wait_text = self._cooldown_text(self._dj_cd_data, str(sender_id), self._config.dj_cd_time, COOLDOWN_DAJIAO, jj=self._jj_name())
        if wait_text is not None:
            return PlainReply(wait_text, mention_sender=True)
        self._dj_cd_data[str(sender_id)] = time.time()
        delta_cm, is_critical = self._random_delta()
        current_length = self._store.change_length(sender_id, delta_cm)
        self._record_group_length_change(group_id, sender_id, delta_cm, current_length, "dajiao_count", True)
        return PlainReply(self._format_single_change(DAJIAO_GROWTH, DAJIAO_SHRINK, delta_cm, current_length, is_critical), media_request=self._build_media_request("dajiao", self._config.dajiao_media_mode, delta_cm < 0, sender_id, None), mention_sender=True)

    def handle_suo(self, group_enabled: bool, sender_id: int, at_id: str | None, group_id: int | None = None) -> PlainReply:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        if at_id is not None and not self._config.suo_allow_target_other:
            return PlainReply("当前配置不让你对别人下手。", mention_sender=True)
        target_id = sender_id if at_id is None else int(at_id)
        if not self._store.has_user(target_id):
            self._store.ensure_user(target_id, self._config.user_initial_length)
            prefix = "你" if target_id == sender_id else "TA"
            return PlainReply(f"{prefix}还没建档，先补个 {self._config.user_initial_length}cm 的起步款。", mention_sender=True)
        wait_text = self._cooldown_text(self._suo_cd_data, str(sender_id), self._config.suo_cd_time, COOLDOWN_SUO)
        if wait_text is not None:
            return PlainReply(wait_text, mention_sender=True)
        self._suo_cd_data[str(sender_id)] = time.time()
        delta_cm, is_critical = self._random_delta()
        current_length = self._store.change_length(target_id, delta_cm)
        if target_id == sender_id:
            self._record_group_length_change(group_id, sender_id, delta_cm, current_length, "suo_count", True)
        else:
            self._record_group_length_change(group_id, sender_id, 0.0, self._store.get_length(sender_id), "suo_count", True)
            self._record_group_length_change(group_id, target_id, delta_cm, current_length, None, False)
        return PlainReply(self._format_single_change(SUO_GROWTH, SUO_SHRINK, delta_cm, current_length, is_critical), media_request=self._build_media_request("suo", self._config.suo_media_mode, delta_cm < 0, sender_id, target_id), mention_sender=True)

    def handle_query(self, group_enabled: bool, sender_id: int, at_id: str | None, group_id: int | None = None) -> PlainReply:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        target_id = sender_id if at_id is None else int(at_id)
        if not self._store.has_user(target_id):
            self._store.ensure_user(target_id, self._config.user_initial_length)
            prefix = "你" if target_id == sender_id else "TA"
            return PlainReply(f"{prefix}还没建档，先补个 {self._config.user_initial_length}cm 的起步款。", mention_sender=True)
        self._record_group_query(group_id, sender_id)
        current_length = self._store.get_length(target_id)
        is_self = target_id == sender_id
        if current_length < 12:
            query_text = pick(QUERY_SELF_LOW if is_self else QUERY_TARGET_LOW)
        elif current_length < 18:
            query_text = pick(QUERY_SELF_MID if is_self else QUERY_TARGET_MID)
        else:
            query_text = pick(QUERY_SELF_HIGH if is_self else QUERY_TARGET_HIGH)
        display_text = query_text.format(length=current_length)
        mention_sender = is_self
        return PlainReply(display_text, mention_sender=mention_sender)

    def handle_pk(self, group_enabled: bool, sender_id: int, at_id: str | None, group_id: int | None = None) -> PlainReply:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        if at_id is None and self._config.pk_require_at:
            return PlainReply(pick(PK_NO_TARGET))
        if at_id is None:
            return PlainReply(pick(PK_NO_TARGET))
        target_id = int(at_id)
        if target_id == sender_id:
            return PlainReply(pick(PK_SELF_TARGET))
        sender_created = self._store.ensure_user(sender_id, self._config.user_initial_length)
        target_created = self._store.ensure_user(target_id, self._config.user_initial_length)
        if sender_created or target_created:
            return PlainReply(self._format_pk_creation_reply(sender_created, target_created))
        wait_text = self._cooldown_text(self._pk_cd_data, str(sender_id), self._config.pk_cd_time, COOLDOWN_PK)
        if wait_text is not None:
            return PlainReply(wait_text)
        self._pk_cd_data[str(sender_id)] = time.time()
        delta_cm, is_critical = self._random_delta()
        abs_delta = abs(delta_cm)
        winner_gain = round(abs_delta * self._config.pk_winner_gain_ratio, 3)
        winner_delta = winner_gain if delta_cm >= 0 else -winner_gain
        loser_delta = -abs_delta if delta_cm >= 0 else -abs_delta
        if random.random() > 0.5:
            sender_length = self._store.change_length(sender_id, winner_delta)
            target_length = self._store.change_length(target_id, loser_delta)
            self._record_group_pk(group_id, sender_id, target_id, winner_delta, loser_delta, sender_length, target_length)
            return PlainReply(self._format_pk_result(True, delta_cm, winner_delta, loser_delta, is_critical), media_request=self._build_media_request("pk", self._config.pk_media_mode, delta_cm < 0, sender_id, target_id))
        sender_length = self._store.change_length(sender_id, loser_delta)
        target_length = self._store.change_length(target_id, winner_delta)
        self._record_group_pk(group_id, target_id, sender_id, winner_delta, loser_delta, target_length, sender_length)
        return PlainReply(self._format_pk_result(False, delta_cm, loser_delta, winner_delta, is_critical), media_request=self._build_media_request("pk", self._config.pk_media_mode, delta_cm < 0, sender_id, target_id))

    def handle_toggle(self, group_id: int, normalized: str, event: AstrMessageEvent) -> PlainReply:
        if not self.is_sender_admin(event):
            return PlainReply(pick(TOGGLE_ADMIN_ONLY))
        enabled = "开启" in normalized or "开始" in normalized
        self._store.set_group_enabled(group_id, enabled)
        from .impact_copy_bank import TOGGLE_ON, TOGGLE_OFF
        return PlainReply(pick(TOGGLE_ON) if enabled else pick(TOGGLE_OFF))

    def handle_injection(self, group_enabled: bool, sender_id: int, normalized: str, at_id: str | None, group_id: int | None = None) -> PlainReply | tuple[dict[str, float], str]:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        target_id = sender_id if at_id is None else int(at_id)
        object_name = "您" if target_id == sender_id else "该用户"
        self._record_group_query(group_id, sender_id)
        if "历史" not in normalized and "全部" not in normalized:
            return PlainReply(pick(INJECTION_TODAY).format(object=object_name, volume=self._store.get_today_injection(target_id)), mention_sender=True)
        history = self._store.get_injection_history(target_id)
        total_volume = round(sum(item.volume_ml for item in history), 3)
        if len(history) < 2:
            return PlainReply(pick(INJECTION_HISTORY).format(object=object_name, volume=total_volume), mention_sender=True)
        return ({item.date_text: item.volume_ml for item in history}, pick(INJECTION_HISTORY).format(object=object_name, volume=total_volume))

    def can_yinpa(self, group_enabled: bool, sender_id: int) -> PlainReply | None:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        wait_text = self._cooldown_text(self._yinpa_cd_data, str(sender_id), self._config.fuck_cd_time, COOLDOWN_YINPA)
        if wait_text is not None:
            return PlainReply(wait_text)
        return None

    def finish_yinpa(self, sender_id: int, target_id: int, group_id: int | None = None) -> float:
        self._yinpa_cd_data[str(sender_id)] = time.time()
        injected_volume = round(random.uniform(self._config.yinpa_volume_min, self._config.yinpa_volume_max), 3)
        self._store.add_injection(target_id, injected_volume)
        self._store.touch_user(sender_id, self._config.user_initial_length)
        self._store.touch_user(target_id, self._config.user_initial_length)
        if group_id is not None:
            week_key = get_current_week_key()
            self._store.record_weekly_yinpa(week_key, group_id, sender_id, target_id, injected_volume, self._store.get_length(sender_id), self._store.get_length(target_id))
            self._store.record_rivalry_yinpa(week_key, group_id, sender_id, target_id)
        return injected_volume

    def get_today_injection(self, target_id: int) -> float:
        return self._store.get_today_injection(target_id)

    def handle_fuck_wife(
        self,
        group_enabled: bool,
        group_id: str,
        sender_uid: str,
        target_uid: str | None,
        normalized: str,
        roll_seed: float | None = None,
        index: int | None = None,
    ) -> FuckWifeResult:
        if not group_enabled:
            return FuckWifeResult(ok=False, reason="not_enabled")

        # Lazy import animewifexI facade
        from data.plugins.astrbot_plugin_animewifexI.app.interop import get_wife_interop

        interop = get_wife_interop()

        # Cooldown check
        wait_text = self._cooldown_text(
            self._fuck_wife_cd_data, sender_uid, self._config.fuck_wife_cd_time, COOLDOWN_FUCK_WIFE
        )
        if wait_text is not None:
            return FuckWifeResult(ok=False, reason="cooldown")

        # Daily limit check
        daily_count = self._store.get_daily_fuck_wife_count(sender_uid)
        if daily_count >= self._config.fuck_wife_daily_limit:
            return FuckWifeResult(ok=False, reason="daily_limit")

        is_ntr = target_uid is not None and target_uid != sender_uid

        if not is_ntr:
            # Own wife path — always success
            import asyncio

            peek_coro = interop.peek_wife(group_id, sender_uid, index=index)
            peek_result: dict = asyncio.run(peek_coro)
            if not peek_result:
                return FuckWifeResult(ok=False, reason="no_wife")

            wid = peek_result["wid"]
            wife_name = peek_result.get("name", "")
            intimacy_gain = self._config.fuck_wife_intimacy_gain_self

            record_coro = interop.record_sex_act(group_id, wid, sender_uid, False, intimacy_gain)
            record_result: dict = asyncio.run(record_coro)
            if not record_result.get("ok"):
                return FuckWifeResult(ok=False, reason="record_failed")

            volume_ml = round(random.uniform(self._config.fuck_wife_volume_min, self._config.fuck_wife_volume_max), 3)

            self._fuck_wife_cd_data[sender_uid] = time.time()
            self._store.incr_daily_fuck_wife_count(sender_uid)
            self._store.record_wife_sex(
                sender_uid, group_id, wid, sender_uid,
                is_ntr=False, success=True,
                volume_ml=volume_ml, satisfaction=100,
            )

            return FuckWifeResult(
                ok=True, success=True, is_ntr=False,
                wife_wid=wid, wife_name=wife_name,
                intimacy_gain=intimacy_gain,
                new_intimacy=record_result.get("new_intimacy", 0),
                volume_ml=volume_ml,
                satisfaction=100,
            )

        # NTR path
        import asyncio

        peek_coro = interop.peek_wife(group_id, target_uid, index=index)
        peek_result: dict = asyncio.run(peek_coro)
        if not peek_result:
            return FuckWifeResult(ok=False, reason="target_no_wife")

        wid = peek_result["wid"]
        wife_name = peek_result.get("name", "")

        resistance_coro = interop.compute_ntr_resistance(group_id, wid)
        resistance_result: dict = asyncio.run(resistance_coro)
        if not resistance_result:
            return FuckWifeResult(ok=False, reason="target_no_wife")

        if resistance_result.get("locked"):
            return FuckWifeResult(ok=False, reason="target_locked", resistance_flags=resistance_result)

        # Probability pipeline
        base = self._config.fuck_wife_base_possibility

        # Charm factor: jj_length tiers
        try:
            sender_length = self._store.get_length(int(sender_uid))
        except (ValueError, TypeError):
            sender_length = 0.0
        thresholds = self._config.fuck_wife_charm_thresholds
        charm = 1.0
        if len(thresholds) >= 3 and sender_length >= thresholds[2]:
            charm = 1.5
        elif len(thresholds) >= 2 and sender_length >= thresholds[1]:
            charm = 1.25
        elif len(thresholds) >= 1 and sender_length >= thresholds[0]:
            charm = 1.1

        # Revenge factor: was NTR'd by target owner before
        revenge = self._config.fuck_wife_revenge_multiplier if self._store.was_ntrd_by(sender_uid, target_uid) else 1.0

        # Streak factor: same-target decay 0.7^streak
        streak_count = self._store.get_same_target_fuck_streak(sender_uid, target_uid)
        streak = 0.7 ** streak_count if streak_count > 0 else 1.0

        resistance = resistance_result.get("resistance", 1.0)
        prob = min(1.0, base * charm * revenge * streak * resistance)

        roll = roll_seed if roll_seed is not None else random.random()
        success = roll < prob

        intimacy_gain = self._config.fuck_wife_intimacy_gain_ntr if success else 0
        new_intimacy = 0

        if success:
            record_coro = interop.record_sex_act(group_id, wid, sender_uid, True, intimacy_gain)
            record_result: dict = asyncio.run(record_coro)
            if not record_result.get("ok"):
                return FuckWifeResult(ok=False, reason="record_failed", resistance_flags=resistance_result)
            new_intimacy = record_result.get("new_intimacy", 0)

        volume_ml = round(random.uniform(self._config.fuck_wife_volume_min, self._config.fuck_wife_volume_max), 3) if success else 0.0

        self._fuck_wife_cd_data[sender_uid] = time.time()
        self._store.incr_daily_fuck_wife_count(sender_uid)
        self._store.record_wife_sex(
            sender_uid, group_id, wid, target_uid,
            is_ntr=True, success=success,
            volume_ml=volume_ml, satisfaction=80 if success else 0,
        )

        return FuckWifeResult(
            ok=True, success=success, is_ntr=True,
            wife_wid=wid, wife_name=wife_name,
            intimacy_gain=intimacy_gain,
            new_intimacy=new_intimacy,
            volume_ml=volume_ml,
            satisfaction=80 if success else 0,
            resistance_flags=resistance_result,
        )
