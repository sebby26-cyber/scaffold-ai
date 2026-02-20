"""
help — Context-aware help/guide system for Scaffold AI.

Owns: help model, builder, terminal renderer, JSON output.
"""

from .model import HelpGuide
from .builder import generate_help
from .renderer import render_help_terminal
from .json_output import render_help_json

__all__ = [
    "HelpGuide",
    "generate_help",
    "render_help_terminal",
    "render_help_json",
]
