from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

_FRAMES_DIR = Path(__file__).parent / "resource" / "avatar_gif" / "lash_frames"
_FRAME_COUNT = 9
_SELF_LOCS = [
    (84, 25), (87, 23), (87, 27),
    (86, 28), (62, 26), (59, 28),
    (76, 20), (85, 24), (80, 23),
]
_SELF_SIZE = (22, 22)
_USER_LOCS = [
    (12, 69), (15, 66), (14, 67),
    (15, 66), (17, 67), (14, 63),
    (21, 56), (15, 62), (17, 69),
]
_USER_SIZE = (22, 22)
_USER_ROTATE = 30.0


def _make_circle(image: Image.Image) -> Image.Image:
    size = image.size[0]
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result


def generate_lash(commander_path: str, target_path: str, output_path: str, fps: int = 20) -> str:
    commander = Image.open(commander_path).convert("RGBA")
    commander = commander.resize(_SELF_SIZE, Image.LANCZOS)
    commander = _make_circle(commander)

    target = Image.open(target_path).convert("RGBA")
    target = target.resize(_USER_SIZE, Image.LANCZOS)
    target = _make_circle(target)
    rotated = target.rotate(_USER_ROTATE, expand=True, resample=Image.BICUBIC)
    left = (rotated.width - _USER_SIZE[0]) // 2
    top = (rotated.height - _USER_SIZE[1]) // 2
    target = rotated.crop((left, top, left + _USER_SIZE[0], top + _USER_SIZE[1]))

    duration_ms = int(1000.0 / fps)
    frames: list[Image.Image] = []
    for index in range(_FRAME_COUNT):
        overlay = Image.open(_FRAMES_DIR / f"{index}.png").convert("RGBA")
        canvas = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        canvas.paste(overlay, (0, 0), overlay)
        canvas.paste(commander, _SELF_LOCS[index], commander)
        canvas.paste(target, _USER_LOCS[index], target)
        frames.append(canvas)

    frames[0].save(
        output_path,
        "GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
    )
    return output_path
