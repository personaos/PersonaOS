"""
Voice module for PersonaOS.

This module provides voice conversation capabilities including:
- Voice pipeline controller for orchestrating STT → Intent → LLM → TTS flow
- State management for voice conversations
- Integration with existing PersonaOS systems

The voice system maintains compatibility with CLI and web interfaces
while providing natural voice interaction capabilities.
"""

from .voice_pipeline_controller import VoicePipelineController, VoiceState

__all__ = ["VoicePipelineController", "VoiceState"]

# Module metadata
__version__ = "0.1.0"
__author__ = "PersonaOS Development Team"