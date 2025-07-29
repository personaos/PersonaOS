# main.py

import argparse
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_config
from setup_env import is_env_complete, run_env_setup, reset_env
from core.llm.llm_handler import init_llm_manager, handle_conversation
from core.llm.memory import MemoryManager
from core.voice.voice_pipeline_controller import VoicePipelineController

def main():
    # CLI flag parsing
    parser = argparse.ArgumentParser(description="PersonaOS CLI")
    parser.add_argument("--reset-env", action="store_true", help="Reset and reconfigure environment")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice features")
    parser.add_argument("--voice-only", action="store_true", help="Voice input only mode")
    parser.add_argument("--no-stt", action="store_true", help="Disable speech-to-text")
    parser.add_argument("--voice-status", action="store_true", help="Show voice pipeline status and exit")
    parser.add_argument("--voice-recover", action="store_true", help="Attempt voice pipeline recovery and exit")
    parser.add_argument("--tts-test", type=str, help="Test TTS with provided text and exit")
    parser.add_argument("--list-voices", action="store_true", help="List available TTS voices and exit")
    args = parser.parse_args()

    # Handle --reset-env flag
    if args.reset_env:
        reset_env()

    # Onboarding step: run setup if .env is missing or incomplete
    if not is_env_complete():
        run_env_setup()

    # Load environment variables from .env
    load_dotenv()

    # Load config and initialize memory
    config = load_config()
    
    # Override config based on CLI arguments
    if args.no_voice or args.no_stt:
        config["stt_enabled"] = False
    
    memory = MemoryManager(config) if config.get("memory_enabled", True) else None

    # Initialize LLM manager
    llm_manager = init_llm_manager(config)

    # Initialize voice pipeline controller if enabled
    voice_controller = None
    if (config.get("stt_enabled", False) and 
        config.get("voice_pipeline_enabled", True) and 
        not args.no_voice):
        print("🎤 Initializing voice pipeline...")
        voice_controller = VoicePipelineController(config, llm_manager, memory)
        if voice_controller.initialize():
            print("✅ Voice pipeline ready")
        else:
            print("❌ Voice pipeline failed to initialize")
            voice_controller = None

    # Handle --voice-status flag
    if args.voice_status:
        print("🎤 Voice Pipeline Status:")
        if voice_controller:
            status = voice_controller.get_status()
            print(f"  State: {status['state']}")
            print(f"  Active Session: {status['active_session']}")
            print(f"  Voice Enabled: {status['voice_enabled']}")
            if status['metrics']:
                print(f"  Total Conversations: {status['metrics']['total_conversations']}")
                print(f"  Average Response Time: {status['metrics']['average_response_time']:.2f}s")
            
            # Error status
            error_status = voice_controller.get_error_status()
            print(f"  Error Status:")
            print(f"    Total Errors: {error_status['error_count']}")
            print(f"    Consecutive Failures: {error_status['consecutive_failures']}")
            if error_status['last_error']:
                print(f"    Last Error: {error_status['last_error']['error']} ({error_status['last_error']['context']})")
            print(f"    Can Recover: {error_status['can_attempt_recovery']}")
            
            print(f"  Configuration:")
            for key, value in status['config'].items():
                print(f"    {key}: {value}")
        else:
            print("  Voice pipeline not initialized")
        return
    
    # Handle --voice-recover flag
    if args.voice_recover:
        print("🔧 Voice Pipeline Recovery:")
        if voice_controller:
            error_status = voice_controller.get_error_status()
            if error_status['can_attempt_recovery']:
                print("  Attempting voice pipeline recovery...")
                if voice_controller.attempt_recovery():
                    print("  ✅ Voice pipeline recovery successful")
                else:
                    print("  ❌ Voice pipeline recovery failed")
            else:
                print("  ⚠️  Voice pipeline not in error state - no recovery needed")
        else:
            print("  Voice pipeline not initialized")
        return
    
    # Handle --tts-test flag
    if args.tts_test:
        print(f"Testing TTS with text: '{args.tts_test}'")
        if voice_controller:
            if voice_controller.audio_processor.speak_text(args.tts_test):
                print("TTS test completed successfully")
            else:
                print("TTS test failed")
        else:
            print("Voice pipeline not initialized")
        return
    
    # Handle --list-voices flag
    if args.list_voices:
        print("Available TTS voices:")
        if voice_controller:
            voices = voice_controller.get_available_voices()
            if voices:
                for voice_id, voice_info in voices.items():
                    print(f"  {voice_id}: {voice_info['name']} ({voice_info['language']})")
            else:
                print("  No voices available")
        else:
            print("  Voice pipeline not initialized")
        return

    # Initialize memory session
    if memory:
        session_id = memory.start_new_session()
        print(f"🧠 Memory session started: {session_id}")

    # Start conversation loop
    if args.voice_only and voice_controller:
        print("🎤 PersonaOS Voice Mode - Speak to interact (Ctrl+C to quit)")
        run_voice_only_mode(voice_controller, config, memory, llm_manager)
    else:
        print("🤖 PersonaOS is running... (type 'exit' to quit)")
        if voice_controller:
            print("💡 Voice input available - say something or type!")
        run_text_mode(voice_controller, config, memory, llm_manager)
    
    # Cleanup
    try:
        if voice_controller:
            voice_controller.cleanup()
        if memory:
            memory.clear_session()
            print("💾 Conversation saved to memory")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

def run_voice_only_mode(voice_controller, config, memory, llm_manager):
    """Run PersonaOS in voice-only mode."""
    import signal
    import time
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n👋 Stopping voice mode...")
        voice_controller.stop_voice_session()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Define callback for voice responses
    def handle_voice_response(intent_result):
        original_text = intent_result.get('original_text', '')
        response = intent_result.get('response', 'I processed your request.')
        print(f"🎤 Heard: '{original_text}'")
        print(f"🤖 PersonaOS: {response}")
    
    # Set up voice controller callbacks
    voice_controller.set_callbacks(response_callback=handle_voice_response)
    
    # Start voice session
    if voice_controller.start_voice_session():
        print("🎤 Listening... (speak now)")
        try:
            while True:
                time.sleep(0.1)  # Keep main thread alive
        except KeyboardInterrupt:
            pass
    else:
        print("❌ Failed to start voice session")

def run_text_mode(voice_controller, config, memory, llm_manager):
    """Run PersonaOS in text mode with optional voice input."""
    
    # Define callback for voice input (if available)
    def handle_voice_response(intent_result):
        original_text = intent_result.get('original_text', '')
        response = intent_result.get('response', 'I processed your request.')
        print(f"\n🎤 Heard: '{original_text}'")
        print(f"🤖 PersonaOS: {response}")
        print("\nYou: ", end="", flush=True)  # Restore input prompt
    
    # Define fallback callback for voice errors
    def handle_voice_fallback(message):
        print(f"\n⚠️  {message}")
        print("💬 Continuing in text-only mode")
        print("\nYou: ", end="", flush=True)  # Restore input prompt
    
    # Start voice processing if available
    if voice_controller:
        voice_controller.set_callbacks(response_callback=handle_voice_response)
        voice_controller.set_fallback_callback(handle_voice_fallback)
        voice_controller.start_voice_session()
    
    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                print("👋 Goodbye!")
                break

            # Process text input through normal flow
            response = handle_conversation(user_input, config, memory, llm_manager)
            print("PersonaOS:", response)
    finally:
        # Stop voice processing if active
        if voice_controller:
            voice_controller.stop_voice_session()

if __name__ == "__main__":
    main()
