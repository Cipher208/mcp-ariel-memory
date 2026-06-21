"""
Universal Memory MCP Server
Two-layer unified memory: Layer 1 (user) + Layer 2 (agent identity)
"""
import sys
from pathlib import Path

_pkg_dir = Path(__file__).parent
if str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
