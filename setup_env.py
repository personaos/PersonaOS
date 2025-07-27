#!/usr/bin/env python3
"""
PersonaOS Environment Setup Script v2
Interactive configuration wizard for setting up .env file with enhancements:
- Section skipping
- Input validation
- Defaults/headless mode
- Quiet mode
- .env backup
- Summary logging
- Cleaner UI
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv, set_key, dotenv_values

ENV_FILE = Path(".env")
TEMPLATE_FILE = Path(".env.template")
BACKUP_FILE = Path(".env.backup")
SUMMARY_FILE = Path("onboarding_summary.txt")
QUIET_MODE = "--quiet" in sys.argv
DEFAULTS_MODE = "--defaults" in sys.argv

def qprint(*args, **kwargs):
    if not QUIET_MODE:
        print(*args, **kwargs)

def load_existing_env():
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

def mask_sensitive_value(value, is_sensitive=False):
    if not value or not is_sensitive:
        return value
    if len(value) <= 8:
        return '*' * len(value)
    return value[:4] + '*' * (len(value) - 8) + value[-4:]

def get_current_value(key, default='', is_sensitive=False):
    return os.getenv(key, default)

def validate_input(key, value):
    if key.endswith("_API_KEY") and value and not value.startswith(("sk-", "pk-", "api-")):
        qprint("  ⚠️  Warning: API key format may be invalid.")
    if key.endswith("PORT") and value and not value.isdigit():
        qprint("  ❌ Port must be a number.")
    return value

def prompt_user(prompt_text, help_text, current_value='', is_sensitive=False):
    display_value = mask_sensitive_value(current_value, is_sensitive) if current_value else 'none'
    qprint(f"\n{prompt_text} [current: {display_value}]:")
    qprint(f"  💡 {help_text}")
    user_input = input("  > ").strip()
    return current_value if not user_input else validate_input(prompt_text, user_input)

def print_section_header(title):
    qprint(f"\n{'='*60}\n{title.center(60)}\n{'='*60}")

def backup_env():
    if ENV_FILE.exists():
        shutil.copy(ENV_FILE, BACKUP_FILE)
        qprint("🗂️  Backup of previous .env saved as .env.backup")

def run_env_setup():
    qprint("\n🛠️  PersonaOS Onboarding — Configure Your Environment")
    qprint("\n💡 Press ENTER to keep existing values or use defaults. Use --defaults for automatic setup.")

    load_existing_env()

    config_options = {
        "🤖 LLM Configuration": {
            "LLM_PROVIDER": {"default": "ollama", "help": "LLM backend (openai, anthropic, ollama)", "sensitive": False},
            "OLLAMA_MODEL": {"default": "openhermes", "help": "Ollama model name", "sensitive": False},
            "OLLAMA_API_URL": {"default": "", "help": "Ollama API URL (blank = CLI mode)", "sensitive": False},
        },
        "🔑 API Keys": {
            "OPENAI_API_KEY": {"default": "", "help": "OpenAI API key", "sensitive": True},
            "ANTHROPIC_API_KEY": {"default": "", "help": "Claude API key", "sensitive": True},
            "GOOGLE_API_KEY": {"default": "", "help": "Google Gemini API key", "sensitive": True},
            "COHERE_API_KEY": {"default": "", "help": "Cohere API key", "sensitive": True},
            "PICOVOICE_API_KEY": {"default": "", "help": "Wake word API key", "sensitive": True},
            "ELEVENLABS_API_KEY": {"default": "", "help": "Text-to-speech API key", "sensitive": True},
        },
        "🔊 Audio Settings": {
            "MIC_DEVICE_INDEX": {"default": "", "help": "Microphone index (optional)", "sensitive": False},
            "SPEAKER_DEVICE_INDEX": {"default": "", "help": "Speaker index (optional)", "sensitive": False},
        },
        "🛡️ Intent & Safety": {
            "INTENT_ENABLED": {"default": "true", "help": "Enable intent processing", "sensitive": False},
            "SAFETY_LEVEL": {"default": "standard", "help": "strict, standard, or relaxed", "sensitive": False},
            "ALLOW_TOOL_EXECUTION": {"default": "true", "help": "Allow plugin execution", "sensitive": False},
            "MAX_INTENT_CONFIDENCE": {"default": "1.0", "help": "Max confidence threshold", "sensitive": False},
        },
        "⚙️ Developer Options": {
            "DEBUG_MODE": {"default": "false", "help": "Enable debug logs", "sensitive": False},
            "LOG_LEVEL": {"default": "INFO", "help": "DEBUG, INFO, WARNING, ERROR", "sensitive": False},
            "ENABLE_API_LOGGING": {"default": "false", "help": "Log API requests (sensitive)", "sensitive": False},
        },
        "🌐 Web UI": {
            "WEB_UI_ENABLED": {"default": "true", "help": "Enable web UI", "sensitive": False},
            "WEB_UI_PORT": {"default": "8000", "help": "Backend port", "sensitive": False},
            "FRONTEND_PORT": {"default": "3000", "help": "Frontend dev server port", "sensitive": False},
        }
    }

    if DEFAULTS_MODE:
        qprint("\n🔁 Applying default config from template...")
        default_config = dotenv_values(TEMPLATE_FILE)
        for key, val in default_config.items():
            set_key(ENV_FILE, key, val)
        qprint("✅ Defaults applied.")
        sys.exit(0)

    new_config = {}

    for section, options in config_options.items():
        print_section_header(section)
        skip = input("  ➤ Skip this section? (Y/n): ").strip().lower()
        if skip in ["y", "yes"]:
            continue

        for key, config in options.items():
            current = get_current_value(key, config["default"], config["sensitive"])
            prompt = f"{key.replace('_', ' ').title()} [{config['default']}]"
            new_val = prompt_user(prompt, config["help"], current, config["sensitive"])
            new_config[key] = new_val

    qprint("\n✅ Review summary before saving...")
    for section, options in config_options.items():
        qprint(f"\n{section}")
        for key in options:
            val = new_config.get(key, '')
            masked = mask_sensitive_value(val, True) if options[key]["sensitive"] else val
            qprint(f"  {key}: {masked if masked else '(empty)'}")

    confirm = input("\nPress [Y] to confirm and save, or [N] to cancel: ").strip().lower()
    if confirm not in ['y', 'yes']:
        qprint("❌ Configuration cancelled.")
        sys.exit(1)

    backup_env()
    for k, v in new_config.items():
        set_key(ENV_FILE, k, v)

    with open(SUMMARY_FILE, "w") as f:
        for k, v in new_config.items():
            log_val = mask_sensitive_value(v, True) if "API_KEY" in k else v
            f.write(f"{k} = {log_val}\n")

    qprint("\n✅ Configuration saved to .env")
    qprint("📄 Summary saved to onboarding_summary.txt")
    qprint("\n🚀 Start PersonaOS with: python core/main.py")

def is_env_complete():
    """Checks whether all required env keys are present and non-empty"""
    required = dotenv_values(TEMPLATE_FILE)
    current = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    return all(key in current and current[key] for key in required)

def reset_env():
    """Removes .env file for fresh setup"""
    if ENV_FILE.exists():
        ENV_FILE.unlink()
        print("🧹 .env file reset.")

if __name__ == "__main__":
    run_env_setup()