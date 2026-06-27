from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionMediaRequest:
    action: str
    mode: str
    negative: bool = False
    sender_id: int | None = None
    target_id: int | None = None


@dataclass(frozen=True, slots=True)
class PlainReply:
    text: str
    media_request: ActionMediaRequest | None = None


@dataclass(frozen=True, slots=True)
class ImageReply:
    image_bytes: bytes
    suffix: str
    text: str | None = None
