from __future__ import annotations

from dataclasses import dataclass


def _to_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def _to_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_str_list(value: object, default: list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]
    return default.copy()


@dataclass(frozen=True, slots=True)
class ImpactConfig:
    dj_cd_time: int
    pk_cd_time: int
    suo_cd_time: int
    fuck_cd_time: int
    enable_inactive_penalty: bool
    default_group_enabled: bool
    rank_min_users: int
    rank_top_count: int
    rank_bottom_count: int
    pk_require_at: bool
    suo_allow_target_other: bool
    yinpa_allow_random_target: bool
    yinpa_allow_owner_target: bool
    yinpa_allow_admin_target: bool
    admin_only_toggle: bool
    user_initial_length: float
    random_growth_min: float
    random_growth_max: float
    lucky_growth_min: float
    lucky_growth_max: float
    lucky_growth_probability: float
    pk_winner_gain_ratio: float
    inactive_penalty_min: float
    inactive_penalty_max: float
    inactive_penalty_floor: float
    yinpa_volume_min: float
    yinpa_volume_max: float
    enabled_groups: list[str]
    disabled_groups: list[str]
    admin_list: list[str]
    private_chat_enabled: bool
    commands_enabled: list[str]
    jj_names: list[str]
    not_enabled_reply: str
    rank_image_enabled: bool
    usage_image_enabled: bool
    nickname_fallback_to_user_id: bool
    yinpa_require_member_api: bool
    temp_file_ttl_seconds: int
    strict_command_match: bool
    log_debug: bool
    media_send_mode: str
    dajiao_media_mode: str
    suo_media_mode: str
    pk_media_mode: str
    yinpa_media_mode: str
    pk_avatar_gif_styles: list[str]
    yinpa_avatar_gif_styles: list[str]

    @staticmethod
    def from_dict(raw: dict | None) -> ImpactConfig:
        config = raw or {}
        jj_names = _to_str_list(config.get("jj_names"), ["牛子", "牛牛", "丁丁", "JJ"])
        commands_enabled = _to_str_list(
            config.get("commands_enabled"),
            ["dajiao", "suo", "query", "pk", "rank", "toggle", "yinpa", "inject", "help"],
        )
        pk_avatar_gif_styles = _to_str_list(config.get("pk_avatar_gif_styles"), ["lash"])
        yinpa_avatar_gif_styles = _to_str_list(config.get("yinpa_avatar_gif_styles"), ["do"])
        not_enabled_reply = str(
            config.get(
                "not_enabled_reply",
                '群内还未开启淫趴游戏, 请管理员或群主发送"开启淫趴", "禁止淫趴"以开启/关闭该功能',
            )
        )
        return ImpactConfig(
            dj_cd_time=_to_int(config.get("djcdtime"), 300),
            pk_cd_time=_to_int(config.get("pkcdtime"), 60),
            suo_cd_time=_to_int(config.get("suocdtime"), 300),
            fuck_cd_time=_to_int(config.get("fuckcdtime"), 3600),
            enable_inactive_penalty=_to_bool(config.get("isalive"), False),
            default_group_enabled=_to_bool(config.get("default_group_enabled"), False),
            rank_min_users=max(1, _to_int(config.get("rank_min_users"), 5)),
            rank_top_count=max(1, _to_int(config.get("rank_top_count"), 5)),
            rank_bottom_count=max(1, _to_int(config.get("rank_bottom_count"), 5)),
            pk_require_at=_to_bool(config.get("pk_require_at"), True),
            suo_allow_target_other=_to_bool(config.get("suo_allow_target_other"), True),
            yinpa_allow_random_target=_to_bool(config.get("yinpa_allow_random_target"), True),
            yinpa_allow_owner_target=_to_bool(config.get("yinpa_allow_owner_target"), True),
            yinpa_allow_admin_target=_to_bool(config.get("yinpa_allow_admin_target"), True),
            admin_only_toggle=_to_bool(config.get("admin_only_toggle"), False),
            user_initial_length=_to_float(config.get("user_initial_length"), 10.0),
            random_growth_min=_to_float(config.get("random_growth_min"), 0.0),
            random_growth_max=_to_float(config.get("random_growth_max"), 1.0),
            lucky_growth_min=_to_float(config.get("lucky_growth_min"), 1.0),
            lucky_growth_max=_to_float(config.get("lucky_growth_max"), 2.0),
            lucky_growth_probability=_to_float(config.get("lucky_growth_probability"), 0.1),
            pk_winner_gain_ratio=_to_float(config.get("pk_winner_gain_ratio"), 0.5),
            inactive_penalty_min=_to_float(config.get("inactive_penalty_min"), 0.0),
            inactive_penalty_max=_to_float(config.get("inactive_penalty_max"), 1.0),
            inactive_penalty_floor=_to_float(config.get("inactive_penalty_floor"), 1.0),
            yinpa_volume_min=_to_float(config.get("yinpa_volume_min"), 1.0),
            yinpa_volume_max=_to_float(config.get("yinpa_volume_max"), 100.0),
            enabled_groups=_to_str_list(config.get("enabled_groups"), []),
            disabled_groups=_to_str_list(config.get("disabled_groups"), []),
            admin_list=_to_str_list(config.get("admin_list"), []),
            private_chat_enabled=_to_bool(config.get("private_chat_enabled"), False),
            commands_enabled=commands_enabled,
            jj_names=jj_names,
            not_enabled_reply=not_enabled_reply,
            rank_image_enabled=_to_bool(config.get("rank_image_enabled"), True),
            usage_image_enabled=_to_bool(config.get("usage_image_enabled"), True),
            nickname_fallback_to_user_id=_to_bool(config.get("nickname_fallback_to_user_id"), True),
            yinpa_require_member_api=_to_bool(config.get("yinpa_require_member_api"), True),
            temp_file_ttl_seconds=max(0, _to_int(config.get("temp_file_ttl_seconds"), 10)),
            strict_command_match=_to_bool(config.get("strict_command_match"), True),
            log_debug=_to_bool(config.get("log_debug"), False),
            media_send_mode=str(config.get("media_send_mode", "text_and_media")).strip() or "text_and_media",
            dajiao_media_mode=str(config.get("dajiao_media_mode", "fixed_gif")).strip() or "fixed_gif",
            suo_media_mode=str(config.get("suo_media_mode", "fixed_gif")).strip() or "fixed_gif",
            pk_media_mode=str(config.get("pk_media_mode", "avatar_gif")).strip() or "avatar_gif",
            yinpa_media_mode=str(config.get("yinpa_media_mode", "avatar_gif")).strip() or "avatar_gif",
            pk_avatar_gif_styles=pk_avatar_gif_styles,
            yinpa_avatar_gif_styles=yinpa_avatar_gif_styles,
        )
