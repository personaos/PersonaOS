#!/usr/bin/env python3
"""
Test script for Voice Pipeline Controller

This script provides basic validation of the voice pipeline controller
functionality, including state management, error handling, and configuration.
"""

import sys
import os
import time

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import load_config
from core.llm.llm_handler import init_llm_manager
from core.llm.memory import MemoryManager
from core.voice.voice_pipeline_controller import VoicePipelineController, VoiceState

def test_voice_pipeline_initialization():
    """Test voice pipeline controller initialization."""
    print("🧪 Testing Voice Pipeline Initialization...")
    
    # Load configuration
    config = load_config()
    
    # Initialize dependencies
    llm_manager = init_llm_manager(config)
    memory = MemoryManager(config) if config.get("memory_enabled", True) else None
    
    # Test controller creation
    voice_controller = VoicePipelineController(config, llm_manager, memory)
    
    # Test initial state
    assert voice_controller.get_state() == VoiceState.DISABLED, "Initial state should be DISABLED"
    print("  ✅ Controller created with correct initial state")
    
    # Test status retrieval
    status = voice_controller.get_status()
    assert isinstance(status, dict), "Status should be a dictionary"
    assert "state" in status, "Status should include state"
    assert "config" in status, "Status should include config"
    print("  ✅ Status retrieval working")
    
    # Test error status
    error_status = voice_controller.get_error_status()
    assert error_status["error_count"] == 0, "Initial error count should be 0"
    assert error_status["consecutive_failures"] == 0, "Initial consecutive failures should be 0"
    print("  ✅ Error status tracking initialized correctly")
    
    return voice_controller

def test_voice_pipeline_configuration():
    """Test voice pipeline configuration integration."""
    print("🧪 Testing Voice Pipeline Configuration...")
    
    # Test configuration loading
    config = load_config()
    
    # Check that voice pipeline settings exist
    voice_settings = [
        "voice_pipeline_enabled",
        "voice_auto_start", 
        "voice_response_timeout",
        "voice_state_callbacks",
        "voice_metrics_enabled",
        "voice_fallback_enabled",
        "voice_max_retries"
    ]
    
    for setting in voice_settings:
        assert setting in config, f"Configuration should include {setting}"
    
    print("  ✅ All voice pipeline configuration settings present")
    
    # Test configuration validation
    from core.config import validate_config
    issues = validate_config(config)
    
    # Should not have issues with default configuration
    voice_issues = {k: v for k, v in issues.items() if "voice" in k}
    assert not voice_issues, f"Default voice configuration should be valid, but found: {voice_issues}"
    print("  ✅ Voice configuration validation working")

def test_voice_pipeline_state_management():
    """Test voice pipeline state management."""
    print("🧪 Testing Voice Pipeline State Management...")
    
    config = load_config()
    llm_manager = init_llm_manager(config)
    memory = MemoryManager(config) if config.get("memory_enabled", True) else None
    
    voice_controller = VoicePipelineController(config, llm_manager, memory)
    
    # Test state transitions
    initial_state = voice_controller.get_state()
    assert initial_state == VoiceState.DISABLED, "Should start in DISABLED state"
    print("  ✅ Initial state correct")
    
    # Test state availability check
    assert not voice_controller.is_voice_available(), "Voice should not be available initially"
    print("  ✅ Voice availability check working")
    
    # Test callbacks system
    callback_called = {"count": 0}
    
    def test_callback(old_state, new_state):
        callback_called["count"] += 1
    
    voice_controller.set_callbacks(state_change_callback=test_callback)
    
    # Force a state change to test callbacks
    voice_controller._set_state(VoiceState.IDLE)
    assert callback_called["count"] == 1, "State change callback should have been called"
    print("  ✅ State change callbacks working")

