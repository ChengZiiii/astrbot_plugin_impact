# Avatar GIF Templates

`avatar_gif/` uses JSON template definitions so contributors can add most new two-avatar GIF templates without writing Python.

## How To Add A New Template

1. Put frame assets under `resource/avatar_gif/<template_name>_frames/`.
2. Add `avatar_gif/templates/<template_name>.json`.
3. Reference the template name in `pk_avatar_gif_styles` or `yinpa_avatar_gif_styles`.

## Template JSON Fields

- `name`: template name used in config
- `frames_dir`: resource folder name under `resource/avatar_gif/`
- `frame_count`: number of frames to load, starting at `0.png`
- `fps`: output frame rate
- `commander`: sender avatar placement config
- `target`: target avatar placement config

Each placement object supports:

- `size`: `[width, height]`
- `rotate_degrees`: rotation angle
- `rotate_mode`: `none`, `simple`, or `crop`
- `locations`: per-frame `[x, y]` positions

## Compatibility

- Config values support both canonical names and `_frames` suffixes.
- Example: `do` and `do_frames` both resolve to the `do` template.

## When Python Is Still Needed

Most two-avatar overlays can stay fully data-driven.
Only add new Python rendering code when a template needs behavior the generic renderer cannot express, such as perspective warps, nonuniform masks, or frame-specific custom compositing.
