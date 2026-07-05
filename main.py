from __future__ import annotations

import asyncio
from pathlib import Path
from typing import assert_never

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.event.filter import EventMessageType
from astrbot.api.star import Context, Star, StarTools, register

from .impact_command_defs import USAGE_TEXT
from .impact_config import ImpactConfig
from .impact_media import ImpactMediaManager
from .impact_models import ImageReply, PlainReply
from .impact_plugin_handlers import ImpactPluginHandlersMixin
from .impact_service import ImpactService
from .impact_store import ImpactStore
from .impact_time import get_current_week_key
from .txt2img import txt_to_img


@register(
    "astrbot_plugin_impact",
    "Soren",
    "从 nonebot_plugin_impact 迁移的 AstrBot 群聊小游戏插件",
    "0.2.0",
    "https://github.com/Special-Week/nonebot_plugin_impact",
)
class ImpactPlugin(ImpactPluginHandlersMixin, Star):
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
        self._txt_to_img = txt_to_img
        self._usage_text = USAGE_TEXT
        self._weekly_broadcast_task = None
        try:
            self._weekly_broadcast_task = asyncio.create_task(self._weekly_broadcast_loop())
        except RuntimeError:
            self._weekly_broadcast_task = None
        if self._impact_config.log_debug:
            logger.info(f"[impact] loaded config: {self._impact_config}")

    async def _weekly_broadcast_loop(self) -> None:
        await asyncio.sleep(5)
        while True:
            try:
                await self._run_scheduled_weekly_report_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[impact] 周报定时播报失败")
            await asyncio.sleep(30)

    async def _run_scheduled_weekly_report_once(self) -> None:
        current_week_key = get_current_week_key()
        if not self._service.should_run_scheduled_weekly_report():
            return
        had_pending_report = False
        send_failed = False
        for group_id, umo in self._store.list_group_sessions():
            report_text = self._service.ensure_weekly_settlement(group_id, current_week_key)
            if report_text is None:
                continue
            had_pending_report = True
            try:
                await self.context.send_message(umo, [Comp.Plain(report_text)])
            except Exception as exc:
                send_failed = True
                logger.warning(f"[impact] 周报主动播报失败: group_id={group_id}, error={exc}")
        if not had_pending_report or not send_failed:
            self._service.mark_scheduled_weekly_report_sent(current_week_key)

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
            case PlainReply(text=text, media_request=media_request, preface_text=preface_text, mention_sender=mention_sender):
                if preface_text:
                    await event.send(event.plain_result(preface_text))
                media_reply = await self._media_manager.build_media_reply(media_request)
                if media_reply is None or self._impact_config.media_send_mode == "text_only":
                    if mention_sender:
                        yield event.chain_result([Comp.At(qq=str(event.get_sender_id())), Comp.Plain(f"\n{text}")])
                    else:
                        yield event.plain_result(text)
                elif self._impact_config.media_send_mode == "media_only":
                    if mention_sender:
                        media_reply = ImageReply(media_reply.image_bytes, media_reply.suffix, media_reply.text, True)
                    yield self._media_manager.build_image_result(event, media_reply)
                else:
                    merged_reply = self._media_manager.merge_text_with_media(media_reply, text)
                    if mention_sender:
                        merged_reply = ImageReply(merged_reply.image_bytes, merged_reply.suffix, merged_reply.text, True)
                    yield self._media_manager.build_image_result(event, merged_reply)
            case ImageReply(image_bytes=image_bytes, suffix=suffix, text=text, mention_sender=mention_sender):
                yield self._media_manager.build_image_result(event, ImageReply(image_bytes, suffix, text, mention_sender))
            case unreachable:
                assert_never(unreachable)

    async def terminate(self) -> None:
        task = self._weekly_broadcast_task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
