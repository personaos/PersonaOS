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
from pathlib import Path
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
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