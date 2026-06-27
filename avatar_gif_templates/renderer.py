from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never

from PIL import Image

from .common import make_circle, save_gif

RotateMode = Literal["none", "simple", "crop"]


@dataclass(frozen=True, slots=True)
class AvatarPlacement:
    size: tuple[int, int]
    rotate_degrees: float
    rotate_mode: RotateMode
    locations: list[tuple[int, int]]


@dataclass(frozen=True, slots=True)
class AvatarGifTemplate:
    name: str
    frames_dir: str
    frame_count: int
    fps: int
    commander: AvatarPlacement
    target: AvatarPlacement


def normalize_template_name(template_name: str) -> str:
    normalized = template_name.strip().lower()
    match normalized:
        case "do" | "do_frames":
            return "do"
        case "lash" | "lash_frames":
            return "lash"
        case _:
            return normalized


def render_avatar_gif(template_name: str, commander_path: str, target_path: str, output_path: str) -> str:
    template = load_template(template_name)
    commander = _prepare_avatar(Image.open(commander_path).convert("RGBA"), template.commander)
    target = _prepare_avatar(Image.open(target_path).convert("RGBA"), template.target)

    frames_dir = Path(__file__).resolve().parent.parent / "resource" / "avatar_gif" / template.frames_dir
    frames: list[Image.Image] = []
    for index in range(template.frame_count):
        overlay = Image.open(frames_dir / f"{index}.png").convert("RGBA")
        canvas = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        canvas.paste(overlay, (0, 0), overlay)
        canvas.paste(commander, template.commander.locations[index], commander)
        canvas.paste(target, template.target.locations[index], target)
        frames.append(canvas)
    return save_gif(output_path, frames, template.fps)


def has_template(template_name: str) -> bool:
    normalized_name = normalize_template_name(template_name)
    template_path = Path(__file__).resolve().parent / "templates" / f"{normalized_name}.json"
    return template_path.is_file()


def load_template(template_name: str) -> AvatarGifTemplate:
    normalized_name = normalize_template_name(template_name)
    template_path = Path(__file__).resolve().parent / "templates" / f"{normalized_name}.json"
    raw = json.loads(template_path.read_text(encoding="utf-8"))
    return AvatarGifTemplate(
        name=str(raw["name"]),
        frames_dir=str(raw["frames_dir"]),
        frame_count=int(raw["frame_count"]),
        fps=int(raw.get("fps", 20)),
        commander=_parse_placement(raw["commander"]),
        target=_parse_placement(raw["target"]),
    )


def _parse_placement(raw: dict) -> AvatarPlacement:
    return AvatarPlacement(
        size=(int(raw["size"][0]), int(raw["size"][1])),
        rotate_degrees=float(raw.get("rotate_degrees", 0.0)),
        rotate_mode=_parse_rotate_mode(str(raw.get("rotate_mode", "none"))),
        locations=[(int(item[0]), int(item[1])) for item in raw["locations"]],
    )


def _parse_rotate_mode(raw: str) -> RotateMode:
    match raw:
        case "none":
            return "none"
        case "simple":
            return "simple"
        case "crop":
            return "crop"
        case _:
            raise ValueError(f"Unsupported rotate_mode: {raw}")


def _prepare_avatar(image: Image.Image, placement: AvatarPlacement) -> Image.Image:
    resized = image.resize(placement.size, Image.LANCZOS)
    rounded = make_circle(resized)
    match placement.rotate_mode:
        case "none":
            return rounded
        case "simple":
            return rounded.rotate(placement.rotate_degrees, expand=False, resample=Image.BICUBIC)
        case "crop":
            rotated = rounded.rotate(placement.rotate_degrees, expand=True, resample=Image.BICUBIC)
            left = (rotated.width - placement.size[0]) // 2
            top = (rotated.height - placement.size[1]) // 2
            return rotated.crop((left, top, left + placement.size[0], top + placement.size[1]))
        case unreachable:
            assert_never(unreachable)