def test_voice_pipeline_error_handling():
    """Test voice pipeline error handling."""
    print("🧪 Testing Voice Pipeline Error Handling...")
    
    config = load_config()
    llm_manager = init_llm_manager(config)
    memory = MemoryManager(config) if config.get("memory_enabled", True) else None
    
    voice_controller = VoicePipelineController(config, llm_manager, memory)
    
    # Test error tracking
    initial_error_count = voice_controller.error_count
    
    # Simulate an error
    test_error = Exception("Test error")
    voice_controller._handle_pipeline_error(test_error, "test_context")
    
    # Check error tracking
    assert voice_controller.error_count == initial_error_count + 1, "Error count should increment"
    assert voice_controller.consecutive_failures == 1, "Consecutive failures should increment"
    assert voice_controller.get_state() == VoiceState.ERROR, "State should be ERROR after error"
    print("  ✅ Error tracking working")
    
    # Test error status retrieval
    error_status = voice_controller.get_error_status()
    assert error_status["last_error"] is not None, "Should have last error information"
    assert error_status["last_error"]["context"] == "test_context", "Should track error context"
    print("  ✅ Error status reporting working")
    
    # Test fallback callback
    fallback_called = {"message": None}
    
    def test_fallback(message):
        fallback_called["message"] = message
    
    voice_controller.set_fallback_callback(test_fallback)
    
    # Test recovery tracking
    voice_controller._reset_error_tracking()
    assert voice_controller.consecutive_failures == 0, "Error tracking should reset"
    print("  ✅ Error recovery tracking working")

def test_voice_pipeline_direct_processing():
    """Test direct voice command processing."""
    print("🧪 Testing Voice Pipeline Direct Processing...")
    
    config = load_config()
    llm_manager = init_llm_manager(config)
    memory = MemoryManager(config) if config.get("memory_enabled", True) else None
    
    voice_controller = VoicePipelineController(config, llm_manager, memory)
    
    # Test direct command processing
    test_command = "Hello, this is a test command"
    result = voice_controller.process_voice_command_direct(test_command)
    
    # Check result structure
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "action" in result, "Result should include action"
    assert "input_type" in result, "Result should include input_type"
    assert result["input_type"] == "voice_direct", "Input type should be voice_direct"
    print("  ✅ Direct voice command processing working")

def test_voice_pipeline_performance():
    """Test voice pipeline performance characteristics."""
    print("🧪 Testing Voice Pipeline Performance...")
    
    config = load_config()
    llm_manager = init_llm_manager(config)
    memory = MemoryManager(config) if config.get("memory_enabled", True) else None
    
    voice_controller = VoicePipelineController(config, llm_manager, memory)
    
    # Test multiple direct commands to check performance
    commands = [
        "What time is it?",
        "Hello PersonaOS",
        "How are you?",
        "Test command 1",
        "Test command 2"
    ]
    
    start_time = time.time()
    
    for command in commands:
        result = voice_controller.process_voice_command_direct(command)
        assert "processing_time" in result, "Should track processing time"
    
    total_time = time.time() - start_time
    average_time = total_time / len(commands)
    
    print(f"  📊 Processed {len(commands)} commands in {total_time:.2f}s")
    print(f"  📊 Average processing time: {average_time:.2f}s per command")
    
    # Check if metrics are being tracked
    if voice_controller.metrics_enabled:
        status = voice_controller.get_status()
        if status["metrics"]:
            print(f"  📊 Controller metrics: {status['metrics']['total_conversations']} conversations")
            print("  ✅ Performance metrics tracking working")
    
    print("  ✅ Performance testing completed")

def run_all_tests():
    """Run all voice pipeline tests."""
    print("🎤 Voice Pipeline Controller Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        voice_controller = test_voice_pipeline_initialization()
        test_voice_pipeline_configuration()
        test_voice_pipeline_state_management()
        test_voice_pipeline_error_handling()
        test_voice_pipeline_direct_processing()
        test_voice_pipeline_performance()
        
        print("\n" + "=" * 50)
        print("✅ All voice pipeline tests passed!")
        print("🎤 Voice Pipeline Controller is ready for use")
        
        # Cleanup
        if voice_controller:
            voice_controller.cleanup()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)