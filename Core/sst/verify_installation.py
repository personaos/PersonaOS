#!/usr/bin/env python3
"""
Installation verification script for PersonaOS STT system.

This script verifies that all dependencies are properly installed
and the STT system can be initialized.
"""

import sys
import os
from loguru import logger

def check_python_version():
    """Check if Python version is compatible."""
    logger.info("Checking Python version...")
    if sys.version_info < (3, 8):
        logger.error(f"Python 3.8+ required, found {sys.version}")
        return False
    logger.success(f"Python version OK: {sys.version}")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    logger.info("Checking dependencies...")
    
    required_packages = [
        ("pyaudio", "Audio capture"),
        ("numpy", "Numerical operations"),
        ("loguru", "Logging"),
    ]
    
    optional_packages = [
        ("whisper", "OpenAI Whisper STT"),
    ]
    
    success = True
    
    # Check required packages
    for package, description in required_packages:
        try:
            __import__(package)
            logger.success(f"✓ {package} - {description}")
        except ImportError:
            logger.error(f"✗ {package} - {description} (REQUIRED)")
            success = False
    
    # Check optional packages
    for package, description in optional_packages:
        try:
            __import__(package)
            logger.success(f"✓ {package} - {description}")
        except ImportError:
            logger.warning(f"⚠ {package} - {description} (OPTIONAL - STT won't work)")
    
    return success

def check_audio_devices():
    """Check if audio devices are available."""
    logger.info("Checking audio devices...")
    
    try:
        import pyaudio
        
        pa = pyaudio.PyAudio()
        
        # Check for input devices
        input_devices = []
        output_devices = []
        
        for i in range(pa.get_device_count()):
            device_info = pa.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                input_devices.append((i, device_info['name']))
            if device_info['maxOutputChannels'] > 0:
                output_devices.append((i, device_info['name']))
        
        pa.terminate()
        
        logger.info(f"Found {len(input_devices)} input devices:")
        for idx, name in input_devices[:5]:  # Show first 5
            logger.info(f"  [{idx}] {name}")
        
        logger.info(f"Found {len(output_devices)} output devices:")
        for idx, name in output_devices[:5]:  # Show first 5
            logger.info(f"  [{idx}] {name}")
        
        if len(input_devices) == 0:
            logger.error("No audio input devices found!")
            return False
        
        logger.success("Audio devices available")
        return True
        
    except Exception as e:
        logger.error(f"Audio device check failed: {e}")
        return False

def test_stt_initialization():
    """Test STT system initialization."""
    logger.info("Testing STT system initialization...")
    
    try:
        # Import STT components
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from core.sst.whisper_stt_handler import WhisperSTTHandler
        from core.audio import AudioProcessor
        
        # Test configuration
        test_config = {
            "stt_enabled": True,
            "stt_model": "base",
            "stt_language": "en",
            "stt_device_index": None
        }
        
        # Test STT handler creation
        logger.info("Creating STT handler...")
        stt_handler = WhisperSTTHandler(test_config)
        
        if not stt_handler.validate_config():
            logger.error("STT configuration validation failed")
            return False
        
        logger.success("STT handler created successfully")
        
        # Test audio processor creation
        logger.info("Creating audio processor...")
        audio_processor = AudioProcessor(test_config)
        logger.success("Audio processor created successfully")
        
        logger.success("STT system initialization test passed")
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.warning("This is expected if Whisper is not installed")
        return False
    except Exception as e:
        logger.error(f"STT initialization test failed: {e}")
        return False

def test_configuration_loading():
    """Test configuration loading."""
    logger.info("Testing configuration loading...")
    
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from core.config import load_config, validate_config
        
        # Load configuration
        config = load_config()
        
        # Check STT-related configuration
        stt_config_keys = ['stt_enabled', 'stt_model', 'stt_language']
        for key in stt_config_keys:
            if key not in config:
                logger.error(f"Missing configuration key: {key}")
                return False
        
        # Validate configuration
        issues = validate_config(config)
        if issues:
            logger.warning(f"Configuration issues found: {issues}")
        else:
            logger.success("Configuration validation passed")
        
        logger.success("Configuration loading test passed")
        return True
        
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False

def main():
    """Main verification function."""
    logger.info("PersonaOS STT Installation Verification")
    logger.info("=" * 50)
    
    tests = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Audio Devices", check_audio_devices),
        ("Configuration", test_configuration_loading),
        ("STT Initialization", test_stt_initialization),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        logger.info(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All verification tests passed!")
        logger.info("STT system is ready for use.")
        return True
    else:
        logger.error("❌ Some verification tests failed.")
        logger.info("Please resolve the issues above before using STT.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)