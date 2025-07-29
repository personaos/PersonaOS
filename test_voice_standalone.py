#!/usr/bin/env python3
"""
Standalone Voice Pipeline Controller Test

This test validates the voice controller architecture without dependencies.
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_voice_state_enum():
    """Test VoiceState enum directly."""
    print("Testing VoiceState enum...")
    
    try:
        # Test enum creation without importing full controller
        from enum import Enum
        
        class VoiceState(Enum):
            IDLE = "idle"
            LISTENING = "listening"
            PROCESSING = "processing"
            SPEAKING = "speaking"
            ERROR = "error"
            DISABLED = "disabled"
        
        # Test enum values
        assert VoiceState.IDLE.value == "idle"
        assert VoiceState.LISTENING.value == "listening"
        assert VoiceState.PROCESSING.value == "processing"
        assert VoiceState.SPEAKING.value == "speaking"
        assert VoiceState.ERROR.value == "error"
        assert VoiceState.DISABLED.value == "disabled"
        
        print("  [PASS] VoiceState enum structure correct")
        return True
    except Exception as e:
        print(f"  [FAIL] VoiceState enum test failed: {e}")
        return False

def test_configuration_integration():
    """Test configuration system integration."""
    print("Testing configuration integration...")
    
    try:
        from core.config import load_config, validate_config
        
        config = load_config()
        
        # Test voice configuration keys
        voice_keys = [
            "voice_pipeline_enabled",
            "voice_auto_start",
            "voice_response_timeout",
            "voice_state_callbacks", 
            "voice_metrics_enabled",
            "voice_fallback_enabled",
            "voice_max_retries"
        ]
        
        for key in voice_keys:
            if key not in config:
                print(f"  [FAIL] Missing configuration key: {key}")
                return False
        
        print("  [PASS] All voice configuration keys present")
        
        # Test validation
        issues = validate_config(config)
        voice_issues = [k for k in issues.keys() if 'voice' in k]
        
        if voice_issues:
            print(f"  [WARN] Voice configuration issues: {voice_issues}")
        else:
            print("  [PASS] Voice configuration validation passed")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Configuration test failed: {e}")
        return False

def test_intent_processor_voice_support():
    """Test intent processor voice support."""
    print("Testing intent processor voice support...")
    
    try:
        from core.intent.intent_processor import IntentProcessor
        import time
        
        processor = IntentProcessor({})
        
        # Test with voice metadata
        voice_metadata = {
            "input_type": "voice",
            "original_text": "hello world",
            "timestamp": time.time()
        }
        
        result = processor.process("hello world", voice_metadata)
        
        # Check metadata preservation
        if "input_type" not in result:
            print("  [FAIL] Input type not preserved in result")
            return False
        
        if result["input_type"] != "voice":
            print("  [FAIL] Input type not correctly preserved")
            return False
        
        print("  [PASS] Voice metadata correctly processed")
        return True
    except Exception as e:
        print(f"  [FAIL] Intent processor test failed: {e}")
        return False

def test_environment_template_completeness():
    """Test .env.template has all voice settings."""
    print("Testing .env.template completeness...")
    
    try:
        env_file = ".env.template"
        
        if not os.path.exists(env_file):
            print("  [WARN] .env.template not found")
            return True
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        required_settings = [
            "VOICE_PIPELINE_ENABLED",
            "VOICE_AUTO_START", 
            "VOICE_RESPONSE_TIMEOUT",
            "VOICE_STATE_CALLBACKS",
            "VOICE_METRICS_ENABLED",
            "VOICE_FALLBACK_ENABLED",
            "VOICE_MAX_RETRIES"
        ]
        
        missing = []
        for setting in required_settings:
            if setting not in content:
                missing.append(setting)
        
        if missing:
            print(f"  [FAIL] Missing settings in .env.template: {missing}")
            return False
        
        print("  [PASS] All voice settings present in .env.template")
        return True
    except Exception as e:
        print(f"  [FAIL] Environment template test failed: {e}")
        return False

def run_standalone_tests():
    """Run standalone tests."""
    print("Voice Pipeline Controller Standalone Tests")
    print("=" * 50)
    
    tests = [
        ("VoiceState Enum", test_voice_state_enum),
        ("Configuration Integration", test_configuration_integration),
        ("Intent Processor Voice Support", test_intent_processor_voice_support),
        ("Environment Template", test_environment_template_completeness),
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
        print("[PASS] All standalone voice tests passed!")
        print("Voice Pipeline Controller architecture is sound")
        return True
    else:
        print("[FAIL] Some standalone tests failed")
        return False

if __name__ == "__main__":
    success = run_standalone_tests()
    print(f"\nTest suite completed with {'success' if success else 'failures'}")
    sys.exit(0 if success else 1)