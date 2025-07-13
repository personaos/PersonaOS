from core.llm_handler import handle_conversation
from core.config_manager import load_config
from core.memory_manager import MemoryManager

if __name__ == "__main__":
    config = load_config()
    memory = MemoryManager()
    print("PersonaOS is running... (type 'exit' to quit)")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        response = handle_conversation(user_input, config, memory)
        print("PersonaOS:", response)
