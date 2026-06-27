from __future__ import annotations

from PIL import Image

from .common import make_circle, resource_frames_dir, save_gif

_FRAMES_DIR = resource_frames_dir(__file__, "lash_frames")
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


def generate_lash(commander_path: str, target_path: str, output_path: str, fps: int = 20) -> str:
    commander = Image.open(commander_path).convert("RGBA")
    commander = commander.resize(_SELF_SIZE, Image.LANCZOS)
    commander = make_circle(commander)

    target = Image.open(target_path).convert("RGBA")
    target = target.resize(_USER_SIZE, Image.LANCZOS)
    target = make_circle(target)
    rotated = target.rotate(_USER_ROTATE, expand=True, resample=Image.BICUBIC)
    left = (rotated.width - _USER_SIZE[0]) // 2
    top = (rotated.height - _USER_SIZE[1]) // 2
    target = rotated.crop((left, top, left + _USER_SIZE[0], top + _USER_SIZE[1]))

    frames: list[Image.Image] = []
    for index in range(_FRAME_COUNT):
        overlay = Image.open(_FRAMES_DIR / f"{index}.png").convert("RGBA")
        canvas = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        canvas.paste(overlay, (0, 0), overlay)
        canvas.paste(commander, _SELF_LOCS[index], commander)
        canvas.paste(target, _USER_LOCS[index], target)
        frames.append(canvas)

    return save_gif(output_path, frames, fps)
