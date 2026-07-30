from __future__ import annotations

import random
import time

from astrbot.api import logger

from .impact_copy_bank import (
    COOLDOWN_DAJIAO,
    COOLDOWN_DAJIAO_SAFE,
    COOLDOWN_FUCK_WIFE,
    COOLDOWN_FUCK_WIFE_SAFE,
    COOLDOWN_PK,
    COOLDOWN_PK_SAFE,
    COOLDOWN_SUO,
    COOLDOWN_SUO_SAFE,
    COOLDOWN_YINPA,
    COOLDOWN_YINPA_SAFE,
    DAJIAO_GROWTH,
    DAJIAO_GROWTH_SAFE,
    DAJIAO_SHRINK,
    DAJIAO_SHRINK_SAFE,
    COOLDOWN_MINE,
    COOLDOWN_MINE_SAFE,
    INJECTION_HISTORY,
    INJECTION_HISTORY_SAFE,
    INJECTION_TODAY,
    INJECTION_TODAY_SAFE,
    MINE_MISS,
    MINE_MISS_SAFE,
    MINE_NO_CHANGE,
    MINE_NO_CHANGE_SAFE,
    MINE_OTHER_GROW,
    MINE_OTHER_GROW_SAFE,
    MINE_OTHER_SHRINK,
    MINE_OTHER_SHRINK_SAFE,
    MINE_SELF_GROW,
    MINE_SELF_GROW_SAFE,
    MINE_SELF_SHRINK,
    MINE_SELF_SHRINK_SAFE,
    NEW_USER_REPLY,
    PK_NO_TARGET,
    PK_SELF_TARGET,
    QUERY_SELF_T,
    QUERY_SELF_T_SAFE,
    QUERY_TARGET_T,
    QUERY_TARGET_T_SAFE,
    SUO_GROWTH,
    SUO_GROWTH_SAFE,
    SUO_SHRINK,
    SUO_SHRINK_SAFE,
    TOGGLE_ADMIN_ONLY,
    pick,
)

from astrbot.api.event import AstrMessageEvent

from .impact_models import FuckWifeResult, MineResult, MineTargetSpec, PlainReply
from .impact_service_gameplay_support import ImpactServiceGameplaySupportMixin
from .impact_time import get_current_week_key


