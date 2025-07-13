import argparse
import sys
from llm_handler import LLMHandler
from config_manager import ConfigManager
from memory import Memory

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

    # Load or initialize config
    config = ConfigManager.load_config()

    # Override LLM if specified
    if args.llm:
        config['llm_model'] = args.llm

    # Handle config commands
    if args.config:
        print("Current PersonaOS Config:")
        for key, value in config.items():
            print(f"{key}: {value}")
        sys.exit(0)

    if args.set_config:
        key, value = args.set_config
        # Basic type inference for common types, extend as needed
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        config[key] = value
        ConfigManager.save_config(config)
        print(f"Config key '{key}' set to '{value}'")
        sys.exit(0)

    if args.reset_config:
        ConfigManager.reset_config()
        print("Config reset to default values.")
        sys.exit(0)

    # Initialize memory if enabled
    conversation_memory = None
    if not args.no_memory:
        conversation_memory = Memory()

    # Initialize LLM handler
    llm = LLMHandler(config=config, memory=conversation_memory)

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
