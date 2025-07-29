#!/usr/bin/env python3
"""
Test script for Direct Model Execution (DME) functionality in PersonaOS.

This script tests the llama-cpp-python integration and demonstrates
the full DME pipeline: model loading, inference, and streaming.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add the core module to the path
sys.path.insert(0, str(Path(__file__).parent / "core"))

from core.config import load_config
from core.llm.llm_handler import LLMManager
from core.llm.model_config_loader import ModelConfigLoader
from core.llm.llama_cpp_handler import LlamaCppHandler

def setup_logging():
    """Setup logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_model_config_loader():
    """Test the model configuration loader."""
    print("=" * 60)
    print("TESTING MODEL CONFIG LOADER")
    print("=" * 60)
    
    loader = ModelConfigLoader()
    
    # Test loading configuration
    config = loader.load_config()
    print(f"✓ Loaded configuration with {len(config.get('backends', {}))} backends")
    
    # Test listing backends
    backends = loader.list_available_backends()
    print(f"✓ Available backends: {', '.join(backends)}")
    
    # Test getting specific backend config
    for backend in backends:
        backend_config = loader.get_backend_config(backend)
        print(f"✓ Backend '{backend}' config loaded (type: {backend_config.get('type', 'unknown')})")
    
    return config

def test_llama_cpp_handler_direct():
    """Test the LlamaCppHandler directly."""
    print("\n" + "=" * 60)
    print("TESTING LLAMA-CPP HANDLER DIRECTLY")
    print("=" * 60)
    
    loader = ModelConfigLoader()
    llama_config = loader.get_backend_config("llama_cpp")
    
    if not llama_config:
        print("❌ No llama_cpp backend configuration found")
        return False
    
    print(f"📁 Model path: {llama_config.get('model_path', 'Not specified')}")
    
    # Check if model file exists
    model_path = llama_config.get('model_path')
    if not model_path or not os.path.exists(model_path):
        print(f"⚠️  Model file not found: {model_path}")
        print("   You need to download a GGUF model file first.")
        print("   Example: place a .gguf file in the models/ directory")
        print("   and update config/model_config.yaml with the correct path.")
        return False
    
    try:
        # Create handler
        print("🔄 Creating LlamaCppHandler...")
        handler = LlamaCppHandler(llama_config)
        
        # Validate config
        print("🔍 Validating configuration...")
        if not handler.validate_config():
            print("❌ Configuration validation failed")
            return False
        print("✓ Configuration validated")
        
        # Load model
        print("🔄 Loading model (this may take a moment)...")
        start_time = time.time()
        if not handler.load_model():
            print("❌ Failed to load model")
            return False
        load_time = time.time() - start_time
        print(f"✓ Model loaded successfully in {load_time:.2f} seconds")
        
        # Get model info
        info = handler.get_model_info()
        print(f"📊 Model info: {info['backend']} with {info['context_length']} context length")
        
        # Test basic generation
        print("\n🔄 Testing basic generation...")
        test_prompt = "Hello! Please introduce yourself briefly."
        print(f"📝 Prompt: {test_prompt}")
        
        start_time = time.time()
        response = handler.generate(test_prompt, stream=False)
        gen_time = time.time() - start_time
        
        print(f"🤖 Response ({gen_time:.2f}s): {response[:100]}{'...' if len(response) > 100 else ''}")
        
        # Test streaming generation
        print("\n🔄 Testing streaming generation...")
        print("📝 Prompt: Tell me a very short joke.")
        print("🤖 Streaming response: ", end="", flush=True)
        
        start_time = time.time()
        for token in handler.generate_streaming("Tell me a very short joke."):
            print(token, end="", flush=True)
        stream_time = time.time() - start_time
        print(f"\n✓ Streaming completed in {stream_time:.2f}s")
        
        # Unload model
        print("\n🔄 Unloading model...")
        if handler.unload_model():
            print("✓ Model unloaded successfully")
        else:
            print("⚠️  Failed to unload model")
        
        return True
        
    except ImportError:
        print("❌ llama-cpp-python not installed. Install with: pip install llama-cpp-python")
        return False
    except Exception as e:
        print(f"❌ Error testing LlamaCppHandler: {e}")
        return False

