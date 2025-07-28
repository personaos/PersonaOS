# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PersonaOS is a modular AI personality operating system designed for embodied agents and humanoid robots. This is version 0.1.0, an MVP focused on CLI interaction with local LLMs via Ollama, featuring a FastAPI backend and React frontend for web-based interaction.

For long-term goals, see `ROADMAP.md` – which outlines a 5-stage evolution toward memory, autonomy, and embodied interaction.

## Core Architecture

### Entry Points
- `core/main.py` – Main CLI application with conversation loop
- `persona_web_ui/backend/main.py` – FastAPI web backend
- `persona_web_ui/frontend/` – React frontend application
- `setup_env.py` – Environment configuration wizard

### Key Components

**LLM Integration** (`core/llm/`):
- `llm_handler.py` – Main LLM manager with `OllamaHandler`
- `memory.py` – Conversation memory with encryption support
- Supports both CLI and API modes for Ollama
- `LLMManager` abstracts different LLM providers

**Intent Processing & Safety** (`core/intent/`):
- `intent_processor.py` – Main intent processing pipeline
- `intent_classifier.py` – Classifies user intents (safe, tool, unsafe)
- `safety_validator.py` – Safety validation with configurable levels
- Handles tool execution and safety blocking

**Configuration System**:
- `core/config.py` – Secure config loader with encrypted API key support
- `.env.template` – Template for environment configuration
- All config values centrally managed

**Web UI Architecture**:
- FastAPI backend with RESTful endpoints
- React frontend with Vite development server
- CORS configured for local development only

**Tool System** (`core/tools/`):
- Plugin-based tool architecture with dynamic loading
- Tool registry and factory pattern for extensibility
- Intent-based tool execution with safety validation

## Development Commands

### Environment Setup
```bash
# First-time setup (creates .env file)
python core/main.py

# Reset environment configuration
python core/main.py --reset-env

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

**CLI Mode:**
```bash
# Main CLI interface
python core/main.py

# Reset environment configuration
python core/main.py --reset-env
```

**Web UI Mode:**
```bash
# Option 1: Use the automated startup script (recommended)
start_webui.bat

# Option 2: Manual startup
# Start the FastAPI backend (backend runs on port 8000)
cd persona_web_ui/backend
python main.py

# Start the React frontend (in separate terminal, runs on configured port from .env)
cd persona_web_ui/frontend
npm install
npm run dev
```

**Port Configuration:**
- Backend: Port 8000 (configurable via WEB_UI_PORT in .env)
- Frontend: Port 5173 (configurable via FRONTEND_PORT in .env)
- Vite automatically increments port if configured port is unavailable (5173→5174→5175→etc.)
- CORS is configured to allow multiple port ranges for development flexibility

**Testing and Development:**
```bash
# Frontend linting
cd persona_web_ui/frontend
npm run lint

# Frontend build
npm run build
```

### Configuration

The system uses a `.env` file for configuration. Key variables:

**LLM Settings:**
- `LLM_PROVIDER` - LLM service (default: ollama)
- `OLLAMA_MODEL` - Ollama model name (default: openhermes)
- `OLLAMA_API_URL` - Ollama API URL (blank = CLI mode)

**Web UI Settings:**
- `WEB_UI_ENABLED` - Enable web UI (default: true)
- `WEB_UI_PORT` - Backend port (default: 8000)
- `FRONTEND_PORT` - Frontend dev server port (default: 3000)

**Intent & Safety:**
- `INTENT_ENABLED` - Enable intent processing (default: true)
- `SAFETY_LEVEL` - strict, standard, or relaxed (default: standard)
- `ALLOW_TOOL_EXECUTION` - Allow plugin execution (default: true)

**Memory & Storage:**
- `MEMORY_ENABLED` - Enable conversation memory (default: true)
- `USE_ENCRYPTED_STORAGE` - Encrypt memory storage (default: true)
- `MEMORY_RETENTION_DAYS` - Days to keep conversations (default: 30)

**Development:**
- `DEBUG_MODE` - Enable debug logging (default: false)
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR (default: INFO)

## Key Implementation Details

### LLM Handler Architecture
The LLM system uses a manager pattern with `LLMManager` that initializes specific handlers based on configuration. Currently supports:
- `OllamaHandler` - Handles both CLI (`ollama chat`) and API calls
- Model management through web UI with load/download/remove operations

### Memory System
Comprehensive conversation memory with the following features:
- Thread-based conversation storage with encryption
- Configurable retention policies and session limits
- Search capabilities across conversation history
- Context trimming for LLM token limits

### Intent Processing Pipeline
Three-stage intent processing for safety and tool execution:
1. **Intent Classification** - Categorizes user input (safe, tool_required, unsafe)
2. **Safety Validation** - Validates against configurable safety levels
3. **Tool Execution** - Executes approved tools with result formatting

### Web API Architecture
FastAPI backend providing:
- Message processing endpoints (`/api/message`)
- Model management (`/api/models/*`)
- Setup configuration (`/api/setup/*`)
- Tool listing and execution
- Health checks and system status

### Error Handling & Security
- Comprehensive error handling for LLM failures and network issues
- API key encryption and secure storage
- Request validation and rate limiting preparation
- Safety validation for all tool executions

### Plugin System
Tool-based plugin architecture:
- Dynamic tool loading with factory functions
- Intent-based tool selection and safety validation
- Centralized tool registry for management
- Configurable tool execution permissions

## Important Notes

**Development Workflow:**
- Environment setup is mandatory before first run (`python core/main.py` for initial setup)
- Web UI requires both backend and frontend to be running simultaneously
- Frontend uses Vite for hot reloading during development
- No formal test framework is currently configured

**Security Considerations:**
- API keys are stored in encrypted format when possible
- Memory conversations can be encrypted at rest
- Safety validation is mandatory for all tool executions
- Web UI includes CORS configuration for local development

**Architecture Design:**
- Modular structure supports future extensions (STT, TTS, vision)
- Intent processing separates concerns of classification, safety, and execution
- Memory system designed for long-term conversation context
- Tool system uses factory pattern for dynamic loading