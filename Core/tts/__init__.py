"""
Text-to-Speech (TTS) module for PersonaOS.

This module provides local text-to-speech capabilities for converting
LLM responses and system messages into natural speech output.

The TTS system is designed to be:
- Fully offline and local (no external API calls)
- Modular and pluggable (different TTS engines can be used)
- Integrated with the voice pipeline controller
- Privacy-focused (no data leaves the local system)
"""

from .base_tts_handler import BaseTTSHandler
from .local_tts_handler import LocalTTSHandler

__all__ = ["BaseTTSHandler", "LocalTTSHandler"]

# Module metadata
__version__ = "0.1.0"
__author__ = "PersonaOS Development Team"