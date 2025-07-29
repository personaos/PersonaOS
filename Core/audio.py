import pvporcupine
import pyaudio
import struct
import threading
import time
import wave
import io
from typing import Optional, Callable, Dict, Any
from loguru import logger

from .sst import WhisperSTTHandler
from .tts import LocalTTSHandler

class AudioProcessor:
    """
    Central audio processing utility for PersonaOS.
    Handles microphone capture, audio streaming, and STT integration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the audio processor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.audio_interface = pyaudio.PyAudio()
        self.stt_handler = None
        self.tts_handler = None
        
        # Audio settings
        self.sample_rate = 16000
        self.channels = 1
        self.format = pyaudio.paInt16
        self.chunk_size = 4096
        
        # Audio device management
        self.input_device_id = config.get("mic_device_index")
        self.output_device_id = config.get("speaker_device_index")
        
        logger.info("AudioProcessor initialized")
    
    def initialize_stt(self) -> bool:
        """
        Initialize the STT handler if enabled in configuration.
        
        Returns:
            True if STT initialized successfully, False otherwise
        """
        if not self.config.get("stt_enabled", False):
            logger.info("STT disabled in configuration")
            return False
        
        try:
            self.stt_handler = WhisperSTTHandler(self.config)
            if self.stt_handler.load_model():
                logger.success("STT handler initialized successfully")
                return True
            else:
                logger.error("Failed to load STT model")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize STT: {e}")
            return False
    
    def initialize_tts(self) -> bool:
        """
        Initialize the TTS handler if enabled in configuration.
        
        Returns:
            True if TTS initialized successfully, False otherwise
        """
        if not self.config.get("tts_enabled", False):
            logger.info("TTS disabled in configuration")
            return False
        
        try:
            self.tts_handler = LocalTTSHandler(self.config)
            if self.tts_handler.initialize():
                logger.success("TTS handler initialized successfully")
                return True
            else:
                logger.error("Failed to initialize TTS handler")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
            return False
    
    def start_voice_input(self, text_callback: Callable[[str], None]) -> bool:
        """
        Start capturing voice input and converting to text.
        
        Args:
            text_callback: Function to call with transcribed text
            
        Returns:
            True if voice input started successfully, False otherwise
        """
        if not self.stt_handler:
            logger.error("STT not initialized. Call initialize_stt() first.")
            return False
        
        return self.stt_handler.start_streaming_transcription(text_callback)
    
    def stop_voice_input(self) -> bool:
        """
        Stop voice input capture.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.stt_handler:
            return self.stt_handler.stop_streaming_transcription()
        return True
    
    def transcribe_audio_file(self, file_path: str) -> Optional[str]:
        """
        Transcribe an audio file to text.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Transcribed text or None if failed
        """
        if not self.stt_handler:
            logger.error("STT not initialized")
            return None
        
        return self.stt_handler.transcribe_file(file_path)
    
    def speak_text(self, text: str, **kwargs) -> bool:
        """
        Convert text to speech and play audio.
        
        Args:
            text: Text to convert to speech
            **kwargs: Additional TTS parameters
            
        Returns:
            True if TTS successful, False otherwise
        """
        if not self.tts_handler:
            logger.error("TTS not initialized. Call initialize_tts() first.")
            return False
        
        return self.tts_handler.synthesize(text, **kwargs)
    
    def speak_text_streaming(self, text_generator, **kwargs) -> bool:
        """
        Convert streaming text to speech for real-time audio output.
        
        Args:
            text_generator: Generator yielding text chunks
            **kwargs: Additional TTS parameters
            
        Returns:
            True if streaming TTS started successfully, False otherwise
        """
        if not self.tts_handler:
            logger.error("TTS not initialized. Call initialize_tts() first.")
            return False
        
        return self.tts_handler.synthesize_streaming(text_generator, **kwargs)
    
    def stop_speech(self) -> bool:
        """
        Stop current TTS playback.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.tts_handler:
            return self.tts_handler.stop()
        return True
    
    def is_speaking(self) -> bool:
        """
        Check if TTS is currently playing audio.
        
        Returns:
            True if currently speaking, False otherwise
        """
        if self.tts_handler:
            return self.tts_handler.is_speaking()
        return False
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set the TTS voice.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if voice set successfully, False otherwise
        """
        if not self.tts_handler:
            logger.error("TTS not initialized")
            return False
        
        return self.tts_handler.set_voice(voice_id)
    
    def get_available_voices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available TTS voices.
        
        Returns:
            Dictionary of available voices
        """
        if self.tts_handler:
            return self.tts_handler.get_available_voices()
        return {}
    
    def get_audio_devices(self) -> Dict[str, Any]:
        """
        Get information about available audio devices.
        
        Returns:
            Dictionary with input and output device information
        """
        try:
            info = self.audio_interface.get_host_api_info_by_index(0)
            device_count = info.get('deviceCount', 0)
            
            input_devices = []
            output_devices = []
            
            for i in range(device_count):
                device_info = self.audio_interface.get_device_info_by_host_api_device_index(0, i)
                
                device_data = {
                    "index": i,
                    "name": device_info.get('name', 'Unknown'),
                    "max_input_channels": device_info.get('maxInputChannels', 0),
                    "max_output_channels": device_info.get('maxOutputChannels', 0),
                    "default_sample_rate": device_info.get('defaultSampleRate', 0)
                }
                
                if device_info.get('maxInputChannels', 0) > 0:
                    input_devices.append(device_data)
                
                if device_info.get('maxOutputChannels', 0) > 0:
                    output_devices.append(device_data)
            
            return {
                "input_devices": input_devices,
                "output_devices": output_devices,
                "current_input": self.input_device_id,
                "current_output": self.output_device_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio devices: {e}")
            return {"input_devices": [], "output_devices": [], "current_input": None, "current_output": None}
    
    def record_audio_to_file(self, duration: float, output_path: str) -> bool:
        """
        Record audio from microphone to a file.
        
        Args:
            duration: Recording duration in seconds
            output_path: Path to save the audio file
            
        Returns:
            True if recording successful, False otherwise
        """
        try:
            # Open stream
            stream = self.audio_interface.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            logger.info(f"Recording audio for {duration} seconds...")
            frames = []
            
            for _ in range(int(self.sample_rate / self.chunk_size * duration)):
                data = stream.read(self.chunk_size)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # Save to file
            with wave.open(output_path, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio_interface.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            
            logger.success(f"Audio saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record audio: {e}")
            return False
    
    def cleanup(self):
        """Clean up audio resources."""
        try:
            if self.stt_handler:
                self.stt_handler.unload_model()
            if self.tts_handler:
                self.tts_handler.cleanup()
            self.audio_interface.terminate()
            logger.info("AudioProcessor cleaned up")
        except Exception as e:
            logger.error(f"Error during audio cleanup: {e}")

class PorcupineHotword:
    def __init__(self, keyword_paths=None, sensitivities=None):
        self.porcupine = pvporcupine.create(
            keyword_paths=keyword_paths,
            sensitivities=sensitivities or [0.5]
        )
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )
        self.running = False
        self.callback = None  # to be set to function called on hotword detect

    def start(self, callback):
        self.callback = callback
        self.running = True
        threading.Thread(target=self._process_audio, daemon=True).start()

    def _process_audio(self):
        while self.running:
            pcm = self.stream.read(self.porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            result = self.porcupine.process(pcm_unpacked)
            if result >= 0:
                if self.callback:
                    self.callback()  # Hotword detected!

    def stop(self):
        self.running = False
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
        self.porcupine.delete()
