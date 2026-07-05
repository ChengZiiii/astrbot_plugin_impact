from __future__ import annotations

import random
import time

from .impact_copy_bank import QUERY_SELF_HIGH, QUERY_SELF_LOW, QUERY_SELF_MID, QUERY_TARGET_HIGH, QUERY_TARGET_LOW, QUERY_TARGET_MID, pick

from astrbot.api.event import AstrMessageEvent

from .impact_models import PlainReply
from .impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
from .impact_time import get_current_week_key


class ImpactServiceGameplayMixin(ImpactServiceGameplaySupportMixin):
    def handle_dajiao(self, group_enabled: bool, sender_id: int, group_id: int | None = None) -> PlainReply:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        if not self._store.has_user(sender_id):
            self._store.ensure_user(sender_id, self._config.user_initial_length)
            return PlainReply(f"你还没建档，先给你补个 {self._config.user_initial_length}cm 的起步款。", mention_sender=True)
        wait_text = self._cooldown_text(self._dj_cd_data, str(sender_id), self._config.dj_cd_time, "刚打完，先缓缓")
        if wait_text is not None:
            return PlainReply(wait_text, mention_sender=True)
        self._dj_cd_data[str(sender_id)] = time.time()
        delta_cm, is_critical = self._random_delta()
        current_length = self._store.change_length(sender_id, delta_cm)
        self._record_group_length_change(group_id, sender_id, delta_cm, current_length, "dajiao_count", True)
        return PlainReply(self._format_single_change("这把打完了", f"你的{self._jj_name()}", delta_cm, current_length, is_critical), media_request=self._build_media_request("dajiao", self._config.dajiao_media_mode, delta_cm < 0, sender_id, None), mention_sender=True)

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
        wait_text = self._cooldown_text(self._suo_cd_data, str(sender_id), self._config.suo_cd_time, "你刚嗦过，先歇会")
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
        prefix = "你的" if target_id == sender_id else "对方的"
        return PlainReply(self._format_single_change("这口下去", f"{prefix}{self._jj_name()}", delta_cm, current_length, is_critical), media_request=self._build_media_request("suo", self._config.suo_media_mode, delta_cm < 0, sender_id, target_id), mention_sender=True)

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
            return PlainReply("pk 得先 @ 一个目标。")
        if at_id is None:
            return PlainReply("现在没可打的目标。")
        target_id = int(at_id)
        if target_id == sender_id:
            return PlainReply("你打自己是想图什么。")
        sender_created = self._store.ensure_user(sender_id, self._config.user_initial_length)
        target_created = self._store.ensure_user(target_id, self._config.user_initial_length)
        if sender_created or target_created:
            return PlainReply(self._format_pk_creation_reply(sender_created, target_created))
        wait_text = self._cooldown_text(self._pk_cd_data, str(sender_id), self._config.pk_cd_time, "刚打完一场，先冷静")
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
            return PlainReply("这开关得管理员或群主来动。")
        enabled = "开启" in normalized or "开始" in normalized
        self._store.set_group_enabled(group_id, enabled)
        return PlainReply("已经开了，想玩就继续。" if enabled else "已经关了，先到这里。")

    def handle_injection(self, group_enabled: bool, sender_id: int, normalized: str, at_id: str | None, group_id: int | None = None) -> PlainReply | tuple[dict[str, float], str]:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        target_id = sender_id if at_id is None else int(at_id)
        object_name = "您" if target_id == sender_id else "该用户"
        self._record_group_query(group_id, sender_id)
        if "历史" not in normalized and "全部" not in normalized:
            return PlainReply(f"{object_name}当日总被注射量为{self._store.get_today_injection(target_id)}ml", mention_sender=True)
        history = self._store.get_injection_history(target_id)
        total_volume = round(sum(item.volume_ml for item in history), 3)
        if len(history) < 2:
            return PlainReply(f"{object_name}历史总被注射量为{total_volume}ml", mention_sender=True)
        return ({item.date_text: item.volume_ml for item in history}, f"{object_name}历史总被注射量为{total_volume}ml")

    def can_yinpa(self, group_enabled: bool, sender_id: int) -> PlainReply | None:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        wait_text = self._cooldown_text(self._yinpa_cd_data, str(sender_id), self._config.fuck_cd_time, "你这边刚结束，先缓一缓")
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
