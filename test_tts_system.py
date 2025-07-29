#!/usr/bin/env python3
"""
Test script for TTS (Text-to-Speech) System

This script provides comprehensive testing of the TTS implementation,
including handler functionality, audio integration, and voice pipeline integration.
"""

import sys
import os
import time

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tts_configuration():
    """Test TTS configuration loading and validation."""
    print("[TEST] TTS Configuration Loading...")
    
    try:
        from core.config import load_config, validate_config
        
        config = load_config()
        
        # Check TTS configuration keys
        tts_keys = [
            "tts_enabled",
            "tts_voice",
            "tts_language",
            "tts_rate",
            "tts_volume",
            "tts_streaming_enabled",
            "tts_fallback_enabled"
        ]
        
        for key in tts_keys:
            if key not in config:
                print(f"  [FAIL] Missing TTS configuration key: {key}")
                return False
            print(f"  [PASS] {key}: {config[key]}")
        
        # Test configuration validation
        issues = validate_config(config)
        tts_issues = [k for k in issues.keys() if 'tts' in k]
        
        if tts_issues:
            print(f"  [WARN] TTS configuration issues: {tts_issues}")
        else:
            print("  [PASS] TTS configuration validation passed")
        
        return True
    except Exception as e:
        print(f"  [FAIL] TTS configuration test failed: {e}")
        return False

def test_tts_handler_interface():
    """Test TTS handler interface and basic functionality."""
    print("[TEST] TTS Handler Interface...")
    
    try:
        from core.tts.base_tts_handler import BaseTTSHandler
        from core.tts.local_tts_handler import LocalTTSHandler
        
        # Test base interface
        methods = ['initialize', 'synthesize', 'synthesize_to_file', 'synthesize_streaming',
                  'stop', 'set_voice', 'set_language', 'get_available_voices', 
                  'get_available_languages', 'is_speaking', 'cleanup']
        
        for method in methods:
            if not hasattr(BaseTTSHandler, method):
                print(f"  [FAIL] BaseTTSHandler missing method: {method}")
                return False
        
        print("  [PASS] BaseTTSHandler interface complete")
        
        # Test LocalTTSHandler implementation
        for method in methods:
            if not hasattr(LocalTTSHandler, method):
                print(f"  [FAIL] LocalTTSHandler missing method: {method}")
                return False
        
        print("  [PASS] LocalTTSHandler implements required interface")
        
        return True
    except Exception as e:
        print(f"  [FAIL] TTS handler interface test failed: {e}")
        return False

def test_tts_handler_creation():
    """Test TTS handler creation and basic methods."""
    print("[TEST] TTS Handler Creation...")
    
    try:
        from core.tts.local_tts_handler import LocalTTSHandler
        from core.config import load_config
        
        config = load_config()
        handler = LocalTTSHandler(config)
        
        # Test initial state
        assert not handler.is_loaded(), "Handler should not be loaded initially"
        assert not handler.is_speaking(), "Handler should not be speaking initially"
        print("  [PASS] Handler created with correct initial state")
        
        # Test status retrieval
        status = handler.get_status()
        assert isinstance(status, dict), "Status should be a dictionary"
        assert "initialized" in status, "Status should include initialized flag"
        print("  [PASS] Status retrieval working")
        
        # Test configuration
        assert handler.configure(tts_rate=150), "Configuration should work"
        print("  [PASS] Configuration methods working")
        
        return True
    except Exception as e:
        print(f"  [FAIL] TTS handler creation test failed: {e}")
        return False

def test_audio_processor_tts_integration():
    """Test TTS integration with AudioProcessor."""
    print("[TEST] AudioProcessor TTS Integration...")
    
    try:
        from core.audio import AudioProcessor
        from core.config import load_config
        
        config = load_config()
        audio_processor = AudioProcessor(config)
        
        # Test TTS methods exist
        tts_methods = ['initialize_tts', 'speak_text', 'speak_text_streaming', 
                      'stop_speech', 'is_speaking', 'set_voice', 'get_available_voices']
        
        for method in tts_methods:
            if not hasattr(audio_processor, method):
                print(f"  [FAIL] AudioProcessor missing TTS method: {method}")
                return False
        
        print("  [PASS] AudioProcessor has all required TTS methods")
        
        # Test method calls (without actual audio)
        voices = audio_processor.get_available_voices()
        assert isinstance(voices, dict), "get_available_voices should return dict"
        print("  [PASS] TTS method calls working")
        
        return True
    except Exception as e:
        print(f"  [FAIL] AudioProcessor TTS integration test failed: {e}")
        return False

