"""
json_output.py — JSON output for HelpGuide.

The JSON representation IS the help model. Terminal output derives from it.
"""

from __future__ import annotations

import json

from .model import HelpGuide


def render_help_json(guide: HelpGuide, indent: int = 2) -> str:
    """Serialize a HelpGuide to JSON string."""
    return json.dumps(guide.to_dict(), indent=indent, ensure_ascii=False)