class ImpactServiceGameplayMixin(ImpactServiceGameplaySupportMixin):
    def handle_dajiao(self, group_enabled: bool, sender_id: int, group_id: int | None = None) -> PlainReply:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        if not self._store.has_user(sender_id):
            self._store.ensure_user(sender_id, self._config.user_initial_length)
            return PlainReply(pick(NEW_USER_REPLY).format(length=self._config.user_initial_length), mention_sender=True)
        wait_text = self._cooldown_text(self._dj_cd_data, str(sender_id), self._config.dj_cd_time, self._cs(COOLDOWN_DAJIAO, COOLDOWN_DAJIAO_SAFE), jj=self._jj_name())
        if wait_text is not None:
            return PlainReply(wait_text, mention_sender=True)
        self._dj_cd_data[str(sender_id)] = time.time()
        delta_cm, is_critical = self._random_delta()
        current_length = self._store.change_length(sender_id, delta_cm)
        self._record_group_length_change(group_id, sender_id, delta_cm, current_length, "dajiao_count", True)
        return PlainReply(self._format_single_change(self._cs(DAJIAO_GROWTH, DAJIAO_GROWTH_SAFE), self._cs(DAJIAO_SHRINK, DAJIAO_SHRINK_SAFE), delta_cm, current_length, is_critical), media_request=self._build_media_request("dajiao", self._config.dajiao_media_mode, delta_cm < 0, sender_id, None), mention_sender=True)

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
        wait_text = self._cooldown_text(self._suo_cd_data, str(sender_id), self._config.suo_cd_time, self._cs(COOLDOWN_SUO, COOLDOWN_SUO_SAFE))
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
        return PlainReply(self._format_single_change(self._cs(SUO_GROWTH, SUO_GROWTH_SAFE), self._cs(SUO_SHRINK, SUO_SHRINK_SAFE), delta_cm, current_length, is_critical), media_request=self._build_media_request("suo", self._config.suo_media_mode, delta_cm < 0, sender_id, target_id), mention_sender=True)

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
        # Use same 5-tier thresholds as 日老婆 charm_tier
        _thr = self._config.fuck_wife_charm_thresholds
        _tier = 1
        if len(_thr) >= 3 and current_length >= (_thr[2] * 2):
            _tier = 5
        elif len(_thr) >= 3 and current_length >= _thr[2]:
            _tier = 4
        elif len(_thr) >= 2 and current_length >= _thr[1]:
            _tier = 3
        elif len(_thr) >= 1 and current_length >= _thr[0]:
            _tier = 2
        pool = self._cs(QUERY_SELF_T, QUERY_SELF_T_SAFE) if is_self else self._cs(QUERY_TARGET_T, QUERY_TARGET_T_SAFE)
        query_text = pick(pool.get(_tier, pool[2]))
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
        wait_text = self._cooldown_text(self._pk_cd_data, str(sender_id), self._config.pk_cd_time, self._cs(COOLDOWN_PK, COOLDOWN_PK_SAFE))
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
            return PlainReply(self._format_pk_result(True, delta_cm, winner_delta, loser_delta, is_critical, sender_length, target_length), media_request=self._build_media_request("pk", self._config.pk_media_mode, delta_cm < 0, sender_id, target_id))
        sender_length = self._store.change_length(sender_id, loser_delta)
        target_length = self._store.change_length(target_id, winner_delta)
        self._record_group_pk(group_id, target_id, sender_id, winner_delta, loser_delta, target_length, sender_length)
        return PlainReply(self._format_pk_result(False, delta_cm, loser_delta, winner_delta, is_critical, sender_length, target_length), media_request=self._build_media_request("pk", self._config.pk_media_mode, delta_cm < 0, sender_id, target_id))

    def handle_toggle(self, group_id: int, normalized: str, event: AstrMessageEvent) -> PlainReply:
        if not self.is_sender_admin(event):
            return PlainReply(pick(TOGGLE_ADMIN_ONLY))
        enabled = "开启" in normalized or "开始" in normalized
        self._store.set_group_enabled(group_id, enabled)
        from .impact_copy_bank import TOGGLE_ON, TOGGLE_OFF, TOGGLE_ON_SAFE, TOGGLE_OFF_SAFE
        return PlainReply(pick(self._cs(TOGGLE_ON, TOGGLE_ON_SAFE)) if enabled else pick(self._cs(TOGGLE_OFF, TOGGLE_OFF_SAFE)))

    def handle_injection(self, group_enabled: bool, sender_id: int, normalized: str, at_id: str | None, group_id: int | None = None) -> PlainReply | tuple[dict[str, float], str]:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        target_id = sender_id if at_id is None else int(at_id)
        object_name = "您" if target_id == sender_id else "该用户"
        self._record_group_query(group_id, sender_id)
        if "历史" not in normalized and "全部" not in normalized:
            return PlainReply(pick(self._cs(INJECTION_TODAY, INJECTION_TODAY_SAFE)).format(object=object_name, volume=self._store.get_today_injection(target_id)), mention_sender=True)
        history = self._store.get_injection_history(target_id)
        total_volume = round(sum(item.volume_ml for item in history), 3)
        if len(history) < 2:
            return PlainReply(pick(self._cs(INJECTION_HISTORY, INJECTION_HISTORY_SAFE)).format(object=object_name, volume=total_volume), mention_sender=True)
        return ({item.date_text: item.volume_ml for item in history}, pick(self._cs(INJECTION_HISTORY, INJECTION_HISTORY_SAFE)).format(object=object_name, volume=total_volume))

    def can_yinpa(self, group_enabled: bool, sender_id: int) -> PlainReply | None:
        if not group_enabled:
            return PlainReply(self._config.not_enabled_reply)
        wait_text = self._cooldown_text(self._yinpa_cd_data, str(sender_id), self._config.fuck_cd_time, self._cs(COOLDOWN_YINPA, COOLDOWN_YINPA_SAFE))
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

    # ── 挖矿 ───────────────────────────────────────────────

    @staticmethod
    def _range_pair(values: tuple[float, ...], default: tuple[float, float]) -> tuple[float, float]:
        """把配置里的区间元组安全地取成 (low, high)。"""
        if len(values) >= 2:
            low, high = float(values[0]), float(values[1])
        elif len(values) == 1:
            low = high = float(values[0])
        else:
            low, high = default
        return (low, high) if low <= high else (high, low)

    def _mine_target_name(self, group_id: int | None, target_id: int, is_self: bool) -> str:
        if is_self:
            return "你"
        if group_id is not None:
            display_name = self._store.get_group_display_name(group_id, target_id)
            if display_name:
                return display_name
        return str(target_id) if self._config.nickname_fallback_to_user_id else "群友"

    def handle_mine(
        self,
        group_enabled: bool,
        group_id: int | None,
        sender_id: int,
        spec: MineTargetSpec,
        at_id: str | None = None,
    ) -> MineResult:
        """挖矿结算（同步）。

        返回 ``MineResult``（含回复文案与挖出量），由 handler 决定是否 @ 通知被挖者。
        不使用全局可变状态，避免并发请求相互覆盖。
        """
        target_id = spec.target_id
        if not group_enabled:
            return MineResult(reply=PlainReply(self._config.not_enabled_reply))

        self._store.ensure_user(sender_id, self._config.user_initial_length)
        self._store.ensure_user(target_id, self._config.user_initial_length)

        wait_text = self._cooldown_text(
            self._mine_cd_data,
            str(sender_id),
            self._config.mine_cd_time,
            self._cs(COOLDOWN_MINE, COOLDOWN_MINE_SAFE),
        )
        if wait_text is not None:
            return MineResult(reply=PlainReply(wait_text, mention_sender=True))

        target_name = self._mine_target_name(group_id, target_id, spec.is_self)

        # v1 仅 "user" 矿脉：储量 = 目标今日被注入量。
        reserve = self._store.get_today_injection(target_id)
        fluid_low, fluid_high = self._range_pair(self._config.mine_fluid_range, (1.0, 20.0))
        want = random.uniform(fluid_low, fluid_high)
        cap = max(0.0, reserve) * self._config.mine_fluid_max_ratio_to_reserve
        dug = self._store.consume_today_injection(target_id, min(want, reserve, cap))

        self._mine_cd_data[str(sender_id)] = time.time()
        self._store.touch_user(sender_id, self._config.user_initial_length)
        self._store.touch_user(target_id, self._config.user_initial_length)

        if dug <= 0:
            return MineResult(
                reply=PlainReply(
                    pick(self._cs(MINE_MISS, MINE_MISS_SAFE)).format(name=target_name),
                    mention_sender=True,
                ),
                dug=dug,
                is_self=spec.is_self,
                target_id=target_id,
            )

        if spec.is_self:
            prob = self._config.mine_self_prob
            change_range = self._range_pair(self._config.mine_self_change_range, (-1.0, 2.0))
            growth_pool = self._cs(MINE_SELF_GROW, MINE_SELF_GROW_SAFE)
            shrink_pool = self._cs(MINE_SELF_SHRINK, MINE_SELF_SHRINK_SAFE)
        else:
            prob = self._config.mine_other_prob
            change_range = self._range_pair(self._config.mine_other_change_range, (-2.0, 1.0))
            growth_pool = self._cs(MINE_OTHER_GROW, MINE_OTHER_GROW_SAFE)
            shrink_pool = self._cs(MINE_OTHER_SHRINK, MINE_OTHER_SHRINK_SAFE)

        if random.random() < prob:
            delta_cm = round(random.uniform(*change_range), 3)
            current_length = self._store.change_length(target_id, delta_cm)
            text = self._format_single_change(
                growth_pool, shrink_pool, delta_cm, current_length, False,
                fluid=dug, name=target_name,
            )
            return MineResult(
                reply=PlainReply(text, mention_sender=True),
                dug=dug,
                hit=True,
                is_self=spec.is_self,
                target_id=target_id,
            )

        current_length = self._store.get_length(target_id)
        return MineResult(
            reply=PlainReply(
                pick(self._cs(MINE_NO_CHANGE, MINE_NO_CHANGE_SAFE)).format(
                    fluid=dug, name=target_name, jj=self._jj_name(),
                ),
                mention_sender=True,
            ),
            dug=dug,
            is_self=spec.is_self,
            target_id=target_id,
        )

    async def handle_fuck_wife(
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
            self._fuck_wife_cd_data, sender_uid, self._config.fuck_wife_cd_time, self._cs(COOLDOWN_FUCK_WIFE, COOLDOWN_FUCK_WIFE_SAFE)
        )
        if wait_text is not None:
            return FuckWifeResult(ok=False, reason="cooldown", cooldown_text=wait_text)

        # Daily limit check
        daily_count = self._store.get_daily_fuck_wife_count(sender_uid)
        if daily_count >= self._config.fuck_wife_daily_limit:
            return FuckWifeResult(ok=False, reason="daily_limit")

        is_ntr = target_uid is not None and target_uid != sender_uid

        # Compute charm_tier for reply templates (both paths need it)
        try:
            _sl = self._store.get_length(int(sender_uid))
        except (ValueError, TypeError):
            _sl = 0.0
        _thr = self._config.fuck_wife_charm_thresholds
        charm_tier = 1
        if len(_thr) >= 4 and _sl >= _thr[3]:
            charm_tier = 5
        elif len(_thr) >= 3 and _sl >= _thr[2]:
            charm_tier = 4
        elif len(_thr) >= 2 and _sl >= _thr[1]:
            charm_tier = 3
        elif len(_thr) >= 1 and _sl >= _thr[0]:
            charm_tier = 2

        if not is_ntr:
            # Own wife path — always success
            peek_result: dict = await interop.peek_wife(group_id, sender_uid, index=index)
            if not peek_result:
                return FuckWifeResult(ok=False, reason="no_wife")

            wid = peek_result["wid"]
            wife_name = peek_result.get("name", "")
            tiers = self._config.fuck_wife_intimacy_gain_tiers
            idx = min(charm_tier - 1, len(tiers) - 1)
            intimacy_gain = tiers[idx] if tiers else 0

            record_result: dict = await interop.record_sex_act(
                group_id, wid, sender_uid, False, intimacy_gain,
            )
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

            daily_vol, daily_cnt = self._store.get_wife_daily_injection(group_id, wid)

            return FuckWifeResult(
                ok=True, success=True, is_ntr=False,
                wife_wid=wid, wife_name=wife_name,
                intimacy_gain=intimacy_gain,
                new_intimacy=record_result.get("new_intimacy", 0),
                volume_ml=volume_ml,
                satisfaction=100,
                daily_injection_ml=daily_vol,
                daily_injection_count=daily_cnt,
                charm_tier=charm_tier,
                sender_length=_sl,
            )

        # NTR path
        peek_result: dict = await interop.peek_wife(group_id, target_uid, index=index)
        if not peek_result:
            return FuckWifeResult(ok=False, reason="target_no_wife")

        wid = peek_result["wid"]
        wife_name = peek_result.get("name", "")

        resistance_result: dict = await interop.compute_ntr_resistance(group_id, wid)
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
        if len(thresholds) >= 4 and sender_length >= thresholds[3]:
            charm = 1.5
        elif len(thresholds) >= 3 and sender_length >= thresholds[2]:
            charm = 1.35
        elif len(thresholds) >= 2 and sender_length >= thresholds[1]:
            charm = 1.25
        elif len(thresholds) >= 1 and sender_length >= thresholds[0]:
            charm = 1.1

        # Target length factor: target owner's jj_length linear scaling
        # (shorter owner → easier NTR). Clamped to configured endpoints.
        # If target owner has never interacted with impact (no row in users
        # table), we have no length to scale on — fall back to a neutral 1.0
        # instead of the old 0.0 (which would silently inflate every
        # unknown-target NTR by factor 1.25 and erase the short/long difference).
        try:
            target_owner_length = self._store.get_length(int(target_uid))
            length_factor = self._compute_target_length_factor(
                target_owner_length,
                self._config.fuck_wife_ntr_target_length_min,
                self._config.fuck_wife_ntr_target_length_max,
                self._config.fuck_wife_ntr_target_length_factor_min,
                self._config.fuck_wife_ntr_target_length_factor_max,
            )
        except (ValueError, TypeError):
            length_factor = 1.0

        # Revenge factor: was NTR'd by target owner before
        revenge = self._config.fuck_wife_revenge_multiplier if self._store.was_ntrd_by(sender_uid, target_uid) else 1.0

        # Streak factor: same-target decay 0.7^streak
        streak_count = self._store.get_same_target_fuck_streak(sender_uid, target_uid)
        streak = 0.7 ** streak_count if streak_count > 0 else 1.0

        resistance = resistance_result.get("resistance", 1.0)
        prob = min(1.0, base * charm * length_factor * revenge * streak * resistance)

        roll = roll_seed if roll_seed is not None else random.random()
        success = roll < prob

        # Debug: print probability breakdown so we can see why NTR succeeded/failed
        # in the AstrBot console. Gated on log_debug to avoid noise in production.
        if self._config.log_debug:
            try:
                _tol = self._store.get_length(int(target_uid))
            except (ValueError, TypeError):
                _tol = None
            logger.info(
                f"[ntr] sender={sender_uid} target={target_uid} wid={wid} "
                f"sender_L={sender_length:.1f} target_L={_tol!r} "
                f"base={base} charm={charm} length_factor={length_factor} "
                f"length_cfg=(min={self._config.fuck_wife_ntr_target_length_min}, "
                f"max={self._config.fuck_wife_ntr_target_length_max}, "
                f"fmin={self._config.fuck_wife_ntr_target_length_factor_min}, "
                f"fmax={self._config.fuck_wife_ntr_target_length_factor_max}) "
                f"revenge={revenge} streak={streak} resistance={resistance} "
                f"resistance_flags={ {k: v for k, v in resistance_result.items() if k != 'intimacy'} } "
                f"roll={roll:.4f} prob={prob:.4f} success={success}"
            )

        # NTR intimacy = -自妻同档涨幅（短→B涨，长→B跌）
        tiers = self._config.fuck_wife_intimacy_gain_tiers
        idx = min(charm_tier - 1, len(tiers) - 1)
        intimacy_gain = -(tiers[idx]) if success else 0
        new_intimacy = 0

        # Phase 6: 寿命扣减结果（NTR success 才计算；其它路径保持空 dict）
        ls_result: dict = {"ok": True, "delta_applied": 0,
                            "new_lifespan": -1, "death_occurred": False,
                            "death_announce": "", "damage_announce": ""}

        if success:
            record_result: dict = await interop.record_sex_act(
                group_id, wid, sender_uid, True, intimacy_gain,
            )
            if not record_result.get("ok"):
                return FuckWifeResult(ok=False, reason="record_failed", resistance_flags=resistance_result)
            new_intimacy = record_result.get("new_intimacy", 0)

            # Phase 6 / 跨插件联动：日成功后 animewifexI 老婆寿命扣减
            # 规则从配置读取：fuck_wife_lifespan_damage_enabled / _threshold / _ratio / _max
            # delta 是绝对寿命值，animewifexI 内部走概率判定死亡
            size_delta = 0
            if self._config.fuck_wife_lifespan_damage_enabled and sender_length >= self._config.fuck_wife_lifespan_damage_threshold:
                _diff = int((sender_length - self._config.fuck_wife_lifespan_damage_threshold) * self._config.fuck_wife_lifespan_damage_ratio)
                size_delta = max(0, min(self._config.fuck_wife_lifespan_damage_max, _diff))

            if size_delta > 0:
                # 解析 actor / owner 昵称（拼恶趣味文案用）
                try:
                    actor_nick = self._store.get_group_display_name(
                        int(group_id), int(sender_uid)
                    ) or "某群友"
                except (ValueError, TypeError):
                    actor_nick = "某群友"
                try:
                    owner_nick_for_msg = self._store.get_group_display_name(
                        int(group_id), int(target_uid)
                    ) or "某群友"
                except (ValueError, TypeError):
                    owner_nick_for_msg = "某群友"

                ls_result = await interop.apply_lifespan_damage_from_impact(
                    group_id, wid, sender_uid,
                    actor_nick=actor_nick,
                    delta=size_delta,
                    owner_nick=owner_nick_for_msg,
                )

        volume_ml = round(random.uniform(self._config.fuck_wife_volume_min, self._config.fuck_wife_volume_max), 3) if success else 0.0

        if success:
            self._fuck_wife_cd_data[sender_uid] = time.time()
            self._store.incr_daily_fuck_wife_count(sender_uid)
        self._store.record_wife_sex(
            sender_uid, group_id, wid, target_uid,
            is_ntr=True, success=success,
            volume_ml=volume_ml, satisfaction=80 if success else 0,
        )

        daily_vol, daily_cnt = self._store.get_wife_daily_injection(group_id, wid) if success else (0.0, 0)

        # Look up owner display name for {cuckold} template
        owner_name_retrieved = ""
        if target_uid is not None:
            try:
                gid_int = int(group_id)
                tuid_int = int(target_uid)
                dn = self._store.get_group_display_name(gid_int, tuid_int)
                if dn:
                    owner_name_retrieved = dn
                else:
                    owner_name_retrieved = str(target_uid) if self._config.nickname_fallback_to_user_id else "群友"
            except (ValueError, TypeError):
                owner_name_retrieved = str(target_uid) if self._config.nickname_fallback_to_user_id else "对方"

        # Phase 6: 寿命扣减 + 死亡/损伤文案
        # 注意：``0 or -1`` 是陷阱（0 是合法值，会被替换成 -1）
        _delta_applied = ls_result.get("delta_applied")
        _new_lifespan = ls_result.get("new_lifespan")
        _lifespan_damage = int(_delta_applied) if _delta_applied is not None else 0
        _wife_new_lifespan = int(_new_lifespan) if _new_lifespan is not None else -1
        _wife_death_occurred = bool(ls_result.get("death_occurred", False))
        _lifespan_announce = (
            ls_result.get("death_announce", "")
            if _wife_death_occurred
            else ls_result.get("damage_announce", "")
        )

        return FuckWifeResult(
            ok=True, success=success, is_ntr=True,
            wife_wid=wid, wife_name=wife_name,
            wife_rarity=peek_result.get("rarity", ""),
            owner_name=owner_name_retrieved,
            intimacy_gain=intimacy_gain,
            new_intimacy=new_intimacy,
            volume_ml=volume_ml,
            satisfaction=80 if success else 0,
            daily_injection_ml=daily_vol,
            daily_injection_count=daily_cnt,
            charm_tier=charm_tier,
            sender_length=_sl,
            resistance_flags=resistance_result,
            lifespan_damage=_lifespan_damage,
            wife_new_lifespan=_wife_new_lifespan,
            wife_death_occurred=_wife_death_occurred,
            lifespan_announce=_lifespan_announce,
        )
