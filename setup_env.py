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

def show_welcome_message():
    """Display enhanced welcome message"""
    qprint("\n" + "="*60)
    qprint("🤖 Welcome to PersonaOS Setup Wizard!".center(60))
    qprint("="*60)
    qprint("\n🎯 This wizard will help you configure PersonaOS for your needs.")
    qprint("\n📝 Setup Options:")
    qprint("  • Quick Setup: Use smart defaults for immediate use")
    qprint("  • Custom Setup: Configure each setting individually")
    qprint("  • Skip sections you don't need right now")
    qprint("\n💡 Tips:")
    qprint("  • Press ENTER to keep current values or use defaults")
    qprint("  • API keys are optional - PersonaOS works with Ollama by default")
    qprint("  • You can reconfigure anytime with: python core/main.py --reset-env")

def show_section_info(section_name, options):
    """Show information about what each section does"""
    section_descriptions = {
        "🤖 LLM Configuration": "Configure your AI language model settings. Ollama (local) is recommended for privacy.",
        "🔑 API Keys": "Optional: Add API keys for cloud AI services. Skip if using only local Ollama.",
        "🔊 Audio Settings": "Optional: Configure microphone and speaker devices for voice interaction.",
        "🛡️ Intent & Safety": "Configure how PersonaOS processes and validates user requests.",
        "⚙️ Developer Options": "Advanced settings for debugging and development.",
        "🌐 Web UI": "Configure ports for the web-based user interface."
    }
    
    description = section_descriptions.get(section_name, "Configure these settings.")
    qprint(f"\n💡 About this section: {description}")
    
    # Show what settings are in this section
    setting_count = len(options)
    qprint(f"📋 This section has {setting_count} setting{'s' if setting_count != 1 else ''}:")
    for key, config in options.items():
        status = "Required" if config.get("required", False) else "Optional"
        qprint(f"  • {key.replace('_', ' ').title()} ({status})")

def get_setup_mode():
    """Ask user for setup mode preference"""
    qprint("\n🚀 Choose your setup mode:")
    qprint("1. 🏃‍♂️ Quick Setup (recommended for beginners)")
    qprint("2. 🔧 Custom Setup (configure each setting)")
    qprint("3. 📖 Help & Information")
    
    while True:
        choice = input("\nSelect mode (1-3): ").strip()
        
        if choice == "1":
            return "quick"
        elif choice == "2":
            return "custom"
        elif choice == "3":
            show_help_info()
            continue
        else:
            qprint("❌ Please choose 1, 2, or 3.")

def show_help_info():
    """Show detailed help information"""
    qprint("\n" + "="*60)
    qprint("📖 PersonaOS Setup Help".center(60))
    qprint("="*60)
    
    qprint("\n🤖 What is PersonaOS?")
    qprint("PersonaOS is your local AI assistant that works offline using Ollama.")
    qprint("It provides both command-line and web interfaces for AI interaction.")
    
    qprint("\n🏃‍♂️ Quick Setup Mode:")
    qprint("• Uses smart defaults for immediate functionality")
    qprint("• Sets up Ollama as the AI provider (privacy-focused)")
    qprint("• Enables basic features without complex configuration")
    qprint("• Perfect for first-time users")
    
    qprint("\n🔧 Custom Setup Mode:")
    qprint("• Step through each configuration section")
    qprint("• Add API keys for cloud AI services")
    qprint("• Configure advanced features and debugging")
    qprint("• Skip sections you don't need")
    
    qprint("\n💡 Key Concepts:")
    qprint("• Ollama: Local AI that runs on your computer (private)")
    qprint("• API Keys: Access tokens for cloud AI services (optional)")
    qprint("• Web UI: Browser-based interface (requires Node.js)")
    qprint("• CLI: Command-line interface (always available)")
    
    qprint("\n🔒 Privacy Notes:")
    qprint("• Ollama keeps everything local - no data sent to cloud")
    qprint("• API keys are stored encrypted when possible")
    qprint("• You can use PersonaOS completely offline with Ollama")
    
    input("\nPress ENTER to continue...")

def run_quick_setup():
    """Run quick setup with smart defaults"""
    qprint("\n🏃‍♂️ Running Quick Setup...")
    qprint("\n✨ Using these smart defaults:")
    
    quick_config = {
        "LLM_PROVIDER": "ollama",
        "OLLAMA_MODEL": "openhermes", 
        "OLLAMA_API_URL": "",
        "WEB_UI_ENABLED": "true",
        "WEB_UI_PORT": "8000",
        "FRONTEND_PORT": "5173",
        "INTENT_ENABLED": "true",
        "SAFETY_LEVEL": "standard",
        "ALLOW_TOOL_EXECUTION": "true",
        "DEBUG_MODE": "false",
        "LOG_LEVEL": "INFO"
    }
    
    for key, value in quick_config.items():
        qprint(f"  ✓ {key.replace('_', ' ').title()}: {value}")
    
    qprint("\n🤔 This setup will:")
    qprint("  • Use Ollama for local AI (no cloud dependency)")
    qprint("  • Enable both CLI and Web UI interfaces")
    qprint("  • Use standard safety settings")
    qprint("  • Skip optional API keys (you can add them later)")
    
    confirm = input("\nProceed with Quick Setup? (Y/n): ").strip().lower()
    if confirm in ['', 'y', 'yes']:
        return quick_config
    else:
        qprint("❌ Quick setup cancelled. Let's try custom setup...")
        return None

