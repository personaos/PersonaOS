#!/usr/bin/env python3
"""
Performance benchmark script for PersonaOS STT system.

This script measures STT performance metrics including latency,
accuracy, and resource usage.
"""

import time
import tempfile
import wave
import numpy as np
from typing import Dict, List
from loguru import logger

def create_test_audio(text: str, duration: float = 2.0) -> str:
    """Create a test audio file with synthetic speech."""
    # Generate simple sine wave as placeholder
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a more complex waveform that might resemble speech patterns
    frequencies = [200, 400, 800, 1600]  # Simulate formants
    audio_data = np.zeros_like(t)
    
    for freq in frequencies:
        audio_data += np.sin(2 * np.pi * freq * t) * (0.1 / len(frequencies))
    
    # Add some noise to simulate real audio
    noise = np.random.normal(0, 0.01, len(audio_data))
    audio_data += noise
    
    # Convert to 16-bit PCM
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

def benchmark_stt_handler():
    """Benchmark the STT handler performance."""
    logger.info("Benchmarking STT Handler...")
    
    try:
        from .whisper_stt_handler import WhisperSTTHandler
        
        config = {
            "stt_enabled": True,
            "stt_model": "base",  # Use base model for reasonable performance
            "stt_language": "en",
            "stt_device_index": None
        }
        
        # Initialize handler
        start_time = time.time()
        handler = WhisperSTTHandler(config)
        init_time = time.time() - start_time
        
        logger.info(f"Handler initialization time: {init_time:.3f}s")
        
        # Load model
        start_time = time.time()
        load_success = handler.load_model()
        load_time = time.time() - start_time
        
        if not load_success:
            logger.error("Failed to load STT model")
            return None
        
        logger.info(f"Model loading time: {load_time:.3f}s")
        
        # Test different audio lengths
        test_durations = [1.0, 2.0, 5.0, 10.0]
        results = []
        
        for duration in test_durations:
            logger.info(f"Testing {duration}s audio...")
            
            # Create test audio
            audio_file = create_test_audio(f"Test audio {duration} seconds", duration)
            
            try:
                # Measure transcription time
                start_time = time.time()
                result = handler.transcribe_file(audio_file)
                transcription_time = time.time() - start_time
                
                # Calculate real-time factor
                rtf = transcription_time / duration
                
                results.append({
                    "audio_duration": duration,
                    "transcription_time": transcription_time,
                    "real_time_factor": rtf,
                    "result": result is not None
                })
                
                logger.info(f"  Duration: {duration}s, Time: {transcription_time:.3f}s, RTF: {rtf:.3f}")
                
            finally:
                # Clean up temp file
                import os
                if os.path.exists(audio_file):
                    os.unlink(audio_file)
        
        # Clean up handler
        handler.unload_model()
        
        return {
            "init_time": init_time,
            "load_time": load_time,
            "transcription_results": results
        }
        
    except Exception as e:
        logger.error(f"STT handler benchmark failed: {e}")
        return None

def benchmark_voice_bridge():
    """Benchmark the voice-to-intent bridge."""
    logger.info("Benchmarking Voice-to-Intent Bridge...")
    
    try:
        from .voice_to_intent_bridge import VoiceToIntentBridge
        
        config = {
            "stt_enabled": True,
            "stt_model": "base",
            "stt_language": "en",
            "intent_enabled": True,
            "safety_level": "standard"
        }
        
        # Initialize bridge
        start_time = time.time()
        bridge = VoiceToIntentBridge(config)
        init_time = time.time() - start_time
        
        logger.info(f"Bridge initialization time: {init_time:.3f}s")
        
        # Test voice command processing
        test_commands = [
            "Hello PersonaOS",
            "What time is it?",
            "Tell me a joke",
            "Calculate 2 plus 2",
            "Set a timer for 5 minutes"
        ]
        
        results = []
        
        for command in test_commands:
            start_time = time.time()
            result = bridge.process_voice_command(command)
            processing_time = time.time() - start_time
            
            results.append({
                "command": command,
                "processing_time": processing_time,
                "action": result.get("action", "unknown"),
                "success": "error" not in result
            })
            
            logger.info(f"  Command: '{command}' -> {processing_time:.3f}s")
        
        # Clean up
        bridge.cleanup()
        
        return {
            "init_time": init_time,
            "command_results": results
        }
        
    except Exception as e:
        logger.error(f"Voice bridge benchmark failed: {e}")
        return None

