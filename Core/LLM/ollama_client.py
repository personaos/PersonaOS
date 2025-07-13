# core/llm/llm_handler.py

from core.llm.ollama_client import OllamaClient

class LLMHandler:
    def __init__(self, model_name="ollama"):
        self.model_name = model_name.lower()
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.model_name == "ollama":
            self.client = OllamaClient(model="llama2")  # default model name
        else:
            # Placeholder for other LLM clients, e.g. local or other APIs
            raise ValueError(f"Unsupported LLM model: {self.model_name}")

    def generate_response(self, prompt: str) -> str:
        if not self.client:
            raise RuntimeError("LLM client not initialized.")
        return self.client.generate(prompt)

# Example usage:
if __name__ == "__main__":
    llm = LLMHandler(model_name="ollama")
    response = llm.generate_response("Hello, how are you?")
    print("Response:", response)
