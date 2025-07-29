"""
Unit tests for PersonaOS Speech-to-Text system.

This module tests the STT components including the Whisper handler,
audio processing, and voice-to-intent bridge.
"""

import unittest
import tempfile
import os
import wave
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Test configuration
TEST_CONFIG = {
    "stt_enabled": True,
    "stt_model": "base",
    "stt_language": "en",
    "stt_device_index": None,
    "intent_enabled": True,
    "safety_level": "standard"
}

class TestWhisperSTTHandler(unittest.TestCase):
    """Test cases for WhisperSTTHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        from .whisper_stt_handler import WhisperSTTHandler
        self.handler = WhisperSTTHandler(TEST_CONFIG)
    
    def test_initialization(self):
        """Test handler initialization."""
        self.assertEqual(self.handler.model_name, "base")
        self.assertEqual(self.handler.language, "en")
        self.assertFalse(self.handler.is_loaded())
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        self.assertTrue(self.handler.validate_config())
        
        # Invalid model
        invalid_handler = WhisperSTTHandler({
            "stt_enabled": True,
            "stt_model": "invalid_model",
            "stt_language": "en"
        })
        self.assertFalse(invalid_handler.validate_config())
    
    @patch('core.sst.whisper_stt_handler.whisper')
    @patch('core.sst.whisper_stt_handler.pyaudio')
    def test_load_model_success(self, mock_pyaudio, mock_whisper):
        """Test successful model loading."""
        mock_whisper.load_model.return_value = Mock()
        mock_pyaudio.PyAudio.return_value = Mock()
        
        result = self.handler.load_model()
        
        self.assertTrue(result)
        self.assertTrue(self.handler.is_loaded())
        mock_whisper.load_model.assert_called_once_with("base")
    
    @patch('core.sst.whisper_stt_handler.WHISPER_AVAILABLE', False)
    def test_load_model_whisper_unavailable(self):
        """Test model loading when Whisper is not available."""
        result = self.handler.load_model()
        
        self.assertFalse(result)
        self.assertFalse(self.handler.is_loaded())
    
    @patch('core.sst.whisper_stt_handler.whisper')
    @patch('core.sst.whisper_stt_handler.pyaudio')
    def test_transcribe_audio(self, mock_pyaudio, mock_whisper):
        """Test audio transcription."""
        # Mock model
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "Hello world"}
        self.handler.model = mock_model
        self.handler._is_loaded = True
        
        # Create test audio data
        test_audio = np.array([1, 2, 3, 4], dtype=np.int16).tobytes()
        
        result = self.handler.transcribe_audio(test_audio)
        
        self.assertEqual(result, "Hello world")
        mock_model.transcribe.assert_called_once()
    
    def test_transcribe_audio_not_loaded(self):
        """Test transcription when model is not loaded."""
        result = self.handler.transcribe_audio(b"test_audio")
        
        self.assertIsNone(result)
    
    def test_transcribe_file_not_found(self):
        """Test file transcription with non-existent file."""
        self.handler._is_loaded = True
        self.handler.model = Mock()
        
        result = self.handler.transcribe_file("non_existent_file.wav")
        
        self.assertIsNone(result)
    
    @patch('core.sst.whisper_stt_handler.whisper')
    @patch('core.sst.whisper_stt_handler.pyaudio')
    def test_unload_model(self, mock_pyaudio, mock_whisper):
        """Test model unloading."""
        # Set up loaded state
        self.handler.model = Mock()
        self.handler.audio_interface = Mock()
        self.handler._is_loaded = True
        
        result = self.handler.unload_model()
        
        self.assertTrue(result)
        self.assertFalse(self.handler.is_loaded())
        self.assertIsNone(self.handler.model)

class TestAudioProcessor(unittest.TestCase):
    """Test cases for AudioProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..audio import AudioProcessor
        self.processor = AudioProcessor(TEST_CONFIG)
    
    @patch('core.sst.whisper_stt_handler.WhisperSTTHandler')
    def test_initialize_stt_enabled(self, mock_handler_class):
        """Test STT initialization when enabled."""
        mock_handler = Mock()
        mock_handler.load_model.return_value = True
        mock_handler_class.return_value = mock_handler
        
        result = self.processor.initialize_stt()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.processor.stt_handler)
    
    def test_initialize_stt_disabled(self):
        """Test STT initialization when disabled."""
        config = TEST_CONFIG.copy()
        config["stt_enabled"] = False
        processor = AudioProcessor(config)
        
        result = processor.initialize_stt()
        
        self.assertFalse(result)
        self.assertIsNone(processor.stt_handler)
    
    def test_start_voice_input_no_stt(self):
        """Test starting voice input without STT initialized."""
        callback = Mock()
        
        result = self.processor.start_voice_input(callback)
        
        self.assertFalse(result)
    
    @patch('pyaudio.PyAudio')
    @patch('wave.open')
    def test_record_audio_to_file(self, mock_wave_open, mock_pyaudio):
        """Test audio recording to file."""
        # Mock audio stream
        mock_stream = Mock()
        mock_stream.read.return_value = b"test_audio_data"
        
        mock_audio_interface = Mock()
        mock_audio_interface.open.return_value = mock_stream
        mock_audio_interface.get_sample_size.return_value = 2
        
        mock_pyaudio.return_value = mock_audio_interface
        self.processor.audio_interface = mock_audio_interface
        
        # Mock wave file
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file
        
        result = self.processor.record_audio_to_file(1.0, "test.wav")
        
        self.assertTrue(result)
        mock_wave_open.assert_called_once_with("test.wav", 'wb')

