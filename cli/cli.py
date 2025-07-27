import argparse
import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.llm.llm_handler import LLMManager
from core.config import load_config, validate_config

def main():
    parser = argparse.ArgumentParser(description="PersonaOS Command Line Interface")

    parser.add_argument(
        '--llm',
        type=str,
        default=None,
        help='Override the default LLM model to use for this session'
    )
    parser.add_argument(
        '--no-memory',
        action='store_true',
        help='Disable conversation memory for this session'
    )
    parser.add_argument(
        '--config',
        action='store_true',
        help='Show current config settings'
    )
    parser.add_argument(
        '--set-config',
        nargs=2,
        metavar=('KEY', 'VALUE'),
        help='Set a config option by key and value'
    )
    parser.add_argument(
        '--reset-config',
        action='store_true',
        help='Reset config to default values'
    )
    parser.add_argument(
        '--query',
        type=str,
        help='Send a single text query to the assistant and print the response'
    )
    parser.add_argument(
        '--log',
        type=str,
        default=None,
        help='File path to save the conversation transcript (append mode)'
    )

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Override LLM if specified
    if args.llm:
        config['llm_model'] = args.llm

    # Handle config commands
    if args.config:
        print("Current PersonaOS Config:")
        # Sort keys for better readability
        for key in sorted(config.keys()):
            value = config[key]
            # Mask sensitive values
            if 'api_key' in key.lower() and value:
                value = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
            print(f"  {key}: {value}")
        sys.exit(0)

    if args.set_config:
        key, value = args.set_config
        print(f"⚠️  Direct config modification not implemented yet.")
        print(f"Use 'python setup_env.py' to modify configuration")
        sys.exit(1)

    if args.reset_config:
        print(f"⚠️  Config reset not implemented yet.")
        print(f"Delete .env file and run 'python setup_env.py' to reset")
        sys.exit(1)

    # Initialize LLM manager
    try:
        llm = LLMManager(config=config)
    except Exception as e:
        print(f"❌ Failed to initialize LLM manager: {e}")
        sys.exit(1)

    if args.query:
        # Send single text query to LLM and print response
        try:
            response = llm.query(args.query)
            print(f"Assistant: {response}")

            # Log conversation if log file specified
            if args.log:
                with open(args.log, 'a', encoding='utf-8') as f:
                    f.write(f"User: {args.query}\nAssistant: {response}\n\n")

        except Exception as e:
            print(f"Error during query: {e}")
        sys.exit(0)

    # If no args given, print help
    parser.print_help()

if __name__ == "__main__":
    main()
