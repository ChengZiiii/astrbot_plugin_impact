from __future__ import annotations

from PIL import Image

from .common import make_circle, resource_frames_dir, save_gif

_FRAMES_DIR = resource_frames_dir(__file__, "do_frames")
_FRAME_COUNT = 3
_SELF_LOCS = [(116, -8), (109, 3), (130, -10)]
_SELF_SIZE = (122, 122)
_SELF_ROTATE = -15.0
_USER_LOCS = [(2, 177), (12, 172), (6, 158)]
_USER_SIZE = (112, 112)
_USER_ROTATE = 90.0


def generate_do(commander_path: str, target_path: str, output_path: str, fps: int = 20) -> str:
    commander = Image.open(commander_path).convert("RGBA")
    commander = commander.resize(_SELF_SIZE, Image.LANCZOS)
    commander = make_circle(commander)
    commander = commander.rotate(_SELF_ROTATE, expand=False, resample=Image.BICUBIC)

    target = Image.open(target_path).convert("RGBA")
    target = target.resize(_USER_SIZE, Image.LANCZOS)
    target = make_circle(target)
    target = target.rotate(_USER_ROTATE, expand=False, resample=Image.BICUBIC)

    frames: list[Image.Image] = []
    for index in range(_FRAME_COUNT):
        overlay = Image.open(_FRAMES_DIR / f"{index}.png").convert("RGBA")
        canvas = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        canvas.paste(overlay, (0, 0), overlay)
        canvas.paste(commander, _SELF_LOCS[index], commander)
        canvas.paste(target, _USER_LOCS[index], target)
        frames.append(canvas)

    return save_gif(output_path, frames, fps)
