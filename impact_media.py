from __future__ import annotations

import asyncio
import functools
import urllib.request
import uuid
from pathlib import Path

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .avatar_gif_templates import has_template, normalize_template_name, render_avatar_gif
from .impact_config import ImpactConfig
from .impact_models import ActionMediaRequest, ImageReply

QQ_AVATAR_URL = "http://q1.qlogo.cn/g?b=qq&nk={qq}&s=640"


class ImpactMediaManager:
    def __init__(self, config: ImpactConfig, tmp_dir: Path, resource_dir: Path) -> None:
        self._config = config
        self._tmp_dir = tmp_dir
        self._resource_dir = resource_dir

    def build_image_result(self, event: AstrMessageEvent, reply: ImageReply):
        image_path = self._tmp_dir / f"impact_{uuid.uuid4().hex[:8]}{reply.suffix}"
        image_path.write_bytes(reply.image_bytes)
        if reply.text:
            result = event.chain_result([Comp.Image(file=str(image_path)), Comp.Plain(f"\n{reply.text}")])
        else:
            result = event.chain_result([Comp.Image(file=str(image_path))])
        asyncio.create_task(self.cleanup_temp_file(image_path))
        return result

    async def build_media_reply(self, request: ActionMediaRequest | None) -> ImageReply | None:
        if request is None:
            return None
        if request.mode == "fixed_gif":
            return self._load_fixed_media(request.action, request.negative)
        if request.mode == "avatar_gif":
            return await self._build_avatar_gif(request)
        return None

    def merge_text_with_media(self, media_reply: ImageReply, text: str) -> ImageReply:
        return ImageReply(media_reply.image_bytes, media_reply.suffix, text)

    def _load_fixed_media(self, action: str, negative: bool) -> ImageReply | None:
        folder_name = f"{action}_shrink" if negative else f"{action}_grow"
        folder_path = self._resource_dir / "fixed_gif" / folder_name
        media_files = [
            path
            for path in folder_path.glob("*")
            if path.is_file() and path.suffix.lower() in {".gif", ".png", ".jpg", ".jpeg", ".webp"}
        ]
        if not media_files:
            return None
        picked_path = media_files[hash(action + str(negative) + uuid.uuid4().hex) % len(media_files)]
        return ImageReply(image_bytes=picked_path.read_bytes(), suffix=picked_path.suffix)

    async def _build_avatar_gif(self, request: ActionMediaRequest) -> ImageReply | None:
        if request.sender_id is None or request.target_id is None:
            return None
        style_names = self._get_avatar_gif_styles(request.action)
        if not style_names:
            return None
        style_name = style_names[hash(request.action + uuid.uuid4().hex) % len(style_names)]
        generator = self._get_avatar_gif_generator(style_name)
        if generator is None:
            return None

        commander_path = self._tmp_dir / f"impact_cmd_{uuid.uuid4().hex[:8]}.png"
        target_path = self._tmp_dir / f"impact_tgt_{uuid.uuid4().hex[:8]}.png"
        output_path = self._tmp_dir / f"impact_media_{uuid.uuid4().hex[:8]}.gif"
        try:
            loop = asyncio.get_running_loop()
            ok_sender = await loop.run_in_executor(None, self._download_avatar_sync, request.sender_id, commander_path)
            ok_target = await loop.run_in_executor(None, self._download_avatar_sync, request.target_id, target_path)
            if not ok_sender or not ok_target:
                return None
            await loop.run_in_executor(None, generator, str(commander_path), str(target_path), str(output_path))
            return ImageReply(image_bytes=output_path.read_bytes(), suffix=".gif")
        except Exception as exc:
            logger.warning(f"[impact] 生成头像 GIF 失败: {exc}")
            return None
        finally:
            for temp_path in (commander_path, target_path, output_path):
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _get_avatar_gif_styles(self, action: str) -> list[str]:
        if action == "pk":
            return self._config.pk_avatar_gif_styles
        if action == "yinpa":
            return self._config.yinpa_avatar_gif_styles
        return []

    @staticmethod
    def _get_avatar_gif_generator(style_name: str):
        normalized_name = normalize_template_name(style_name)
        if has_template(normalized_name):
            return functools.partial(render_avatar_gif, normalized_name)
        logger.warning(f"[impact] 未知头像 GIF 模板: {style_name}")
        return None

    @staticmethod
    def _download_avatar_sync(user_id: int, output_path: Path) -> bool:
        try:
            with urllib.request.urlopen(QQ_AVATAR_URL.format(qq=user_id), timeout=30) as response:
                output_path.write_bytes(response.read())
            return True
        except Exception:
            return False

    async def cleanup_temp_file(self, image_path: Path) -> None:
        await asyncio.sleep(self._config.temp_file_ttl_seconds)
        try:
            image_path.unlink(missing_ok=True)
        except OSError:
            logger.debug(f"[impact] 清理临时文件失败: {image_path}")
