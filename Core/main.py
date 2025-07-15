# main.py

import argparse
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_config
from setup_env import is_env_complete, run_env_setup, reset_env
from core.llm.llm_handler import init_llm_manager, handle_conversation

def main():
    # CLI flag parsing
    parser = argparse.ArgumentParser(description="PersonaOS CLI")
    parser.add_argument("--reset-env", action="store_true", help="Reset and reconfigure environment")
    args = parser.parse_args()

    # Handle --reset-env flag
    if args.reset_env:
        reset_env()

    # Onboarding step: run setup if .env is missing or incomplete
    if not is_env_complete():
        run_env_setup()

    # Load environment variables from .env
    load_dotenv()

    # Load config and memory
    config = load_config()
    memory = None  # Memory manager will be implemented later

    # NEW: Initialize LLM manager
    llm_manager = init_llm_manager(config)

    # Start conversation loop
    print("🤖 PersonaOS is running... (type 'exit' to quit)")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("👋 Goodbye!")
            break

        # UPDATED: Pass llm_manager explicitly
        response = handle_conversation(user_input, config, memory, llm_manager)
        print("PersonaOS:", response)

if __name__ == "__main__":
    main()