def test_llm_manager_integration():
    """Test the LLMManager with DME support."""
    print("\n" + "=" * 60)
    print("TESTING LLM MANAGER INTEGRATION")
    print("=" * 60)
    
    # Load PersonaOS config
    persona_config = load_config()
    
    # Set backend to llama_cpp for testing
    persona_config["model_backend"] = "llama_cpp"
    
    try:
        print("🔄 Creating LLMManager with DME backend...")
        llm_manager = LLMManager(persona_config)
        
        # Get backend info
        info = llm_manager.get_current_backend_info()
        print(f"📊 Current backend: {info['backend']} (status: {info['status']})")
        
        if info['status'] != 'loaded':
            print("⚠️  Model not loaded, skipping LLM tests")
            return False
        
        # Test query
        print("\n🔄 Testing LLM query...")
        test_prompt = "What is the capital of France?"
        print(f"📝 Prompt: {test_prompt}")
        
        response = llm_manager.query(test_prompt)
        print(f"🤖 Response: {response[:100]}{'...' if len(response) > 100 else ''}")
        
        # Test backend switching
        print("\n🔄 Testing backend switching...")
        available_backends = llm_manager.list_available_backends()
        print(f"📋 Available backends: {', '.join(available_backends)}")
        
        # Try switching to ollama and back
        if "ollama" in available_backends:
            print("🔄 Switching to ollama backend...")
            if llm_manager.switch_backend("ollama"):
                print("✓ Switched to ollama")
                
                print("🔄 Switching back to llama_cpp...")
                if llm_manager.switch_backend("llama_cpp"):
                    print("✓ Switched back to llama_cpp")
                else:
                    print("❌ Failed to switch back to llama_cpp")
            else:
                print("❌ Failed to switch to ollama")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing LLMManager: {e}")
        return False

def test_full_pipeline():
    """Test the full PersonaOS pipeline with DME."""
    print("\n" + "=" * 60)
    print("TESTING FULL PERSONA PIPELINE")
    print("=" * 60)
    
    try:
        from core.llm.llm_handler import handle_conversation
        from core.llm.memory import MemoryManager
        
        # Load config and set DME backend
        config = load_config()
        config["model_backend"] = "llama_cpp"
        
        # Initialize components
        print("🔄 Initializing PersonaOS components...")
        llm_manager = LLMManager(config)
        
        if llm_manager.get_current_backend_info()['status'] != 'loaded':
            print("⚠️  DME model not loaded, skipping pipeline test")
            return False
        
        # Initialize memory if enabled
        memory = None
        if config.get("memory_enabled", True):
            try:
                memory = MemoryManager(config)
                print("✓ Memory manager initialized")
            except Exception as e:
                print(f"⚠️  Memory manager failed: {e}")
        
        # Test conversation handling
        print("\n🔄 Testing conversation pipeline...")
        test_prompts = [
            "Hello, I'm testing the DME system.",
            "Can you tell me about artificial intelligence?",
            "What was my first message?"
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n📝 Message {i}: {prompt}")
            
            start_time = time.time()
            response = handle_conversation(prompt, config, memory, llm_manager)
            response_time = time.time() - start_time
            
            print(f"🤖 Response ({response_time:.2f}s): {response[:100]}{'...' if len(response) > 100 else ''}")
        
        print("\n✓ Full pipeline test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error testing full pipeline: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 PersonaOS Direct Model Execution (DME) Test Suite")
    print("=" * 60)
    
    setup_logging()
    
    results = []
    
    # Test 1: Model Config Loader
    try:
        test_model_config_loader()
        results.append(("Model Config Loader", True))
    except Exception as e:
        print(f"❌ Model Config Loader failed: {e}")
        results.append(("Model Config Loader", False))
    
    # Test 2: LlamaCpp Handler Direct
    try:
        success = test_llama_cpp_handler_direct()
        results.append(("LlamaCpp Handler Direct", success))
    except Exception as e:
        print(f"❌ LlamaCpp Handler test failed: {e}")
        results.append(("LlamaCpp Handler Direct", False))
    
    # Test 3: LLM Manager Integration
    try:
        success = test_llm_manager_integration()
        results.append(("LLM Manager Integration", success))
    except Exception as e:
        print(f"❌ LLM Manager test failed: {e}")
        results.append(("LLM Manager Integration", False))
    
    # Test 4: Full Pipeline
    try:
        success = test_full_pipeline()
        results.append(("Full Pipeline", success))
    except Exception as e:
        print(f"❌ Full Pipeline test failed: {e}")
        results.append(("Full Pipeline", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! DME system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("\nCommon issues:")
        print("- Missing GGUF model file (download one and update config/model_config.yaml)")
        print("- llama-cpp-python not installed (pip install llama-cpp-python)")
        print("- Insufficient RAM for model loading")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)