class TestVoiceToIntentBridge(unittest.TestCase):
    """Test cases for VoiceToIntentBridge."""
    
    def setUp(self):
        """Set up test fixtures."""
        from .voice_to_intent_bridge import VoiceToIntentBridge
        self.bridge = VoiceToIntentBridge(TEST_CONFIG)
    
    @patch('core.sst.voice_to_intent_bridge.AudioProcessor')
    @patch('core.sst.voice_to_intent_bridge.IntentProcessor')
    def test_initialization(self, mock_intent_processor, mock_audio_processor):
        """Test bridge initialization."""
        bridge = VoiceToIntentBridge(TEST_CONFIG)
        
        self.assertIsNotNone(bridge.audio_processor)
        self.assertIsNotNone(bridge.intent_processor)
        self.assertFalse(bridge.voice_active)
    
    def test_initialize_stt_disabled(self):
        """Test initialization when STT is disabled."""
        config = TEST_CONFIG.copy()
        config["stt_enabled"] = False
        bridge = VoiceToIntentBridge(config)
        
        result = bridge.initialize()
        
        self.assertFalse(result)
    
    @patch('core.sst.voice_to_intent_bridge.AudioProcessor')
    def test_initialize_stt_enabled(self, mock_audio_processor_class):
        """Test initialization when STT is enabled."""
        mock_processor = Mock()
        mock_processor.initialize_stt.return_value = True
        mock_audio_processor_class.return_value = mock_processor
        
        bridge = VoiceToIntentBridge(TEST_CONFIG)
        bridge.audio_processor = mock_processor
        
        result = bridge.initialize()
        
        self.assertTrue(result)
    
    @patch('core.sst.voice_to_intent_bridge.IntentProcessor')
    def test_process_voice_command(self, mock_intent_processor_class):
        """Test voice command processing."""
        # Mock intent processor
        mock_processor = Mock()
        mock_processor.process.return_value = {
            "intent": "safe_response",
            "action": "llm_response",
            "user_input": "test command"
        }
        
        bridge = VoiceToIntentBridge(TEST_CONFIG)
        bridge.intent_processor = mock_processor
        
        result = bridge.process_voice_command("test command")
        
        self.assertEqual(result["input_type"], "voice")
        self.assertEqual(result["original_text"], "test command")
        mock_processor.process.assert_called_once_with("test command")
    
    def test_get_status(self):
        """Test status reporting."""
        status = self.bridge.get_status()
        
        self.assertIn("voice_active", status)
        self.assertIn("stt_enabled", status)
        self.assertIn("stt_model", status)
        self.assertIn("stt_language", status)

class TestSTTIntegration(unittest.TestCase):
    """Integration tests for the complete STT system."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.config = TEST_CONFIG.copy()
    
    def create_test_audio_file(self, duration=1.0):
        """Create a test audio file for testing."""
        # Generate simple sine wave
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.3  # 440 Hz tone
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        
        # Write audio data
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
        
        return temp_file.name
    
    @patch('core.sst.whisper_stt_handler.whisper')
    def test_file_transcription_integration(self, mock_whisper):
        """Test complete file transcription workflow."""
        # Mock Whisper
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "Integration test successful"}
        mock_whisper.load_model.return_value = mock_model
        
        # Create test audio file
        audio_file = self.create_test_audio_file()
        
        try:
            from .voice_to_intent_bridge import VoiceToIntentBridge
            bridge = VoiceToIntentBridge(self.config)
            
            # Initialize and transcribe
            if bridge.initialize():
                result = bridge.transcribe_audio_file(audio_file)
                
                self.assertIsNotNone(result)
                self.assertEqual(result["input_type"], "voice")
                self.assertEqual(result["original_text"], "Integration test successful")
        
        finally:
            # Clean up temp file
            if os.path.exists(audio_file):
                os.unlink(audio_file)
    
    def test_configuration_validation(self):
        """Test configuration validation across components."""
        from ..config import validate_config
        
        # Test valid configuration
        issues = validate_config(self.config)
        self.assertEqual(len(issues), 0)
        
        # Test invalid STT model
        invalid_config = self.config.copy()
        invalid_config["stt_model"] = "invalid_model"
        issues = validate_config(invalid_config)
        self.assertIn("stt_model", issues)

def run_stt_tests():
    """Run all STT tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestWhisperSTTHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestVoiceToIntentBridge))
    suite.addTests(loader.loadTestsFromTestCase(TestSTTIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    # Run tests when executed directly
    success = run_stt_tests()
    exit(0 if success else 1)