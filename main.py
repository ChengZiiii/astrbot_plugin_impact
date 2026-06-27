from __future__ import annotations

import asyncio
import random
from pathlib import Path
from typing import assert_never

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.event.filter import EventMessageType
from astrbot.api.star import Context, Star, StarTools, register

from .impact_config import ImpactConfig
from .impact_models import ActionMediaRequest, ImageReply, PlainReply
from .impact_media import ImpactMediaManager
from .impact_service import ImpactService
from .impact_store import ImpactStore
from .draw_img import draw_bar_chart
from .txt2img import txt_to_img

COMMAND_ALIASES = {
    "rank": ("jj排行榜", "jj排名", "jj榜单", "jjrank"),
    "toggle": ("开始银趴", "关闭银趴", "开启淫趴", "禁止淫趴", "开启银趴", "禁止银趴"),
    "yinpa": ("日群友", "透群友", "日群主", "透群主", "日管理", "透管理"),
    "inject": ("注入查询", "摄入查询", "射入查询"),
}
COMMAND_GROUP_MAP = {
    "dajiao": ("打胶", "开导"),
    "suo": ("嗦牛子",),
    "query": ("查询",),
    "pk": ("pk", "对决"),
    "rank": COMMAND_ALIASES["rank"],
    "toggle": COMMAND_ALIASES["toggle"],
    "yinpa": COMMAND_ALIASES["yinpa"],
    "inject": COMMAND_ALIASES["inject"],
    "help": ("淫趴介绍",),
}
USAGE_TEXT = """指令1: 嗦牛子 (给目标牛牛增加长度, 自己或者他人, 通过艾特选择对象, 没有at时目标是自己)
指令2: 打胶 | 开导 (给自己牛牛增加长度)
指令3: pk | 对决 (普通的pk, 单纯的random实现输赢, 胜利方获取败方随机数/2的牛牛长度)
指令4: 查询 (目标牛牛长度, 自己或者他人, 通过艾特选择对象, 没有at时目标是自己)
指令5: jj排行榜 | jj排名 | jj榜单 | jjrank (输出倒数五位和前五位, 以及自己的排名)
指令6: 开始银趴 | 关闭银趴 | 开启淫趴 | 禁止淫趴 | 开启银趴 | 禁止银趴 (由管理员或群主开启或者关闭)
指令7: 日群友 | 透群友 | 日群主 | 透群主 | 日管理 | 透管理 (当使用透群友的时候如果at了人那么直接指定)
指令8: 注入查询 | 摄入查询 | 射入查询 (查询目标被透注入的量，后接历史或全部可查看总量)
指令9: 淫趴介绍 (输出淫趴插件的命令列表)"""
@register(
    "astrbot_plugin_impact",
    "Soren",
    "从 nonebot_plugin_impact 迁移的 AstrBot 群聊小游戏插件",
    "0.1.0",
    "https://github.com/Special-Week/nonebot_plugin_impact",
)
class ImpactPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None) -> None:
        super().__init__(context)
        self.config = config or {}
        self._impact_config = ImpactConfig.from_dict(self.config)
        self._data_dir = Path(str(StarTools.get_data_dir("astrbot_plugin_impact")))
        self._tmp_dir = self._data_dir / "tmp"
        self._resource_dir = Path(__file__).parent / "resource"
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        self._store = ImpactStore(self._data_dir)
        self._service = ImpactService(store=self._store, config=self._impact_config)
        self._media_manager = ImpactMediaManager(self._impact_config, self._tmp_dir, self._resource_dir)
        if self._impact_config.log_debug:
            logger.info(f"[impact] loaded config: {self._impact_config}")

    @filter.event_message_type(EventMessageType.ALL)
    async def handle_all_commands(self, event: AstrMessageEvent):
        message_text = event.message_str.strip()
        normalized = message_text.lstrip("/").strip()
        if not normalized:
            return

        reply = await self._dispatch(event, normalized)
        if reply is None:
            return

        event.stop_event()
        match reply:
            case PlainReply(text=text, media_request=media_request, preface_text=preface_text, preface_delay_seconds=preface_delay_seconds):
                if preface_text:
                    yield event.plain_result(preface_text)
                    if preface_delay_seconds > 0:
                        await asyncio.sleep(preface_delay_seconds)
                media_reply = await self._media_manager.build_media_reply(media_request)
                if media_reply is None or self._impact_config.media_send_mode == "text_only":
                    yield event.plain_result(text)
                elif self._impact_config.media_send_mode == "media_only":
                    yield self._media_manager.build_image_result(event, media_reply)
                else:
                    yield self._media_manager.build_image_result(event, self._media_manager.merge_text_with_media(media_reply, text))
            case ImageReply(image_bytes=image_bytes, suffix=suffix, text=text):
                yield self._media_manager.build_image_result(event, ImageReply(image_bytes, suffix, text))
            case unreachable:
                assert_never(unreachable)

    async def _dispatch(self, event: AstrMessageEvent, normalized: str) -> PlainReply | ImageReply | None:
        group_id_raw = event.get_group_id()
        is_private = not group_id_raw
        if is_private and not self._impact_config.private_chat_enabled:
            return None
        group_id = 0 if is_private else int(str(group_id_raw))

        if not is_private:
            group_id_text = str(group_id)
            if group_id_text in self._impact_config.disabled_groups:
                return PlainReply("当前群已被插件黑名单禁用")
            if self._impact_config.enabled_groups and group_id_text not in self._impact_config.enabled_groups:
                return PlainReply("当前群不在插件白名单中")

        self._service.run_daily_maintenance()
        sender_id = int(event.get_sender_id())
        at_id = self._extract_at_qq(event)

        if self._impact_config.log_debug:
            logger.debug(f"[impact] dispatch normalized={normalized} group_id={group_id} private={is_private} at_id={at_id}")

        if self._is_command_enabled("dajiao") and self._matches_command(normalized, COMMAND_GROUP_MAP["dajiao"]):
            return self._service.handle_dajiao(group_id, sender_id)
        if self._is_command_enabled("suo") and self._matches_command(normalized, COMMAND_GROUP_MAP["suo"]):
            return self._service.handle_suo(group_id, sender_id, at_id)
        if self._is_command_enabled("query") and self._matches_command(normalized, COMMAND_GROUP_MAP["query"]):
            return self._service.handle_query(group_id, sender_id, at_id)
        if self._is_command_enabled("pk") and self._matches_command(normalized, COMMAND_GROUP_MAP["pk"]):
            return self._service.handle_pk(group_id, sender_id, at_id)
        if self._is_command_enabled("rank") and self._matches_command(normalized, COMMAND_GROUP_MAP["rank"]):
            return await self._handle_rank(group_id, sender_id, event)
        if not is_private and self._is_command_enabled("toggle") and self._matches_command(normalized, COMMAND_GROUP_MAP["toggle"]):
            return self._service.handle_toggle(group_id, normalized, event)
        if not is_private and self._is_command_enabled("yinpa") and self._matches_command(normalized, COMMAND_GROUP_MAP["yinpa"]):
            return await self._handle_yinpa(group_id, sender_id, normalized, at_id, event)
        if self._is_command_enabled("inject") and self._matches_command(normalized, COMMAND_GROUP_MAP["inject"]):
            return await self._handle_injection(group_id, sender_id, normalized, at_id)
        if self._is_command_enabled("help") and self._matches_command(normalized, COMMAND_GROUP_MAP["help"]):
            if self._impact_config.usage_image_enabled:
                return ImageReply(image_bytes=await txt_to_img.txt_to_img(USAGE_TEXT), suffix=".png")
            return PlainReply(USAGE_TEXT)
        return None

    async def _handle_rank(self, group_id: int, sender_id: int, event: AstrMessageEvent) -> PlainReply | ImageReply:
        if not self._store.is_group_enabled(group_id, self._impact_config.default_group_enabled):
            return PlainReply(self._impact_config.not_enabled_reply)
        if not self._store.has_user(sender_id):
            self._store.ensure_user(sender_id, self._impact_config.user_initial_length)
            return PlainReply(f"你还没有创建{self._jj_name()}看不到rank喵, 咱帮你创建了喵, 目前长度是{self._impact_config.user_initial_length}cm喵")
        rankings = self._store.get_rankings()
        if len(rankings) < self._impact_config.rank_min_users:
            return PlainReply(f"目前记录的数据量小于{self._impact_config.rank_min_users}, 无法显示rank喵")
        my_rank = next(index + 1 for index, item in enumerate(rankings) if item.user_id == sender_id)
        top_slice = rankings[: self._impact_config.rank_top_count]
        picked = top_slice + [
            item for item in rankings[-self._impact_config.rank_bottom_count :] if item.user_id not in {rank.user_id for rank in top_slice}
        ]
        name_map = {item.user_id: await self._get_display_name(event, item.user_id) for item in picked}
        chart_data = {name_map[item.user_id]: item.length_cm for item in picked}
        if not self._impact_config.rank_image_enabled:
            lines = [f"你的排名为{my_rank}喵", "", "排行榜:"]
            for item in picked:
                lines.append(f"{name_map[item.user_id]}: {item.length_cm}cm")
            return PlainReply("\n".join(lines))
        image_bytes = await draw_bar_chart.draw_bar_chart(chart_data)
        return ImageReply(image_bytes=image_bytes, suffix=".png", text=f"你的排名为{my_rank}喵")

    async def _handle_yinpa(self, group_id: int, sender_id: int, normalized: str, at_id: str | None, event: AstrMessageEvent) -> PlainReply:
        gate_reply = self._service.can_yinpa(group_id, sender_id)
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
        preface_text = self._build_yinpa_preface(normalized, sender_name)
        injected_volume = self._service.finish_yinpa(sender_id, target_id)
        total_volume = self._service.get_today_injection(target_id)
        duration_seconds = random.randint(1, 20)
        return PlainReply(
            f"好欸！{sender_name}({sender_id})用时{duration_seconds}秒 \n给 {target_name}({target_id}) 注入了{injected_volume}毫升的脱氧核糖核酸, 当日总注入量为：{total_volume}毫升",
            media_request=ActionMediaRequest(
                action="yinpa",
                mode=self._impact_config.yinpa_media_mode,
                sender_id=sender_id,
                target_id=target_id,
            ),
            preface_text=preface_text,
            preface_delay_seconds=1.0,
        )

    async def _handle_injection(self, group_id: int, sender_id: int, normalized: str, at_id: str | None) -> PlainReply | ImageReply:
        result = self._service.handle_injection(group_id, sender_id, normalized, at_id)
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
    def _build_yinpa_preface(normalized: str, sender_name: str) -> str:
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

    def _jj_name(self) -> str:
        return random.choice(self._impact_config.jj_names)
