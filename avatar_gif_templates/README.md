# Avatar GIF Template Development

`avatar_gif_templates/` stores the code-side template system.
Frame images still belong in `resource/avatar_gif/`.

## How To Add A New Template

1. Put frame assets under `resource/avatar_gif/<template_name>_frames/`.
2. Add `avatar_gif_templates/templates/<template_name>.json`.
3. Reference the template name in `pk_avatar_gif_styles` or `yinpa_avatar_gif_styles`.

## Minimal JSON Example

```json
{
  "name": "example",
  "frames_dir": "example_frames",
  "frame_count": 2,
  "fps": 20,
  "commander": {
    "size": [64, 64],
    "rotate_degrees": 0.0,
    "rotate_mode": "none",
    "locations": [[10, 10], [12, 12]]
  },
  "target": {
    "size": [64, 64],
    "rotate_degrees": 15.0,
    "rotate_mode": "simple",
    "locations": [[100, 100], [102, 98]]
  }
}
```

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
