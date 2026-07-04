from __future__ import annotations

import random

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .draw_img import draw_bar_chart
from .impact_command_defs import COMMAND_GROUP_MAP
from .impact_models import ActionMediaRequest, ImageReply, PlainReply
from .impact_time import get_current_week_key


class ImpactPluginHandlersMixin:
    async def _dispatch(self, event: AstrMessageEvent, normalized: str) -> PlainReply | ImageReply | None:
        command_key = self._resolve_command_key(normalized)
        if command_key is None:
            return None
        group_id_raw = event.get_group_id()
        is_private = not group_id_raw
        if is_private and command_key in {"weekly_report", "weekly_rank", "weekly_stats", "rival", "honor"}:
            return PlainReply("周玩法请在群聊查看喵")
        if is_private and not self._impact_config.private_chat_enabled:
            return None
        group_id = 0 if is_private else int(str(group_id_raw))
        group_enabled = self._impact_config.private_chat_enabled if is_private else self._store.is_group_enabled(group_id, self._impact_config.default_group_enabled)

        if not is_private:
            group_id_text = str(group_id)
            if group_id_text in self._impact_config.disabled_groups:
                return PlainReply("当前群已被插件黑名单禁用")
            if self._impact_config.enabled_groups and group_id_text not in self._impact_config.enabled_groups:
                return PlainReply("当前群不在插件白名单中")

        self._service.run_daily_maintenance()
        sender_id = int(event.get_sender_id())
        at_id = self._extract_at_qq(event)

        if not is_private and command_key not in {"toggle", "help"}:
            settlement_report = self._service.ensure_weekly_settlement(group_id, get_current_week_key())
            if settlement_report is not None:
                await event.send(event.plain_result(settlement_report))
            member_ids = [sender_id]
            if at_id is not None:
                member_ids.append(int(at_id))
            self._store.register_group_members(group_id, member_ids, self._impact_config.user_initial_length)

        if self._impact_config.log_debug:
            logger.debug(f"[impact] dispatch normalized={normalized} command_key={command_key} group_id={group_id} private={is_private} at_id={at_id}")

        if command_key == "dajiao":
            return self._service.handle_dajiao(group_enabled, sender_id, None if is_private else group_id)
        if command_key == "suo":
            return self._service.handle_suo(group_enabled, sender_id, at_id, None if is_private else group_id)
        if command_key == "query":
            return self._service.handle_query(group_enabled, sender_id, at_id, None if is_private else group_id)
        if command_key == "pk":
            return self._service.handle_pk(group_enabled, sender_id, at_id, None if is_private else group_id)
        if command_key == "rank":
            return await self._handle_rank(group_enabled, sender_id, event, is_private, group_id)
        if command_key == "toggle" and not is_private:
            return self._service.handle_toggle(group_id, normalized, event)
        if command_key == "yinpa" and not is_private:
            return await self._handle_yinpa(group_enabled, group_id, sender_id, normalized, at_id, event)
        if command_key == "inject":
            return await self._handle_injection(group_enabled, sender_id, normalized, at_id, None if is_private else group_id)
        if command_key == "weekly_report" and not is_private:
            return self._service.handle_weekly_report(group_id)
        if command_key == "weekly_rank" and not is_private:
            return self._service.handle_weekly_rank(group_id)
        if command_key == "weekly_stats" and not is_private:
            return self._service.handle_my_weekly_stats(group_id, sender_id)
        if command_key == "rival" and not is_private:
            return self._service.handle_my_rivals(group_id, sender_id)
        if command_key == "honor" and not is_private:
            return self._service.handle_honor_wall(group_id)
        if command_key == "help":
            if self._impact_config.usage_image_enabled:
                return ImageReply(image_bytes=await self._txt_to_img.txt_to_img(self._usage_text), suffix=".png")
            return PlainReply(self._usage_text)
        return None

    async def _handle_rank(self, group_enabled: bool, sender_id: int, event: AstrMessageEvent, is_private: bool, group_id: int) -> PlainReply | ImageReply:
        if not group_enabled:
            return PlainReply(self._impact_config.not_enabled_reply)
        if not self._store.has_user(sender_id):
            self._store.ensure_user(sender_id, self._impact_config.user_initial_length)
        rankings = self._store.get_rankings() if is_private else self._store.get_group_rankings(group_id)
        if len(rankings) < self._impact_config.rank_min_users:
            return PlainReply(f"目前记录的数据量小于{self._impact_config.rank_min_users}, 无法显示rank喵")
        my_rank = next(index + 1 for index, item in enumerate(rankings) if item.user_id == sender_id)
        global_rank = self._store.get_global_rank(sender_id)
        if is_private:
            current_length = self._store.get_length(sender_id)
            return PlainReply(f"你的全局长度为{current_length}cm喵\n你的全局排名为{global_rank}喵", mention_sender=True)
        top_slice = rankings[: self._impact_config.rank_top_count]
        picked = top_slice + [item for item in rankings[-self._impact_config.rank_bottom_count :] if item.user_id not in {rank.user_id for rank in top_slice}]
        name_map = {item.user_id: await self._get_display_name(event, item.user_id) for item in picked}
        chart_data = {name_map[item.user_id]: item.length_cm for item in picked}
        if not self._impact_config.rank_image_enabled:
            lines = [f"你的群内排名为{my_rank}喵", f"你的全局排名为{global_rank}喵", "", "本群排行榜:"]
            for item in picked:
                lines.append(f"{name_map[item.user_id]}: {item.length_cm}cm")
            return PlainReply("\n".join(lines))
        image_bytes = await draw_bar_chart.draw_bar_chart(chart_data)
        return ImageReply(image_bytes=image_bytes, suffix=".png", text=f"你的群内排名为{my_rank}喵\n你的全局排名为{global_rank}喵")

    async def _handle_yinpa(self, group_enabled: bool, group_id: int, sender_id: int, normalized: str, at_id: str | None, event: AstrMessageEvent) -> PlainReply:
        gate_reply = self._service.can_yinpa(group_enabled, sender_id)
        if gate_reply is not None:
            return gate_reply
        members = await self._get_group_members(event, group_id)
        if not members and (self._impact_config.yinpa_require_member_api or at_id is None):
            return PlainReply("当前平台无法获取群成员列表, 暂时不能透群友喵")
        target_id = self._pick_yinpa_target(normalized, sender_id, at_id, members)
        if target_id is None:
            return PlainReply("没找到合适的目标喵")
        if target_id == sender_id:
            return PlainReply("你透你自己?")
        sender_name = await self._get_display_name(event, sender_id, members)
        target_name = await self._get_display_name(event, target_id, members)
        preface_text = self._build_yinpa_preface(normalized, sender_name, at_id, target_name, target_id)
        injected_volume = self._service.finish_yinpa(sender_id, target_id, group_id)
        total_volume = self._service.get_today_injection(target_id)
        duration_seconds = random.randint(1, 20)
        return PlainReply(
            f"好欸！{sender_name}({sender_id})用时{duration_seconds}秒 \n给 {target_name}({target_id}) 注入了{injected_volume}毫升的脱氧核糖核酸, 当日总注入量为：{total_volume}毫升",
            media_request=ActionMediaRequest(action="yinpa", mode=self._impact_config.yinpa_media_mode, sender_id=sender_id, target_id=target_id),
            preface_text=preface_text,
        )

    async def _handle_injection(self, group_enabled: bool, sender_id: int, normalized: str, at_id: str | None, group_id: int | None) -> PlainReply | ImageReply:
        result = self._service.handle_injection(group_enabled, sender_id, normalized, at_id, group_id)
        if isinstance(result, PlainReply):
            return result
        chart_data, text = result
        image_bytes = await draw_bar_chart.draw_line_chart(chart_data)
        return ImageReply(image_bytes=image_bytes, suffix=".png", text=text)

    async def _get_group_members(self, event: AstrMessageEvent, group_id: int) -> list[dict]:
        bot = getattr(event, "bot", None)
        if bot is None or not hasattr(bot, "get_group_member_list"):
            return []
        try:
            members = await bot.get_group_member_list(group_id=group_id)
        except Exception as exc:
            logger.warning(f"[impact] 获取群成员列表失败: {exc}")
            return []
        return [member for member in members if isinstance(member, dict)]

    async def _get_display_name(self, event: AstrMessageEvent, user_id: int, members: list[dict] | None = None) -> str:
        if members is not None:
            for member in members:
                if int(member.get("user_id", 0)) != user_id:
                    continue
                card_name = member.get("card")
                if card_name:
                    return str(card_name)
                nickname = member.get("nickname")
                if nickname:
                    return str(nickname)
        bot = getattr(event, "bot", None)
        if bot is None or not hasattr(bot, "call_api"):
            return str(user_id) if self._impact_config.nickname_fallback_to_user_id else "群友"
        try:
            stranger = await bot.call_api("get_stranger_info", user_id=user_id, no_cache=False)
        except Exception:
            return str(user_id) if self._impact_config.nickname_fallback_to_user_id else "群友"
        nickname = stranger.get("nickname") if isinstance(stranger, dict) else None
        if nickname:
            return str(nickname)
        return str(user_id) if self._impact_config.nickname_fallback_to_user_id else "群友"

    @staticmethod
    def _build_yinpa_preface(normalized: str, sender_name: str, at_id: str | None, target_name: str, target_id: int) -> str:
        if at_id is not None:
            return f"现在咱将把{target_name}({target_id})\n送给{sender_name}色色！"
        if "群主" in normalized:
            return f"现在咱将把群主\n送给{sender_name}色色！"
        if "管理" in normalized:
            return f"现在咱将随机抽取一位幸运管理\n送给{sender_name}色色！"
        return f"现在咱将随机抽取一位幸运群友\n送给{sender_name}色色！"

    def _pick_yinpa_target(self, normalized: str, sender_id: int, at_id: str | None, members: list[dict]) -> int | None:
        if at_id is not None:
            return int(at_id)
        if "群主" in normalized:
            if not self._impact_config.yinpa_allow_owner_target:
                return None
            for member in members:
                if member.get("role") == "owner":
                    return int(member.get("user_id", sender_id))
            return None
        if "管理" in normalized:
            if not self._impact_config.yinpa_allow_admin_target:
                return None
            admins = [int(member["user_id"]) for member in members if member.get("role") == "admin" and int(member.get("user_id", sender_id)) != sender_id]
            return random.choice(admins) if admins else None
        if not self._impact_config.yinpa_allow_random_target:
            return None
        candidates = [int(member["user_id"]) for member in members if int(member.get("user_id", sender_id)) != sender_id]
        return random.choice(candidates) if candidates else None

    @staticmethod
    def _extract_at_qq(event: AstrMessageEvent) -> str | None:
        for component in event.get_messages():
            if isinstance(component, Comp.At):
                for attr_name in ("qq", "target", "user_id", "id"):
                    candidate = getattr(component, attr_name, None)
                    if candidate:
                        return str(candidate)
        return None

    def _matches_command(self, normalized: str, commands: tuple[str, ...]) -> bool:
        for command in commands:
            if normalized == command:
                return True
            if self._impact_config.strict_command_match:
                if normalized.startswith(f"{command} "):
                    return True
                if normalized.startswith(f"{command}@"):
                    return True
            elif normalized.startswith(command):
                return True
        return False

    def _is_command_enabled(self, command_key: str) -> bool:
        return command_key in self._impact_config.commands_enabled

    def _resolve_command_key(self, normalized: str) -> str | None:
        for command_key, commands in COMMAND_GROUP_MAP.items():
            if not self._is_command_enabled(command_key):
                continue
            if self._matches_command(normalized, commands):
                return command_key
        return None
