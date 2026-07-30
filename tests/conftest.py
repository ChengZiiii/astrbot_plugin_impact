import sys
from pathlib import Path

# Add the parent directory to sys.path so that astrbot_plugin_impact is a package.
# The plugin uses relative imports (.impact_store_basic etc.), which require package context.
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Pillow 是运行端（AstrBot 宿主）的生产依赖，开发机上不一定装。
# draw_img / txt2img 在 import 时就 `from PIL import ...`，会让纯逻辑测试
# 直接收集失败，因此在缺失时塞一个假的 PIL 进 sys.modules。
try:  # pragma: no cover - 环境相关
    import PIL  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - 环境相关
    from unittest.mock import MagicMock

    _pil_stub = MagicMock()
    sys.modules.setdefault("PIL", _pil_stub)
    for _sub_module in ("Image", "ImageDraw", "ImageFilter", "ImageFont", "ImageOps", "ImageSequence"):
        sys.modules.setdefault(f"PIL.{_sub_module}", getattr(_pil_stub, _sub_module))
