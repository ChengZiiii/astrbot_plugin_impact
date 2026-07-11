from __future__ import annotations

from dataclasses import dataclass, field


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
    preface_text: str | None = None
    mention_sender: bool = False


@dataclass(frozen=True, slots=True)
class ImageReply:
    image_bytes: bytes
    suffix: str
    text: str | None = None
    mention_sender: bool = False


@dataclass(frozen=True, slots=True)
class WeeklyResultEntry:
    category: str
    rank_no: int
    user_id: int
    metric_value: float
    title_text: str | None = None
    display_name_snapshot: str | None = None


@dataclass
class FuckWifeResult:
    ok: bool
    success: bool = False
    is_ntr: bool = False
    reason: str = ""
    wife_wid: str = ""
    wife_name: str = ""
    wife_rarity: str = ""  # Phase 6: animewifexI 联动需要
    owner_name: str = ""
    intimacy_gain: int = 0
    new_intimacy: int = 0
    volume_ml: float = 0.0
    satisfaction: int = 0
    daily_injection_ml: float = 0.0
    daily_injection_count: int = 0
    lewdness_level: int = 0
    charm_tier: int = 0
    sender_length: float = 0.0
    cooldown_text: str = ""
    resistance_flags: dict | None = field(default=None)
    # Phase 6: animewifexI 寿命系统联动（仅 NTR 路径）
    lifespan_damage: int = 0            # 本次对老婆寿命的扣减（0 = 没扣）
    wife_new_lifespan: int = -1         # 扣后寿命
    wife_death_occurred: bool = False  # 本次是否导致老婆死亡
    lifespan_announce: str = ""        # 恶趣味 / 损伤文案（死亡/损伤时非空）
