import os
import subprocess
import requests
import json

class OllamaHandler:
    def __init__(self, model="llama2", api_url=None):
        self.model = model
        self.api_url = api_url

    def query_cli(self, prompt):
        try:
            result = subprocess.run(
                ["ollama", "chat", self.model, "--prompt", prompt],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error calling Ollama CLI: {e.stderr}"

    def query_api(self, prompt):
        if not self.api_url:
            return "API URL not set for Ollama API mode."

        url = f"{self.api_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as e:
            return f"Error calling Ollama API: {str(e)}"

    def query(self, prompt):
        if self.api_url:
            return self.query_api(prompt)
        else:
            return self.query_cli(prompt)


class LLMManager:
    def __init__(self, config):
        self.config = config
        self.llm_name = config.get("llm_model", "ollama")
        self.llm = None
        self._init_llm()

    def _init_llm(self):
        if self.llm_name == "ollama":
            model = self.config.get("ollama_model", "llama2")
            api_url = self.config.get("ollama_api_url", None)
            self.llm = OllamaHandler(model=model, api_url=api_url)
        else:
            raise NotImplementedError(f"LLM '{self.llm_name}' not supported yet")

    def query(self, prompt):
        if not self.llm:
            return "No LLM initialized."
        return self.llm.query(prompt)


def init_llm_manager(config):
    return LLMManager(config)


def handle_conversation(prompt, config, memory, llm_manager):
    from ..intent.intent_processor import IntentProcessor
    
    # Initialize intent processor
    intent_processor = IntentProcessor(config)
    
    # Process user input through intent system
    intent_response = intent_processor.process(prompt)
    
    # Handle different actions
    if intent_response["action"] in ["blocked", "refused", "tool_executed", "tool_failed"]:
        return intent_response["response"]
    
    elif intent_response["action"] == "llm_response":
        # Pass to LLM for safe response generation
        return llm_manager.query(prompt)
    
    else:
        # Fallback to direct LLM query
        return llm_manager.query(prompt)