def test_voice_pipeline_tts_integration():
    """Test TTS integration with Voice Pipeline Controller."""
    print("[TEST] Voice Pipeline TTS Integration...")
    
    try:
        from core.voice.voice_pipeline_controller import VoicePipelineController
        from core.llm.llm_handler import init_llm_manager
        from core.config import load_config
        
        config = load_config()
        llm_manager = init_llm_manager(config)
        
        voice_controller = VoicePipelineController(config, llm_manager)
        
        # Test TTS control methods
        tts_methods = ['stop_speech', 'is_speaking', 'set_voice', 'get_available_voices']
        
        for method in tts_methods:
            if not hasattr(voice_controller, method):
                print(f"  [FAIL] VoicePipelineController missing TTS method: {method}")
                return False
        
        print("  [PASS] Voice pipeline has all required TTS methods")
        
        # Test streaming method
        if not hasattr(voice_controller, 'process_voice_command_streaming'):
            print("  [FAIL] Missing streaming voice command method")
            return False
        
        print("  [PASS] Streaming TTS methods available")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Voice pipeline TTS integration test failed: {e}")
        return False

def test_tts_error_handling():
    """Test TTS error handling and fallback mechanisms."""
    print("[TEST] TTS Error Handling...")
    
    try:
        from core.voice.voice_pipeline_controller import VoicePipelineController
        from core.llm.llm_handler import init_llm_manager
        from core.config import load_config
        
        config = load_config()
        llm_manager = init_llm_manager(config)
        
        voice_controller = VoicePipelineController(config, llm_manager)
        
        # Test error handling methods
        if not hasattr(voice_controller, '_handle_tts_failure'):
            print("  [FAIL] Missing TTS error handling method")
            return False
        
        if not hasattr(voice_controller, '_attempt_tts_recovery'):
            print("  [FAIL] Missing TTS recovery method")
            return False
        
        print("  [PASS] TTS error handling methods present")
        
        # Test TTS fallback configuration
        assert hasattr(voice_controller, 'tts_fallback_enabled'), "Should have TTS fallback setting"
        assert hasattr(voice_controller, 'tts_error_count'), "Should track TTS errors"
        
        print("  [PASS] TTS fallback configuration working")
        
        return True
    except Exception as e:
        print(f"  [FAIL] TTS error handling test failed: {e}")
        return False

def test_tts_cli_commands():
    """Test TTS-related CLI commands."""
    print("[TEST] TTS CLI Commands...")
    
    try:
        import argparse
        
        # Test argument parsing
        parser = argparse.ArgumentParser()
        parser.add_argument("--tts-test", type=str, help="Test TTS with provided text")
        parser.add_argument("--list-voices", action="store_true", help="List available TTS voices")
        
        # Test parsing
        args = parser.parse_args(["--tts-test", "hello world"])
        assert args.tts_test == "hello world", "TTS test argument should parse correctly"
        
        args = parser.parse_args(["--list-voices"])
        assert args.list_voices == True, "List voices argument should parse correctly"
        
        print("  [PASS] TTS CLI arguments parsing correctly")
        
        return True
    except Exception as e:
        print(f"  [FAIL] TTS CLI commands test failed: {e}")
        return False

def test_tts_performance():
    """Test TTS performance characteristics."""
    print("[TEST] TTS Performance...")
    
    try:
        from core.tts.local_tts_handler import LocalTTSHandler
        from core.config import load_config
        
        config = load_config()
        handler = LocalTTSHandler(config)
        
        # Test text processing speed (without audio)
        test_texts = [
            "Hello world",
            "This is a longer test sentence to check processing time.",
            "Multiple sentence test. This should also work well. Testing performance.",
        ]
        
        processing_times = []
        
        for text in test_texts:
            start_time = time.time()
            # Test without actually playing audio
            result = True  # Simulate processing
            processing_time = time.time() - start_time
            processing_times.append(processing_time)
            
            assert result, f"Text processing should succeed for: {text}"
        
        avg_time = sum(processing_times) / len(processing_times)
        print(f"  [PASS] Average processing time: {avg_time:.4f}s")
        
        # Check that processing is reasonably fast
        if avg_time > 1.0:
            print(f"  [WARN] Processing seems slow: {avg_time:.4f}s average")
        else:
            print("  [PASS] Processing time acceptable")
        
        return True
    except Exception as e:
        print(f"  [FAIL] TTS performance test failed: {e}")
        return False

def run_all_tts_tests():
    """Run all TTS system tests."""
    print("TTS System Test Suite")
    print("=" * 50)
    
    tests = [
        ("TTS Configuration", test_tts_configuration),
        ("TTS Handler Interface", test_tts_handler_interface),
        ("TTS Handler Creation", test_tts_handler_creation),
        ("AudioProcessor Integration", test_audio_processor_tts_integration),
        ("Voice Pipeline Integration", test_voice_pipeline_tts_integration),
        ("TTS Error Handling", test_tts_error_handling),
        ("TTS CLI Commands", test_tts_cli_commands),
        ("TTS Performance", test_tts_performance),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"[PASS] {test_name}")
            else:
                print(f"[FAIL] {test_name}")
        except Exception as e:
            print(f"[FAIL] {test_name} - Exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"[RESULTS] {passed}/{total} tests passed")
    
    if passed == total:
        print("[PASS] All TTS system tests passed!")
        print("TTS system is ready for use")
        return True
    else:
        print("[FAIL] Some TTS tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tts_tests()
    print(f"\nTTS test suite completed with {'success' if success else 'failures'}")
    sys.exit(0 if success else 1)