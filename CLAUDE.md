# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PersonaOS is a modular AI personality operating system designed for embodied agents and humanoid robots. This is version 0.1.0, an MVP that focuses on CLI interaction with local LLMs via Ollama.

## Core Architecture

### Entry Points
- `core/main.py` - Main application entry point with conversation loop
- `cli/cli.py` - Alternative CLI interface with advanced options
- `setup_env.py` - Environment configuration wizard

### Key Components

**LLM Integration** (`core/llm/`):
- `llm_handler.py` - Main LLM manager with OllamaHandler class
- Supports both CLI and API modes for Ollama
- Uses `LLMManager` to abstract different LLM providers

**Configuration System**:
- `core/config.py` - Loads runtime config from environment variables
- `.env.template` - Template for environment configuration
- `setup_env.py` - Interactive setup wizard for `.env` file

**Modular Structure**:
- `core/wakeword/` - Wake word detection (Porcupine)
- `core/sst/`, `core/tts/` - Speech-to-text and text-to-speech (placeholders)
- `core/audio.py` - Audio processing utilities
- Designed for easy extensibility with additional modules

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
```bash
# Main CLI interface
python core/main.py

# Advanced CLI with options
python cli/cli.py --query "Hello" --llm ollama

# Show current config
python cli/cli.py --config

# Set config option
python cli/cli.py --set-config LLM_MODEL ollama
```

### Configuration

The system uses a `.env` file for configuration. Key variables:
- `LLM_PROVIDER` - LLM service (default: ollama)
- `OLLAMA_MODEL` - Ollama model name (default: openhermes)
- `PICOVOICE_API_KEY` - For wake word detection
- `DEBUG_MODE` - Enable debug logging

## Key Implementation Details

### LLM Handler Architecture
The LLM system uses a manager pattern with `LLMManager` that initializes specific handlers based on configuration. Currently supports:
- `OllamaHandler` - Handles both CLI (`ollama chat`) and API calls

### Memory System
Memory management is stubbed out in the current implementation via `MemoryManager` class, designed for future conversation context storage.

### Error Handling
The system includes proper error handling for:
- Missing environment configuration
- Failed LLM API/CLI calls
- Subprocess execution errors

### Module Loading
Uses dynamic imports in `core/llm_handler.py` to support multiple LLM backends without tight coupling.

## Important Notes

- The codebase is structured for modularity with placeholder directories for future features
- Environment setup is mandatory before first run
- CLI interface supports single-query mode and interactive conversation
- Configuration can be modified at runtime via CLI flags
- No test framework is currently configured