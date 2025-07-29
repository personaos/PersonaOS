import os
import io
import threading
import time
from typing import Optional, Dict, Any, Callable
import pyaudio
import wave
import numpy as np
from loguru import logger

from .base_stt_handler import BaseSTTHandler

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available. Install with: pip install openai-whisper")

class WhisperSTTHandler(BaseSTTHandler):
    """
    Whisper-based speech-to-text handler for PersonaOS.
    
    Uses OpenAI's Whisper model for local, offline speech recognition.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Whisper STT handler.
        
        Args:
            config: Configuration dictionary containing STT settings
        """
        super().__init__(config)
        
        # Whisper model configuration
        self.model_name = config.get("stt_model", "base")
        self.language = config.get("stt_language", "en")
        self.device_index = config.get("stt_device_index")
        
        # Audio configuration
        self.sample_rate = 16000  # Whisper expects 16kHz
        self.chunk_size = 4096
        self.channels = 1
        self.format = pyaudio.paInt16
        
        # Internal state
        self.model = None
        self.audio_interface = None
        self.stream = None
        self.recording = False
        self.audio_buffer = []
        self.transcription_callback = None
        
        logger.info(f"WhisperSTTHandler initialized with model: {self.model_name}")
    
    def load_model(self) -> bool:
        """
        Load the Whisper model into memory.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        if not WHISPER_AVAILABLE:
            logger.error("Whisper is not available. Cannot load STT model.")
            return False
        
        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            
            # Initialize PyAudio
            self.audio_interface = pyaudio.PyAudio()
            
            self._is_loaded = True
            logger.success(f"Whisper model '{self.model_name}' loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return False
    
    def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe raw audio data to text.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Transcribed text or None if transcription failed
        """
        if not self.is_loaded():
            logger.error("STT model not loaded. Call load_model() first.")
            return None
        
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_array,
                language=self.language if self.language != "auto" else None,
                task="transcribe"
            )
            
            transcribed_text = result["text"].strip()
            logger.debug(f"Transcribed: '{transcribed_text}'")
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    def transcribe_file(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text or None if transcription failed
        """
        if not self.is_loaded():
            logger.error("STT model not loaded. Call load_model() first.")
            return None
        
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None
        
        try:
            result = self.model.transcribe(
                audio_file_path,
                language=self.language if self.language != "auto" else None,
                task="transcribe"
            )
            
            transcribed_text = result["text"].strip()
            logger.debug(f"Transcribed from file: '{transcribed_text}'")
            return transcribed_text
            
        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            return None
    
    def start_streaming_transcription(self, callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Start real-time streaming transcription from microphone.
        
        Args:
            callback: Optional callback function to receive transcribed text
            
        Returns:
            True if streaming started successfully, False otherwise
        """
        if not self.is_loaded():
            logger.error("STT model not loaded. Call load_model() first.")
            return False
        
        if self.recording:
            logger.warning("Streaming transcription already active")
            return True
        
        try:
            self.transcription_callback = callback
            
            # Open audio stream
            self.stream = self.audio_interface.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.recording = True
            self.stream.start_stream()
            
            # Start processing thread
            self.processing_thread = threading.Thread(
                target=self._process_audio_buffer, 
                daemon=True
            )
            self.processing_thread.start()
            
            logger.info("Streaming transcription started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming transcription: {e}")
            return False
    
    def stop_streaming_transcription(self) -> bool:
        """
        Stop streaming transcription and clean up resources.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.recording:
            return True
        
        try:
            self.recording = False
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # Wait for processing thread to finish
            if hasattr(self, 'processing_thread'):
                self.processing_thread.join(timeout=2.0)
            
            self.audio_buffer.clear()
            logger.info("Streaming transcription stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop streaming transcription: {e}")
            return False
    
    def unload_model(self) -> bool:
        """
        Unload the STT model from memory and free resources.
        
        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            # Stop any active transcription
            self.stop_streaming_transcription()
            
            # Clean up audio interface
            if self.audio_interface:
                self.audio_interface.terminate()
                self.audio_interface = None
            
            # Clear model
            self.model = None
            self._is_loaded = False
            
            logger.info("Whisper STT model unloaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload STT model: {e}")
            return False
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio callback for streaming audio data.
        """
        if self.recording:
            self.audio_buffer.append(in_data)
        return (None, pyaudio.paContinue)
    
    def _process_audio_buffer(self):
        """
        Process accumulated audio buffer for transcription.
        Runs in separate thread to avoid blocking audio capture.
        """
        buffer_duration = 3.0  # Process every 3 seconds of audio
        frames_per_buffer = int(self.sample_rate * buffer_duration / self.chunk_size)
        
        while self.recording:
            if len(self.audio_buffer) >= frames_per_buffer:
                # Get accumulated audio data
                audio_frames = self.audio_buffer[:frames_per_buffer]
                self.audio_buffer = self.audio_buffer[frames_per_buffer:]
                
                # Convert to bytes
                audio_data = b''.join(audio_frames)
                
                # Transcribe
                text = self.transcribe_audio(audio_data)
                if text and self.transcription_callback:
                    self.transcription_callback(text)
            
            time.sleep(0.1)  # Small delay to prevent CPU spinning
    
    def validate_config(self) -> bool:
        """
        Validate the configuration for Whisper STT handler.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not super().validate_config():
            return False
        
        # Validate model name
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if self.model_name not in valid_models:
            logger.error(f"Invalid Whisper model: {self.model_name}. Valid options: {valid_models}")
            return False
        
        return True