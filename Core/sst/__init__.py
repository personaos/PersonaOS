"""
Speech-to-Text (STT) module for PersonaOS.

This module provides speech recognition capabilities using various STT engines,
with Whisper as the primary local STT implementation.
"""

from .base_stt_handler import BaseSTTHandler
from .whisper_stt_handler import WhisperSTTHandler
from .voice_to_intent_bridge import VoiceToIntentBridge

__all__ = ["BaseSTTHandler", "WhisperSTTHandler", "VoiceToIntentBridge"]

# Module metadata
__version__ = "0.1.0"
__author__ = "PersonaOS Development Team"