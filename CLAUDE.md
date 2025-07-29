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
- `llm_handler.py` – Multi-backend LLM manager supporting Ollama and DME
- `base_model_handler.py` – Abstract interface for all model backends
- `llama_cpp_handler.py` – Direct Model Execution using llama-cpp-python
- `model_config_loader.py` – YAML-based model configuration management
- `memory.py` – Conversation memory with encryption support
- Supports Ollama (CLI/API) and DME (local GGUF models) backends
- `LLMManager` provides hot-swapping between different backends

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

**DevAgent System** (`core/dev_agent/`):
- `dev_agent.py` – Autonomous developer that accepts natural language tasks
- `project_navigator.py` – Maps project structure, dependencies, and provides context
- `file_manager.py` – Safe file operations with automatic backups and rollback
- `code_executor.py` – Secure command execution with timeout and safety controls
- `cli.py` – CLI interface for development tasks
- Integrates with PersonaOS LLM system for intelligent task planning

**Voice Pipeline System** (`core/voice/`, `core/sst/`, `core/tts/`):
- `voice_pipeline_controller.py` – Orchestrates STT → Intent → LLM → TTS workflow
- `whisper_stt_handler.py` – Speech-to-text using OpenAI Whisper
- `local_tts_handler.py` – Text-to-speech with voice synthesis
- Thread-safe voice conversation state management

**Direct Model Execution (DME) System**:
- `BaseModelHandler` – Abstract interface defining standard methods for all backends
- `LlamaCppHandler` – Concrete implementation using llama-cpp-python for local GGUF models
- `ModelConfigLoader` – YAML configuration system with environment variable overrides
- Supports CPU and GPU acceleration, streaming generation, and memory management
- `config/model_config.yaml` – Centralized backend configuration with multiple model definitions
- Hot-swappable backends without restart via `llm_manager.switch_backend()`

## Development Commands

### Environment Setup
```bash
# Automated installation (recommended for new users)
python install.py

# Manual dependency installation
pip install -r requirements.txt

# First-time setup (creates .env file)
python core/main.py

# Reset environment configuration
python core/main.py --reset-env
```

### Running the Application

**Universal Launcher:**
```bash
# Interactive interface selection menu
python start.py

# Force specific modes
python start.py --web          # Web UI mode
python start.py --health       # System diagnostics
```

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
# DME comprehensive test suite
python test_dme.py

# Test specific DME components
python -c "from core.llm.llama_cpp_handler import LlamaCppHandler; print('DME available')"

# Frontend development commands
cd persona_web_ui/frontend
npm run dev        # Development server
npm run build      # Production build
npm run lint       # Linting
npm run preview    # Preview production build

# Backend switching via environment
MODEL_BACKEND=llama_cpp python core/main.py
MODEL_BACKEND=ollama python core/main.py

# DevAgent testing and validation
python test_dev_agent_simple.py      # Quick DevAgent functionality test
python demo_dev_agent.py             # DevAgent capabilities demonstration

# Voice system testing
python test_voice_pipeline.py        # Voice pipeline integration test
python test_tts_system.py           # Text-to-speech system test
python core/sst/test_stt_system.py  # Speech-to-text system test

