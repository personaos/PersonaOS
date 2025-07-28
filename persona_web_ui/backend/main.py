"""
FastAPI backend for PersonaOS Web UI

This module provides a REST API interface for the PersonaOS assistant,
allowing web-based interaction with the core PersonaOS functionality.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import logging
import os
import shutil
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv, set_key, dotenv_values

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PersonaOS Web API",
    description="REST API for PersonaOS local AI assistant",
    version="0.1.0"
)

# CORS middleware to allow frontend communication
# Load environment variables to get frontend port
load_dotenv()
frontend_port = os.getenv('FRONTEND_PORT', '5173')
allowed_origins = [
    "http://localhost:3000",  # Default React dev server
    f"http://localhost:{frontend_port}",  # Configured frontend port
    "http://localhost:5173",  # Default Vite port
    "http://localhost:5174",  # Vite fallback port 1
    "http://localhost:5175",  # Vite fallback port 2
    "http://localhost:5176",  # Vite fallback port 3
    "http://localhost:5177"   # Vite fallback port 4
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class MessageRequest(BaseModel):
    message: str
    context: Optional[dict] = None

class MessageResponse(BaseModel):
    reply: str
    intent: str
    tools_used: List[str]
    confidence: float = 1.0
    processing_time_ms: Optional[int] = None

class SetupRequest(BaseModel):
    config: Dict[str, str]

class SetupResponse(BaseModel):
    success: bool
    message: str
    backup_created: bool = False

class SetupDefaultsResponse(BaseModel):
    config_sections: Dict[str, Dict[str, Any]]
    current_values: Dict[str, str]

# Model management Pydantic models
class ModelInfo(BaseModel):
    name: str
    size: Optional[str] = None
    modified: Optional[str] = None
    digest: Optional[str] = None
    family: Optional[str] = None
    format: Optional[str] = None
    status: str = "available"  # available, loading, error

class LoadModelRequest(BaseModel):
    model_name: str

class ModelResponse(BaseModel):
    success: bool
    message: str
    model: Optional[ModelInfo] = None

class ModelsListResponse(BaseModel):
    models: List[ModelInfo]
    current_model: Optional[str] = None

class SystemPromptRequest(BaseModel):
    model_name: str
    system_prompt: str

class ModelSettingsRequest(BaseModel):
    model_name: str
    settings: Dict[str, Any]

class SystemPromptResponse(BaseModel):
    success: bool
    message: str
    system_prompt: Optional[str] = None

class ModelSettingsResponse(BaseModel):
    success: bool
    message: str
    settings: Optional[Dict[str, Any]] = None

# Ollama Model Management
class OllamaManager:
    """Manages Ollama models - loading, listing, downloading, and configuration."""
    
    def __init__(self):
        self.current_model = None
        self.models_config_path = Path("../../models/config.json")
        self.prompts_config_path = Path("../../models/prompts.json")
        self._load_config()
    
    def _load_config(self):
        """Load model configurations from JSON files."""
        try:
            if self.models_config_path.exists():
                with open(self.models_config_path, 'r') as f:
                    config = json.load(f)
                    self.current_model = config.get("current_model")
        except Exception as e:
            logger.error(f"Failed to load model config: {e}")
    
    def _save_config(self, config_data: Dict[str, Any]):
        """Save model configuration to JSON file."""
        try:
            self.models_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.models_config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save model config: {e}")
            raise
    
    def _save_prompts(self, prompts_data: Dict[str, Any]):
        """Save system prompts to JSON file."""
        try:
            self.prompts_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.prompts_config_path, 'w') as f:
                json.dump(prompts_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save prompts config: {e}")
            raise
    
    async def list_models(self) -> List[ModelInfo]:
        """List all available Ollama models."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            
            models = []
            lines = result.stdout.strip().split('\n')
            
            # Skip header line
            if len(lines) > 1:
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            model_info = ModelInfo(
                                name=parts[0],
                                size=parts[1] if len(parts) > 1 else None,
                                modified=parts[2] if len(parts) > 2 else None,
                                status="available"
                            )
                            models.append(model_info)
            
            return models
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list Ollama models: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Ollama not found. Please install Ollama first.")
    
    async def load_model(self, model_name: str) -> ModelInfo:
        """Load/run an Ollama model."""
        try:
            # Use 'ollama run' to load the model (this will download if not available)
            process = subprocess.Popen(
                ["ollama", "run", model_name, "--"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send a simple prompt and close to load the model
            process.stdin.write("Hello\n")
            process.stdin.close()
            process.wait(timeout=30)
            
            # Update current model in config
            if self.models_config_path.exists():
                with open(self.models_config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {"model_settings": {}, "current_model": None, "last_updated": None}
            
            config["current_model"] = model_name
            config["last_updated"] = datetime.now().isoformat()
            self._save_config(config)
            self.current_model = model_name
            
            return ModelInfo(name=model_name, status="available")
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise HTTPException(status_code=500, detail=f"Timeout loading model: {model_name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load model: {e}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Ollama not found. Please install Ollama first.")
    
    async def download_model(self, model_name: str) -> ModelInfo:
        """Download a model using ollama pull."""
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Successfully downloaded model: {model_name}")
            return ModelInfo(name=model_name, status="available")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download model {model_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to download model: {e}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Ollama not found. Please install Ollama first.")
    
    async def remove_model(self, model_name: str) -> bool:
        """Remove/eject a model using ollama rm."""
        try:
            result = subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            # If this was the current model, clear it
            if self.current_model == model_name:
                if self.models_config_path.exists():
                    with open(self.models_config_path, 'r') as f:
                        config = json.load(f)
                    config["current_model"] = None
                    config["last_updated"] = datetime.now().isoformat()
                    self._save_config(config)
                    self.current_model = None
            
            logger.info(f"Successfully removed model: {model_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove model {model_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to remove model: {e}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Ollama not found. Please install Ollama first.")
    
    def get_system_prompt(self, model_name: str) -> Optional[str]:
        """Get system prompt for a specific model."""
        try:
            if self.prompts_config_path.exists():
                with open(self.prompts_config_path, 'r') as f:
                    prompts = json.load(f)
                    return prompts.get(model_name, prompts.get("default", {}).get("system_prompt"))
            return None
        except Exception as e:
            logger.error(f"Failed to get system prompt for {model_name}: {e}")
            return None
    
    def set_system_prompt(self, model_name: str, prompt: str):
        """Set system prompt for a specific model."""
        try:
            if self.prompts_config_path.exists():
                with open(self.prompts_config_path, 'r') as f:
                    prompts = json.load(f)
            else:
                prompts = {}
            
            if model_name not in prompts:
                prompts[model_name] = {}
            
            prompts[model_name]["system_prompt"] = prompt
            prompts[model_name]["created_at"] = datetime.now().isoformat()
            
            self._save_prompts(prompts)
            
        except Exception as e:
            logger.error(f"Failed to set system prompt for {model_name}: {e}")
            raise
    
    def get_model_settings(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get generation settings for a specific model."""
        try:
            if self.models_config_path.exists():
                with open(self.models_config_path, 'r') as f:
                    config = json.load(f)
                    return config.get("model_settings", {}).get(model_name, config.get("model_settings", {}).get("default"))
            return None
        except Exception as e:
            logger.error(f"Failed to get model settings for {model_name}: {e}")
            return None
    
    def set_model_settings(self, model_name: str, settings: Dict[str, Any]):
        """Set generation settings for a specific model."""
        try:
            if self.models_config_path.exists():
                with open(self.models_config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {"model_settings": {}, "current_model": None, "last_updated": None}
            
            if "model_settings" not in config:
                config["model_settings"] = {}
            
            config["model_settings"][model_name] = settings
            config["last_updated"] = datetime.now().isoformat()
            
            self._save_config(config)
            
        except Exception as e:
            logger.error(f"Failed to set model settings for {model_name}: {e}")
            raise

# TODO: Replace with actual PersonaOS core integration
class PersonaCore:
    """
    Placeholder class for PersonaOS core functionality.
    This will be replaced with actual imports from the PersonaOS system.
    """
    
    def __init__(self):
        # TODO: Initialize PersonaOS components
        # - LLM handler
        # - Tool registry
        # - Memory manager
        # - Configuration
        self.tools_registry = {
            "clock": {"name": "clock", "description": "Time and date utilities"},
            "prompt_engine": {"name": "prompt_engine", "description": "LLM prompt generation"}
        }
        self.ollama_manager = OllamaManager()
        logger.info("PersonaCore initialized (placeholder)")
    
    def respond(self, message: str, context: Optional[dict] = None) -> dict:
        """
        Process a user message and generate a response.
        
        TODO: Replace with actual PersonaOS processing pipeline:
        1. Intent detection and safety validation
        2. Tool selection and execution
        3. LLM response generation
        4. Response formatting and validation
        
        Args:
            message: User input message
            context: Optional conversation context
            
        Returns:
            Response dictionary with reply, intent, and metadata
        """
        # Simulate intent detection
        intent = self._detect_intent(message)
        
        # Simulate tool usage
        tools_used = self._select_tools(intent, message)
        
        # Generate placeholder response
        reply = self._generate_response(message, intent, tools_used)
        
        return {
            "reply": reply,
            "intent": intent,
            "tools_used": tools_used,
            "confidence": 0.95,
            "processing_time_ms": 150
        }
    
    def _detect_intent(self, message: str) -> str:
        """Placeholder intent detection logic."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["time", "clock", "hour", "minute"]):
            return "inform_time"
        elif any(word in message_lower for word in ["date", "today", "day", "calendar"]):
            return "inform_date"
        elif any(word in message_lower for word in ["hello", "hi", "hey", "greet"]):
            return "greeting"
        elif any(word in message_lower for word in ["help", "assist", "support"]):
            return "request_help"
        elif any(word in message_lower for word in ["weather", "temperature", "forecast"]):
            return "inform_weather"
        else:
            return "general_query"
    
    def _select_tools(self, intent: str, message: str) -> List[str]:
        """Placeholder tool selection logic."""
        if intent in ["inform_time", "inform_date"]:
            return ["clock"]
        elif "generate" in message.lower() or "create" in message.lower():
            return ["prompt_engine"]
        else:
            return []
    
    def _generate_response(self, message: str, intent: str, tools_used: List[str]) -> str:
        """Generate placeholder responses based on intent."""
        if intent == "inform_time":
            return "It's 3:45 PM on Friday, July 26, 2025."
        elif intent == "inform_date":
            return "Today is Friday, July 26, 2025."
        elif intent == "greeting":
            return "Hello! I'm PersonaOS, your local AI assistant. How can I help you today?"
        elif intent == "request_help":
            return "I'm here to help! I can tell you the time, date, and assist with various tasks. What would you like to know?"
        elif intent == "inform_weather":
            return "I don't have weather data available yet, but this feature is planned for future updates."
        else:
            return f"I understand you're asking: '{message}'. I'm still learning how to help with this type of request."

# Initialize PersonaOS core (placeholder)
persona_core = PersonaCore()

# Setup utility functions
ENV_FILE = Path("../../.env")
TEMPLATE_FILE = Path("../../.env.template")
BACKUP_FILE = Path("../../.env.backup")
SUMMARY_FILE = Path("../../onboarding_summary.txt")

def mask_sensitive_value(value: str, is_sensitive: bool = False) -> str:
    """Mask sensitive values for display purposes."""
    if not value or not is_sensitive:
        return value
    if len(value) <= 8:
        return '*' * len(value)
    return value[:4] + '*' * (len(value) - 8) + value[-4:]

def get_config_sections() -> Dict[str, Dict[str, Any]]:
    """Get the configuration sections matching setup_env.py structure."""
    return {
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

def load_current_env_values() -> Dict[str, str]:
    """Load current environment values from .env file."""
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
        return dotenv_values(ENV_FILE)
    return {}

def backup_env() -> bool:
    """Create a backup of the current .env file."""
    try:
        if ENV_FILE.exists():
            shutil.copy(ENV_FILE, BACKUP_FILE)
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to backup .env file: {e}")
        return False

def save_config_summary(config: Dict[str, str]) -> None:
    """Save a masked summary of the configuration."""
    try:
        config_sections = get_config_sections()
        with open(SUMMARY_FILE, "w") as f:
            f.write("PersonaOS Onboarding Summary\n")
            f.write("=" * 40 + "\n\n")
            for section_name, section_config in config_sections.items():
                f.write(f"{section_name}\n")
                f.write("-" * len(section_name) + "\n")
                for key in section_config:
                    value = config.get(key, '')
                    is_sensitive = section_config[key]["sensitive"]
                    masked_value = mask_sensitive_value(value, is_sensitive)
                    f.write(f"{key} = {masked_value if masked_value else '(empty)'}\n")
                f.write("\n")
    except Exception as e:
        logger.error(f"Failed to save config summary: {e}")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "PersonaOS Web API",
        "version": "0.1.0"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check with system status."""
    return {
        "status": "healthy",
        "timestamp": "2025-07-26T15:45:00Z",
        "components": {
            "api": "online",
            "persona_core": "online",
            "tools": list(persona_core.tools_registry.keys())
        }
    }

@app.post("/api/message", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    """
    Process a user message through PersonaOS and return the response.
    
    Args:
        request: MessageRequest containing the user's message and optional context
        
    Returns:
        MessageResponse with the assistant's reply, intent, and metadata
        
    Raises:
        HTTPException: If message processing fails
    """
    try:
        # Validate input
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Log incoming request
        logger.info(f"Processing message: {request.message[:100]}...")
        
        # TODO: Add rate limiting and authentication here
        
        # Process message through PersonaOS core
        response_data = persona_core.respond(
            message=request.message,
            context=request.context
        )
        
        # Log response
        logger.info(f"Generated response with intent: {response_data['intent']}")
        
        return MessageResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )

@app.get("/api/tools")
async def list_tools():
    """Get list of available PersonaOS tools."""
    return {
        "tools": persona_core.tools_registry,
        "count": len(persona_core.tools_registry)
    }

@app.get("/api/setup/defaults", response_model=SetupDefaultsResponse)
async def get_setup_defaults():
    """
    Get configuration defaults and current values for onboarding setup.
    
    Returns:
        SetupDefaultsResponse: Configuration sections with defaults and current values
    """
    try:
        config_sections = get_config_sections()
        current_values = load_current_env_values()
        
        # Mask sensitive values in current_values
        masked_current_values = {}
        for section_config in config_sections.values():
            for key, config in section_config.items():
                current_val = current_values.get(key, '')
                if config["sensitive"]:
                    masked_current_values[key] = mask_sensitive_value(current_val, True)
                else:
                    masked_current_values[key] = current_val
        
        logger.info("Setup defaults retrieved successfully")
        return SetupDefaultsResponse(
            config_sections=config_sections,
            current_values=masked_current_values
        )
        
    except Exception as e:
        logger.error(f"Error retrieving setup defaults: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve setup defaults: {str(e)}"
        )

@app.post("/api/setup/submit", response_model=SetupResponse)
async def submit_setup_config(request: SetupRequest):
    """
    Submit configuration data and save to .env file.
    
    Args:
        request: SetupRequest containing the configuration data
        
    Returns:
        SetupResponse: Success status and backup information
        
    Raises:
        HTTPException: If configuration saving fails
    """
    try:
        # Validate the configuration data
        if not request.config:
            raise HTTPException(status_code=400, detail="Configuration data is required")
        
        # Create backup of existing .env file
        backup_created = backup_env()
        if backup_created:
            logger.info("Backup of existing .env file created")
        
        # Save each configuration key to .env file
        for key, value in request.config.items():
            if value is not None:  # Allow empty strings but not None
                set_key(ENV_FILE, key, value)
        
        # Save configuration summary
        save_config_summary(request.config)
        
        logger.info(f"Configuration saved successfully with {len(request.config)} settings")
        
        return SetupResponse(
            success=True,
            message="Configuration saved successfully",
            backup_created=backup_created
        )
        
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save configuration: {str(e)}"
        )

# Model Management Endpoints

@app.get("/api/models", response_model=ModelsListResponse)
async def list_models():
    """
    Get list of all available Ollama models.
    
    Returns:
        ModelsListResponse: List of models with current model information
    """
    try:
        models = await persona_core.ollama_manager.list_models()
        current_model = persona_core.ollama_manager.current_model
        
        logger.info(f"Listed {len(models)} models, current: {current_model}")
        return ModelsListResponse(
            models=models,
            current_model=current_model
        )
        
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )

@app.post("/api/models/load", response_model=ModelResponse)
async def load_model(request: LoadModelRequest):
    """
    Load/run a specific Ollama model.
    
    Args:
        request: LoadModelRequest containing the model name
        
    Returns:
        ModelResponse: Success status and model information
    """
    try:
        if not request.model_name.strip():
            raise HTTPException(status_code=400, detail="Model name cannot be empty")
        
        logger.info(f"Loading model: {request.model_name}")
        model = await persona_core.ollama_manager.load_model(request.model_name)
        
        return ModelResponse(
            success=True,
            message=f"Model '{request.model_name}' loaded successfully",
            model=model
        )
        
    except Exception as e:
        logger.error(f"Error loading model {request.model_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model: {str(e)}"
        )

@app.post("/api/models/{model_name}/download", response_model=ModelResponse)
async def download_model(model_name: str):
    """
    Download a model using ollama pull.
    
    Args:
        model_name: Name of the model to download
        
    Returns:
        ModelResponse: Success status and model information
    """
    try:
        if not model_name.strip():
            raise HTTPException(status_code=400, detail="Model name cannot be empty")
        
        logger.info(f"Downloading model: {model_name}")
        model = await persona_core.ollama_manager.download_model(model_name)
        
        return ModelResponse(
            success=True,
            message=f"Model '{model_name}' downloaded successfully",
            model=model
        )
        
    except Exception as e:
        logger.error(f"Error downloading model {model_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download model: {str(e)}"
        )

@app.delete("/api/models/{model_name}", response_model=ModelResponse)
async def remove_model(model_name: str):
    """
    Remove/eject a model using ollama rm.
    
    Args:
        model_name: Name of the model to remove
        
    Returns:
        ModelResponse: Success status
    """
    try:
        if not model_name.strip():
            raise HTTPException(status_code=400, detail="Model name cannot be empty")
        
        logger.info(f"Removing model: {model_name}")
        success = await persona_core.ollama_manager.remove_model(model_name)
        
        if success:
            return ModelResponse(
                success=True,
                message=f"Model '{model_name}' removed successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to remove model")
        
    except Exception as e:
        logger.error(f"Error removing model {model_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove model: {str(e)}"
        )

# System Prompt Management Endpoints

@app.get("/api/models/{model_name}/prompt", response_model=SystemPromptResponse)
async def get_system_prompt(model_name: str):
    """
    Get system prompt for a specific model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        SystemPromptResponse: System prompt content
    """
    try:
        prompt = persona_core.ollama_manager.get_system_prompt(model_name)
        
        return SystemPromptResponse(
            success=True,
            message="System prompt retrieved successfully",
            system_prompt=prompt
        )
        
    except Exception as e:
        logger.error(f"Error getting system prompt for {model_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system prompt: {str(e)}"
        )

@app.post("/api/models/{model_name}/prompt", response_model=SystemPromptResponse)
async def set_system_prompt(model_name: str, request: SystemPromptRequest):
    """
    Set system prompt for a specific model.
    
    Args:
        model_name: Name of the model
        request: SystemPromptRequest containing the prompt
        
    Returns:
        SystemPromptResponse: Success status
    """
    try:
        if not request.system_prompt.strip():
            raise HTTPException(status_code=400, detail="System prompt cannot be empty")
        
        persona_core.ollama_manager.set_system_prompt(model_name, request.system_prompt)
        
        return SystemPromptResponse(
            success=True,
            message=f"System prompt updated for model '{model_name}'",
            system_prompt=request.system_prompt
        )
        
    except Exception as e:
        logger.error(f"Error setting system prompt for {model_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set system prompt: {str(e)}"
        )

# Model Settings Management Endpoints

@app.get("/api/models/{model_name}/settings", response_model=ModelSettingsResponse)
async def get_model_settings(model_name: str):
    """
    Get generation settings for a specific model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        ModelSettingsResponse: Model settings
    """
    try:
        settings = persona_core.ollama_manager.get_model_settings(model_name)
        
        return ModelSettingsResponse(
            success=True,
            message="Model settings retrieved successfully",
            settings=settings
        )
        
    except Exception as e:
        logger.error(f"Error getting model settings for {model_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model settings: {str(e)}"
        )

@app.post("/api/models/{model_name}/settings", response_model=ModelSettingsResponse)
async def set_model_settings(model_name: str, request: ModelSettingsRequest):
    """
    Set generation settings for a specific model.
    
    Args:
        model_name: Name of the model
        request: ModelSettingsRequest containing the settings
        
    Returns:
        ModelSettingsResponse: Success status
    """
    try:
        if not request.settings:
            raise HTTPException(status_code=400, detail="Settings cannot be empty")
        
        persona_core.ollama_manager.set_model_settings(model_name, request.settings)
        
        return ModelSettingsResponse(
            success=True,
            message=f"Settings updated for model '{model_name}'",
            settings=request.settings
        )
        
    except Exception as e:
        logger.error(f"Error setting model settings for {model_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set model settings: {str(e)}"
        )

# TODO: Add additional endpoints for:
# - /api/tools/{tool_name}/execute - Direct tool execution
# - /api/config - Configuration management
# - /api/memory - Conversation history
# - /api/plugins - Plugin management
# - /api/logs - System logs and debugging

if __name__ == "__main__":
    import uvicorn
    
    print("Starting PersonaOS Web API...")
    print("API will be available at: http://localhost:8000")
    print("Documentation at: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )