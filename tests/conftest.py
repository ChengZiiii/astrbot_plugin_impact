import sys
from pathlib import Path

# Add the parent directory to sys.path so that astrbot_plugin_impact is a package.
# The plugin uses relative imports (.impact_store_basic etc.), which require package context.
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
