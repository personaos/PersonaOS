# personaos/setup_env.py

import os
from dotenv import dotenv_values, set_key
from pathlib import Path

ENV_FILE = Path(".env")
TEMPLATE_FILE = Path(".env.template")

def is_env_complete():
    """Checks whether all required env keys are present and non-empty"""
    required = dotenv_values(TEMPLATE_FILE)
    current = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    return all(key in current and current[key] for key in required)

def run_env_setup():
    """Prompt user to fill in missing values and write .env"""
    print("🛠️ PersonaOS onboarding: configuring environment...")
    template = dotenv_values(TEMPLATE_FILE)
    current = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}

    for key in template:
        current_value = current.get(key, "")
        user_input = input(f"{key} [{current_value}]: ").strip()
        final_value = user_input if user_input else current_value
        if final_value:
            set_key(ENV_FILE, key, final_value)

    print("✅ Environment setup complete!")

def reset_env():
    """Removes .env file for fresh setup"""
    if ENV_FILE.exists():
        ENV_FILE.unlink()
        print("🧹 .env file reset.")