def benchmark_memory_usage():
    """Benchmark memory usage of STT components."""
    logger.info("Benchmarking memory usage...")
    
    try:
        import psutil
        process = psutil.Process()
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        logger.info(f"Baseline memory: {baseline_memory:.1f} MB")
        
        from .whisper_stt_handler import WhisperSTTHandler
        
        config = {
            "stt_enabled": True,
            "stt_model": "base",
            "stt_language": "en"
        }
        
        # Memory after handler creation
        handler = WhisperSTTHandler(config)
        handler_memory = process.memory_info().rss / 1024 / 1024
        logger.info(f"After handler creation: {handler_memory:.1f} MB (+{handler_memory - baseline_memory:.1f} MB)")
        
        # Memory after model loading
        if handler.load_model():
            loaded_memory = process.memory_info().rss / 1024 / 1024
            logger.info(f"After model loading: {loaded_memory:.1f} MB (+{loaded_memory - baseline_memory:.1f} MB)")
        
            # Clean up
            handler.unload_model()
            cleanup_memory = process.memory_info().rss / 1024 / 1024
            logger.info(f"After model unloading: {cleanup_memory:.1f} MB")
            
            return {
                "baseline_mb": baseline_memory,
                "handler_overhead_mb": handler_memory - baseline_memory,
                "model_overhead_mb": loaded_memory - baseline_memory,
                "cleanup_mb": cleanup_memory
            }
        else:
            logger.error("Could not load model for memory benchmark")
            return None
            
    except ImportError:
        logger.warning("psutil not available, skipping memory benchmark")
        return None
    except Exception as e:
        logger.error(f"Memory benchmark failed: {e}")
        return None

def generate_report(results: Dict):
    """Generate a performance report."""
    logger.info("\n" + "=" * 60)
    logger.info("PERFORMANCE BENCHMARK REPORT")
    logger.info("=" * 60)
    
    # STT Handler Results
    if results.get("stt_handler"):
        stt_results = results["stt_handler"]
        logger.info("\n--- STT Handler Performance ---")
        logger.info(f"Initialization time: {stt_results['init_time']:.3f}s")
        logger.info(f"Model loading time: {stt_results['load_time']:.3f}s")
        
        logger.info("\nTranscription Performance:")
        for result in stt_results['transcription_results']:
            rtf = result['real_time_factor']
            status = "✓" if rtf < 1.0 else "⚠"
            logger.info(f"  {status} {result['audio_duration']}s audio: {result['transcription_time']:.3f}s (RTF: {rtf:.3f})")
    
    # Voice Bridge Results
    if results.get("voice_bridge"):
        bridge_results = results["voice_bridge"]
        logger.info("\n--- Voice-to-Intent Bridge Performance ---")
        logger.info(f"Initialization time: {bridge_results['init_time']:.3f}s")
        
        avg_processing_time = sum(r['processing_time'] for r in bridge_results['command_results']) / len(bridge_results['command_results'])
        logger.info(f"Average command processing time: {avg_processing_time:.3f}s")
        
        success_rate = sum(1 for r in bridge_results['command_results'] if r['success']) / len(bridge_results['command_results'])
        logger.info(f"Command success rate: {success_rate:.1%}")
    
    # Memory Results
    if results.get("memory"):
        memory_results = results["memory"]
        logger.info("\n--- Memory Usage ---")
        logger.info(f"Baseline memory: {memory_results['baseline_mb']:.1f} MB")
        logger.info(f"Handler overhead: {memory_results['handler_overhead_mb']:.1f} MB")
        logger.info(f"Model overhead: {memory_results['model_overhead_mb']:.1f} MB")
        logger.info(f"Memory after cleanup: {memory_results['cleanup_mb']:.1f} MB")
    
    logger.info("\n" + "=" * 60)

def main():
    """Main benchmark function."""
    logger.info("Starting PersonaOS STT Performance Benchmark")
    
    results = {}
    
    # Run benchmarks
    benchmarks = [
        ("stt_handler", benchmark_stt_handler),
        ("voice_bridge", benchmark_voice_bridge),
        ("memory", benchmark_memory_usage),
    ]
    
    for name, benchmark_func in benchmarks:
        logger.info(f"\n--- Running {name} benchmark ---")
        try:
            result = benchmark_func()
            results[name] = result
            if result is None:
                logger.warning(f"{name} benchmark skipped or failed")
        except Exception as e:
            logger.error(f"{name} benchmark crashed: {e}")
            results[name] = None
    
    # Generate report
    generate_report(results)
    
    # Return success if at least one benchmark completed
    success = any(result is not None for result in results.values())
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)