# Intent processing tests
python core/intent/test_intent_system.py  # Intent classification and safety tests
```

### Configuration

The system uses a `.env` file for configuration. Key variables:

**LLM Settings:**
- `LLM_PROVIDER` - LLM service (default: ollama)
- `MODEL_BACKEND` - Backend selection: ollama or llama_cpp (default: ollama)
- `OLLAMA_MODEL` - Ollama model name (default: openhermes)
- `OLLAMA_API_URL` - Ollama API URL (blank = CLI mode)

**DME (Direct Model Execution) Settings:**
- `LLAMA_CPP_MODEL_PATH` - Path to GGUF model file
- `LLAMA_CPP_N_CTX` - Context length (default: 2048)
- `LLAMA_CPP_N_GPU_LAYERS` - GPU layers for acceleration (default: 0)
- `LLAMA_CPP_TEMPERATURE` - Sampling temperature (default: 0.7)

**Web UI Settings:**
- `WEB_UI_ENABLED` - Enable web UI (default: true)
- `WEB_UI_PORT` - Backend port (default: 8000)
- `FRONTEND_PORT` - Frontend dev server port (default: 3000)

**Intent & Safety:**
- `INTENT_ENABLED` - Enable intent processing (default: true)
- `SAFETY_LEVEL` - strict, standard, or relaxed (default: standard)
- `ALLOW_TOOL_EXECUTION` - Allow plugin execution (default: true)

**Voice & Audio:**
- `STT_ENABLED` - Enable speech-to-text (default: false)
- `VOICE_PIPELINE_ENABLED` - Enable voice conversation pipeline (default: true)
- `TTS_ENABLED` - Enable text-to-speech (default: false)
- `WHISPER_MODEL` - Whisper model size for STT (default: base)

**DevAgent:**
- `DEV_AGENT_ENABLED` - Enable autonomous development features (default: true)
- `DEV_AGENT_SAFE_MODE` - Block dangerous commands (default: true)
- `DEV_AGENT_DRY_RUN` - Test mode without file modifications (default: false)

**Memory & Storage:**
- `MEMORY_ENABLED` - Enable conversation memory (default: true)
- `USE_ENCRYPTED_STORAGE` - Encrypt memory storage (default: true)
- `MEMORY_RETENTION_DAYS` - Days to keep conversations (default: 30)

**Development:**
- `DEBUG_MODE` - Enable debug logging (default: false)
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR (default: INFO)

**Model Configuration (config/model_config.yaml):**
PersonaOS also supports a YAML-based configuration system for model backends:
- Multiple backend definitions with detailed parameters
- Environment variable override support
- Hot-swappable backend configurations
- Recommended model suggestions with download URLs
- Per-backend settings for temperature, context length, GPU layers

## Key Implementation Details

### LLM Handler Architecture
The LLM system uses a multi-backend architecture with `LLMManager` that initializes specific handlers based on configuration:

**Backend Abstraction:**
- `BaseModelHandler` - Abstract interface defining standard methods (`load_model()`, `generate()`, `generate_streaming()`, `stop()`, `unload_model()`)
- All backends implement the same interface for seamless switching

**Supported Backends:**
- `OllamaHandler` - Handles both CLI (`ollama chat`) and API calls for Ollama models
- `LlamaCppHandler` - Direct model execution using llama-cpp-python for local GGUF models

**Key Features:**
- Hot-swapping between backends without restart via `llm_manager.switch_backend()`
- Streaming generation support for real-time interaction
- GPU acceleration configuration for DME backends
- Model management through web UI and YAML configuration
- Automatic fallback to Ollama if DME initialization fails

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

### DevAgent Architecture
Autonomous development system with four core components:
- **DevAgent**: Main orchestrator that plans and executes development tasks
- **ProjectNavigator**: Indexes project structure, maps dependencies, provides context
- **FileManager**: Safe file operations with automatic backups, rollback capability
- **CodeExecutor**: Secure command execution with timeout, sandboxing, and safety controls

**DevAgent Task Flow:**
1. **Natural Language Input**: Accept development requests in plain English (e.g., "Add error handling to API endpoints")
2. **LLM Planning**: Use PersonaOS LLM system to generate implementation steps
3. **Context Analysis**: ProjectNavigator provides relevant files and dependencies
4. **Safe Execution**: FileManager creates backups, CodeExecutor runs commands safely
5. **Iterative Improvement**: Retry based on test results and error feedback
6. **Rollback Support**: Complete undo capability for any completed task

**DevAgent CLI Commands:**
- `dev: <task description>` - Execute development task
- `dev-status [task_id]` - Show task status and progress
- `dev-history [limit]` - Show recent development tasks  
- `dev-rollback <task_id>` - Undo changes from specific task
- `dev-cancel` - Cancel currently running task
- `dev-system` - Show DevAgent system status

### Voice Pipeline Architecture
Complete voice conversation system:
- **VoicePipelineController**: Orchestrates STT → Intent → LLM → TTS workflow
- **Thread Safety**: Manages voice state across concurrent operations
- **Audio Processing**: Handles microphone input and speaker output
- **Integration**: Works with existing PersonaOS intent processing and safety systems

**Voice Command Flow:**
1. **Audio Capture**: Continuous microphone monitoring with wake word detection
2. **Speech-to-Text**: Whisper-based transcription with confidence scoring
3. **Intent Processing**: Safety validation and tool execution routing
4. **LLM Response**: Context-aware response generation with memory
5. **Text-to-Speech**: Natural voice synthesis with emotion and timing
6. **Audio Feedback**: Speaker output with volume and quality control

## Important Notes

**Development Workflow:**
- Environment setup is mandatory before first run (`python core/main.py` for initial setup)
- Web UI requires both backend and frontend to be running simultaneously
- Frontend uses Vite for hot reloading during development
- DevAgent provides autonomous development assistance via `dev:` commands
- Voice pipeline enables hands-free interaction (requires microphone/speaker setup)
- Custom test scripts in project root test individual components (no pytest framework)

**Security Considerations:**
- API keys are stored in encrypted format when possible
- Memory conversations can be encrypted at rest
- Safety validation is mandatory for all tool executions
- DevAgent uses safe mode to block dangerous commands (rm, sudo, etc.)
- All file modifications create automatic backups with rollback capability
- Web UI includes CORS configuration for local development

**Architecture Design:**
- Modular structure supports current voice/development features and future extensions
- Intent processing separates concerns of classification, safety, and execution
- Memory system designed for long-term conversation context across CLI, web, and voice
- Tool system uses factory pattern for dynamic loading and plugin extensibility
- DevAgent provides autonomous development capabilities with full safety controls
- Voice pipeline enables natural language interaction through complete STT→LLM→TTS flow