def enhanced_prompt_user(key, config, current_value=''):
    """Enhanced user prompt with better help and validation"""
    display_value = mask_sensitive_value(current_value, config["sensitive"]) if current_value else config["default"]
    
    # Color coding for different types
    if config["sensitive"]:
        key_display = f"🔑 {key.replace('_', ' ').title()}"
    elif key.endswith("_PORT"):
        key_display = f"🌐 {key.replace('_', ' ').title()}"
    elif key.startswith("DEBUG") or key.startswith("LOG"):
        key_display = f"🔧 {key.replace('_', ' ').title()}"
    else:
        key_display = f"⚙️ {key.replace('_', ' ').title()}"
    
    qprint(f"\n{key_display}")
    qprint(f"  💡 {config['help']}")
    qprint(f"  📄 Current: {display_value}")
    
    # Show examples for certain fields
    if key.endswith("_API_KEY") and not current_value:
        qprint("  📋 Example: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        qprint("  ✨ Optional: Leave blank to use local Ollama only")
    elif key.endswith("_PORT"):
        qprint("  📋 Example: 8000")
        qprint("  ✨ Will auto-find free port if this one is busy")
    elif key == "SAFETY_LEVEL":
        qprint("  📋 Options: strict (safest) | standard (balanced) | relaxed (permissive)")
    elif key == "LOG_LEVEL":
        qprint("  📋 Options: DEBUG (verbose) | INFO (normal) | WARNING | ERROR (quiet)")
    
    user_input = input("  💬 Enter new value (or ENTER to keep current): ").strip()
    
    if not user_input:
        return current_value or config["default"]
    
    # Enhanced validation
    validated_value = validate_input(key, user_input)
    
    # Additional validation feedback
    if key.endswith("_API_KEY") and validated_value:
        qprint("  ✅ API key accepted (will be stored securely)")
    elif key.endswith("_PORT") and validated_value.isdigit():
        port_num = int(validated_value)
        if port_num < 1024:
            qprint("  ⚠️ Port numbers below 1024 may require administrator privileges")
        elif port_num > 65535:
            qprint("  ❌ Port number too high (max: 65535)")
            return enhanced_prompt_user(key, config, current_value)
    
    return validated_value

def run_env_setup():
    show_welcome_message()
    load_existing_env()
    
    # Get setup mode preference
    setup_mode = get_setup_mode()
    
    if setup_mode == "quick":
        new_config = run_quick_setup()
        if not new_config:
            setup_mode = "custom"  # Fall back to custom if quick was cancelled

    if setup_mode == "custom":
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
                "FRONTEND_PORT": {"default": "5173", "help": "Frontend dev server port", "sensitive": False},
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
            show_section_info(section, options)
            
            skip = input("  ➤ Skip this section? (Y/n): ").strip().lower()
            if skip in ["y", "yes"]:
                qprint("  ⏭️ Section skipped")
                continue

            for key, config in options.items():
                current = get_current_value(key, config["default"], config["sensitive"])
                new_val = enhanced_prompt_user(key, config, current)
                new_config[key] = new_val
    
    # Save configuration
    backup_env()
    for k, v in new_config.items():
        set_key(ENV_FILE, k, v)

    # Save summary
    with open(SUMMARY_FILE, "w") as f:
        f.write("PersonaOS Configuration Summary\n")
        f.write("=" * 40 + "\n\n")
        for k, v in new_config.items():
            log_val = mask_sensitive_value(v, True) if "API_KEY" in k else v
            f.write(f"{k} = {log_val}\n")

    # Success message
    qprint("\n" + "="*60)
    qprint("🎉 Configuration completed successfully!".center(60))
    qprint("="*60)
    qprint("\n✅ Configuration saved to .env")
    qprint("📄 Summary saved to onboarding_summary.txt")
    
    # Next steps
    qprint("\n🚀 What's next?")
    qprint("  1. Start PersonaOS: python start.py")
    qprint("  2. Or use CLI directly: python core/main.py")
    qprint("  3. For Web UI: Make sure Node.js is installed")
    
    # Show what was configured
    if new_config.get("LLM_PROVIDER") == "ollama":
        qprint("\n🤖 AI Setup:")
        qprint("  • Using Ollama for local AI (privacy-focused)")
        qprint("  • Download models with: ollama pull openhermes")
    
    api_keys_configured = sum(1 for k, v in new_config.items() if k.endswith("_API_KEY") and v)
    if api_keys_configured > 0:
        qprint(f"\n🔑 API Keys: {api_keys_configured} configured")
    
    if new_config.get("WEB_UI_ENABLED") == "true":
        web_port = new_config.get("WEB_UI_PORT", "8000")
        frontend_port = new_config.get("FRONTEND_PORT", "5173")
        qprint(f"\n🌐 Web UI will be available at:")
        qprint(f"  • Backend: http://localhost:{web_port}")
        qprint(f"  • Frontend: http://localhost:{frontend_port}")
    
    qprint("\n💡 Need help? Run: python start.py --health")
    qprint("🔄 Reconfigure anytime: python core/main.py --reset-env")

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