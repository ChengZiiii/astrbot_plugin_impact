from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

_FRAMES_DIR = Path(__file__).parent / "resource" / "avatar_gif" / "do_frames"
_FRAME_COUNT = 3
_SELF_LOCS = [(116, -8), (109, 3), (130, -10)]
_SELF_SIZE = (122, 122)
_SELF_ROTATE = -15.0
_USER_LOCS = [(2, 177), (12, 172), (6, 158)]
_USER_SIZE = (112, 112)
_USER_ROTATE = 90.0


def _make_circle(image: Image.Image) -> Image.Image:
    size = image.size[0]
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result


def generate_do(commander_path: str, target_path: str, output_path: str, fps: int = 20) -> str:
    commander = Image.open(commander_path).convert("RGBA")
    commander = commander.resize(_SELF_SIZE, Image.LANCZOS)
    commander = _make_circle(commander)
    commander = commander.rotate(_SELF_ROTATE, expand=False, resample=Image.BICUBIC)

    target = Image.open(target_path).convert("RGBA")
    target = target.resize(_USER_SIZE, Image.LANCZOS)
    target = _make_circle(target)
    target = target.rotate(_USER_ROTATE, expand=False, resample=Image.BICUBIC)

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
