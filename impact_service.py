from __future__ import annotations

import random
import time

from astrbot.api.event import AstrMessageEvent

from .impact_config import ImpactConfig
from .impact_models import ActionMediaRequest, PlainReply
from .impact_store import ImpactStore

class ImpactService:
    def __init__(self, store: ImpactStore, config: ImpactConfig) -> None:
        self._store = store
        self._config = config
        self._dj_cd_data: dict[str, float] = {}
        self._pk_cd_data: dict[str, float] = {}
        self._suo_cd_data: dict[str, float] = {}
        self._yinpa_cd_data: dict[str, float] = {}
        self._last_penalty_day = ""

    def run_daily_maintenance(self) -> None:
        current_day = time.strftime("%Y-%m-%d", time.localtime())
        if not self._config.enable_inactive_penalty or self._last_penalty_day == current_day:
            return
        self._store.punish_inactive_users(
            penalty_min=self._config.inactive_penalty_min,
            penalty_max=self._config.inactive_penalty_max,
            floor_length=self._config.inactive_penalty_floor,
        )
        self._last_penalty_day = current_day

    def handle_dajiao(self, group_id: int, sender_id: int) -> PlainReply:
        if not self._store.is_group_enabled(group_id, self._config.default_group_enabled):
            return PlainReply(self._config.not_enabled_reply)
        if not self._store.has_user(sender_id):
            self._store.ensure_user(sender_id, self._config.user_initial_length)
            return PlainReply(f"你还没有创建{self._jj_name()}喵, 咱帮你创建了喵, 目前长度是{self._config.user_initial_length}cm喵")
        wait_text = self._cooldown_text(self._dj_cd_data, str(sender_id), self._config.dj_cd_time, "你已经打不动了喵")
        if wait_text is not None:
            return PlainReply(wait_text)
        self._dj_cd_data[str(sender_id)] = time.time()
        delta_cm = self._random_delta()
        current_length = self._store.change_length(sender_id, delta_cm)
        return PlainReply(
            self._format_single_change("打胶结束喵", f"你的{self._jj_name()}", delta_cm, current_length),
            media_request=self._build_media_request("dajiao", self._config.dajiao_media_mode, delta_cm < 0, sender_id, None),
        )

    def handle_suo(self, group_id: int, sender_id: int, at_id: str | None) -> PlainReply:
        if not self._store.is_group_enabled(group_id, self._config.default_group_enabled):
            return PlainReply(self._config.not_enabled_reply)
        if at_id is not None and not self._config.suo_allow_target_other:
            return PlainReply("当前配置不允许给别人嗦喵")
        target_id = sender_id if at_id is None else int(at_id)
        if not self._store.has_user(target_id):
            self._store.ensure_user(target_id, self._config.user_initial_length)
            prefix = "你" if target_id == sender_id else "TA"
            return PlainReply(f"{prefix}还没有创建{self._jj_name()}喵, 咱帮{prefix}创建了喵, 目前长度是{self._config.user_initial_length}cm喵")
        wait_text = self._cooldown_text(self._suo_cd_data, str(sender_id), self._config.suo_cd_time, "你已经嗦不动了喵")
        if wait_text is not None:
            return PlainReply(wait_text)
        self._suo_cd_data[str(sender_id)] = time.time()
        delta_cm = self._random_delta()
        current_length = self._store.change_length(target_id, delta_cm)
        prefix = "你的" if target_id == sender_id else "对方的"
        return PlainReply(
            self._format_single_change("嗦完之后喵", f"{prefix}{self._jj_name()}", delta_cm, current_length),
            media_request=self._build_media_request("suo", self._config.suo_media_mode, delta_cm < 0, sender_id, target_id),
        )

    def handle_query(self, group_id: int, sender_id: int, at_id: str | None) -> PlainReply:
        if not self._store.is_group_enabled(group_id, self._config.default_group_enabled):
            return PlainReply(self._config.not_enabled_reply)
        target_id = sender_id if at_id is None else int(at_id)
        if not self._store.has_user(target_id):
            self._store.ensure_user(target_id, self._config.user_initial_length)
            prefix = "你" if target_id == sender_id else "TA"
            return PlainReply(f"{prefix}还没有创建{self._jj_name()}喵, 咱帮{prefix}创建了喵, 目前长度是{self._config.user_initial_length}cm喵")
        prefix = "你的" if target_id == sender_id else "TA的"
        return PlainReply(f"{prefix}{self._jj_name()}目前长度为{self._store.get_length(target_id)}cm喵")

    def handle_pk(self, group_id: int, sender_id: int, at_id: str | None) -> PlainReply:
        if not self._store.is_group_enabled(group_id, self._config.default_group_enabled):
            return PlainReply(self._config.not_enabled_reply)
        if at_id is None and self._config.pk_require_at:
            return PlainReply("pk 需要 @ 一个目标喵")
        if at_id is None:
            return PlainReply("当前没有可用的pk目标喵")
        target_id = int(at_id)
        if target_id == sender_id:
            return PlainReply("你不能pk自己喵")
        if not self._store.has_user(sender_id) or not self._store.has_user(target_id):
            self._store.ensure_user(sender_id, self._config.user_initial_length)
            self._store.ensure_user(target_id, self._config.user_initial_length)
            return PlainReply(f"你或对面还没有创建{self._jj_name()}喵, 咱全帮你创建了喵, 你们的{self._jj_name()}长度都是{self._config.user_initial_length}cm喵")
        wait_text = self._cooldown_text(self._pk_cd_data, str(sender_id), self._config.pk_cd_time, "你已经pk不动了喵")
        if wait_text is not None:
            return PlainReply(wait_text)
        self._pk_cd_data[str(sender_id)] = time.time()
        delta_cm = self._random_delta()
        abs_delta = abs(delta_cm)
        winner_gain = round(abs_delta * self._config.pk_winner_gain_ratio, 3)
        winner_delta = winner_gain if delta_cm >= 0 else -winner_gain
        loser_delta = -abs_delta if delta_cm >= 0 else -abs_delta
        if random.random() > 0.5:
            self._store.change_length(sender_id, winner_delta)
            self._store.change_length(target_id, loser_delta)
            return PlainReply(
                self._format_pk_result(True, delta_cm, winner_delta, loser_delta),
                media_request=self._build_media_request("pk", self._config.pk_media_mode, delta_cm < 0, sender_id, target_id),
            )
        self._store.change_length(sender_id, loser_delta)
        self._store.change_length(target_id, winner_delta)
        return PlainReply(
            self._format_pk_result(False, delta_cm, loser_delta, winner_delta),
            media_request=self._build_media_request("pk", self._config.pk_media_mode, delta_cm < 0, sender_id, target_id),
        )

    def handle_toggle(self, group_id: int, normalized: str, event: AstrMessageEvent) -> PlainReply:
        if not self.is_sender_admin(event):
            return PlainReply("只有管理员或群主可以切换淫趴开关喵")
        enabled = "开启" in normalized or "开始" in normalized
        self._store.set_group_enabled(group_id, enabled)
        return PlainReply("功能已开启喵" if enabled else "功能已禁用喵")

    def handle_injection(self, group_id: int, sender_id: int, normalized: str, at_id: str | None) -> PlainReply | tuple[dict[str, float], str]:
        if not self._store.is_group_enabled(group_id, self._config.default_group_enabled):
            return PlainReply(self._config.not_enabled_reply)
        target_id = sender_id if at_id is None else int(at_id)
        object_name = "您" if target_id == sender_id else "该用户"
        if "历史" not in normalized and "全部" not in normalized:
            return PlainReply(f"{object_name}当日总被注射量为{self._store.get_today_injection(target_id)}ml")
        history = self._store.get_injection_history(target_id)
        total_volume = round(sum(item.volume_ml for item in history), 3)
        if len(history) < 2:
            return PlainReply(f"{object_name}历史总被注射量为{total_volume}ml")
        return ({item.date_text: item.volume_ml for item in history}, f"{object_name}历史总被注射量为{total_volume}ml")

    def can_yinpa(self, group_id: int, sender_id: int) -> PlainReply | None:
        if not self._store.is_group_enabled(group_id, self._config.default_group_enabled):
            return PlainReply(self._config.not_enabled_reply)
        wait_text = self._cooldown_text(self._yinpa_cd_data, str(sender_id), self._config.fuck_cd_time, "你已经榨不出来任何东西了")
        if wait_text is not None:
            return PlainReply(wait_text)
        return None

    def finish_yinpa(self, sender_id: int, target_id: int) -> float:
        self._yinpa_cd_data[str(sender_id)] = time.time()
        injected_volume = round(
            random.uniform(self._config.yinpa_volume_min, self._config.yinpa_volume_max), 3
        )
        self._store.add_injection(target_id, injected_volume)
        self._store.touch_user(sender_id, self._config.user_initial_length)
        self._store.touch_user(target_id, self._config.user_initial_length)
        return injected_volume

    def get_today_injection(self, target_id: int) -> float:
        return self._store.get_today_injection(target_id)

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
        return self.is_admin(event)

    def _random_delta(self) -> float:
        base_value = random.random()
        if base_value > self._config.lucky_growth_probability:
            delta_cm = random.uniform(self._config.random_growth_min, self._config.random_growth_max)
        else:
            delta_cm = random.uniform(self._config.lucky_growth_min, self._config.lucky_growth_max)
        return round(delta_cm, 3)

    def _jj_name(self) -> str:
        return random.choice(self._config.jj_names)

    @staticmethod
    def _build_media_request(
        action: str,
        mode: str,
        negative: bool,
        sender_id: int | None,
        target_id: int | None,
    ) -> ActionMediaRequest | None:
        if mode == "none":
            return None
        return ActionMediaRequest(
            action=action,
            mode=mode,
            negative=negative,
            sender_id=sender_id,
            target_id=target_id,
        )

    def _format_single_change(
        self,
        prefix_text: str,
        subject_text: str,
        delta_cm: float,
        current_length: float,
    ) -> str:
        if delta_cm >= 0:
            return f"{prefix_text}, {subject_text}很满意喵, 长了{round(delta_cm, 3)}cm喵, 目前长度为{current_length}cm喵"
        return f"{prefix_text}, {subject_text}委屈坏了喵, 缩短了{round(abs(delta_cm), 3)}cm喵, 目前长度只剩{current_length}cm喵"

    def _format_pk_result(
        self,
        is_sender_winner: bool,
        base_delta_cm: float,
        sender_delta_cm: float,
        target_delta_cm: float,
    ) -> str:
        if base_delta_cm >= 0:
            if is_sender_winner:
                return (
                    f"对决胜利喵, 你的{self._jj_name()}增加了{round(sender_delta_cm, 3)}cm喵, "
                    f"对面缩短了{round(abs(target_delta_cm), 3)}cm喵"
                )
            return (
                f"对决失败喵, 你的{self._jj_name()}缩短了{round(abs(sender_delta_cm), 3)}cm喵, "
                f"对面增加了{round(target_delta_cm, 3)}cm喵"
            )

        if is_sender_winner:
            return (
                f"对决虽然赢了喵, 但今天状态不太妙, 你的{self._jj_name()}缩短了{round(abs(sender_delta_cm), 3)}cm喵, "
                f"对面也跟着缩短了{round(abs(target_delta_cm), 3)}cm喵"
            )
        return (
            f"对决失败喵, 今天谁都高兴不起来, 你的{self._jj_name()}缩短了{round(abs(sender_delta_cm), 3)}cm喵, "
            f"对面也只缩短了{round(abs(target_delta_cm), 3)}cm喵"
        )

    @staticmethod
    def _cooldown_text(cache: dict[str, float], key: str, cooldown_seconds: int, prefix: str) -> str | None:
        last_ts = cache.get(key)
        if last_ts is None:
            return None
        remaining = cooldown_seconds - (time.time() - last_ts)
        if remaining <= 0:
            return None
        return f"{prefix}, 请等待{round(remaining, 3)}秒后再试喵"
