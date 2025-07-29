# PersonaOS Specification (v0.1.0)

A technical and strategic specification for the PersonaOS MVP (Minimum Viable Product).

---

## Table of Contents

1. [Overview](#1-overview)  
2. [Goals & Philosophy](#2-goals--philosophy)  
3. [Key Design Principles](#3-key-design-principles)  
4. [Core Modules](#4-core-modules)  
5. [Runtime Workflow](#5-runtime-workflow)  
6. [Installation & Setup](#6-installation--setup)  
7. [CLI Interfaces](#7-cli-interfaces)  
8. [Configuration & Environment](#8-configuration--environment)  
9. [Current Features (v0.1.0)](#9-current-features-v010)  
10. [Direct Model Execution (DME) Architecture](#10-direct-model-execution-dme-architecture)  
11. [Planned Features & Roadmap](#11-planned-features--roadmap)  
12. [Development Guidelines](#12-development-guidelines)  
13. [License & Contribution](#13-license--contribution)  
14. [Appendix: OVOS Integration Plan](#14-appendix-ovos-integration-plan)  
15. [Final Thoughts](#15-final-thoughts)  

---

## 1. Overview

PersonaOS is a modular, privacy-focused AI personality operating system designed to run on local hardware with optional embodiment capabilities (e.g. voice interface, robotics, smart search tools).

Version 0.1.0 includes both CLI and web UI interfaces, supporting conversation with local LLMs via Ollama and Direct Model Execution (DME) using llama-cpp-python, with comprehensive intent processing, safety validation, and tool execution capabilities.

---

## 2. Goals & Philosophy

- **Modular from the start** — Each part of the system can be replaced or extended.
- **Local-first** — Prioritizes offline capabilities and privacy.
- **LLM-native** — Designed to work with local large language models.
- **CLI-first** — No GUI dependency in the MVP.
- **Human-in-the-loop** — Developers retain control over what tools are executed.

---

## 3. Key Design Principles

- **Separation of intent and execution** — LLMs produce intent; rules/tools determine what gets executed.
- **Extensibility over complexity** — Simple components that are easy to extend.
- **No daemon lock-in** — Runs as a user-space app, not a background service (yet).
- **Embodiment-ready** — Audio I/O, wake word detection, and sensor modules are part of the roadmap.

---

## 4. Core Modules

| Module                  | Path                          | Status        | Description                                             |
|-------------------------|-------------------------------|----------------|---------------------------------------------------------|
| Main CLI loop           | `core/main.py`                | ✅ Implemented  | Launches the main conversational loop.                 |
| Env setup wizard        | `setup_env.py`                | ✅ Implemented  | Walks user through .env creation.                      |
| Config loader           | `core/config.py`              | ✅ Implemented  | Loads and validates runtime settings.                  |
| LLM Manager             | `core/llm/llm_handler.py`     | ✅ Implemented  | Multi-backend LLM system (Ollama, DME via llama-cpp).  |
| Base Model Handler      | `core/llm/base_model_handler.py` | ✅ Implemented  | Abstract interface for all model backends.             |
| LlamaCpp Handler        | `core/llm/llama_cpp_handler.py`  | ✅ Implemented  | Direct model execution using llama-cpp-python.         |
| Model Config Loader     | `core/llm/model_config_loader.py` | ✅ Implemented  | YAML-based model configuration management.             |
| Memory system           | `core/llm/memory.py`          | ✅ Implemented  | Conversation memory with encryption support.           |
| Intent processing       | `core/intent/`                | ✅ Implemented  | Intent classification, safety validation, and processing.|
| Tool system             | `core/tools/`                 | ✅ Implemented  | Plugin-based tool architecture with registry.         |
| Web UI backend          | `persona_web_ui/backend/`     | ✅ Implemented  | FastAPI backend for web interface.                     |
| Web UI frontend         | `persona_web_ui/frontend/`    | ✅ Implemented  | React frontend with Vite development server.          |
| Audio utilities         | `core/audio.py`               | 🟡 Placeholder  | Audio I/O helpers (to be extended).                    |
| Wake word detection     | `core/wakeword/`              | 🟡 Partial      | Basic Porcupine wrapper implemented.                   |
| Speech-to-text (STT)    | `core/sst/`                   | 🟡 Placeholder  | Placeholder directory for future STT integration.      |
| Text-to-speech (TTS)    | `core/tts/`                   | 🟡 Placeholder  | Placeholder directory for future TTS integration.      |
| CLI utilities           | `cli/cli.py`                  | ✅ Implemented  | Enables queries, config setting, and debugging.        |

---

## 5. Runtime Workflow

A high-level overview of how the PersonaOS system processes input and produces output:

```plaintext
[User Input: CLI / Audio]
          ↓
   [Input Parsing Layer]
          ↓
   [Intent Classification]
          ↓
  [Intent Safety & Validation]
          ↓
  ┌────────────┬────────────┐
  │ LLM Output │ Tool Calls │
  └────────────┴────────────┘
          ↓
     [Response TTS]
          ↓
     [Audio Output]
```

Key decision points:
- Tool execution is only invoked if the intent is validated and mapped to a tool.
- LLM output is passed directly to TTS otherwise.

---

## 6. Installation & Setup

### ⚙️ Requirements
- Python 3.10+
- Ollama (for Ollama backend LLMs)
- Git

### 🧠 Optional DME Requirements
- **llama-cpp-python** (for Direct Model Execution)
- **GGUF model files** (quantized LLaMA models)
- **4GB+ RAM** (minimum for 7B models)
- **GPU with CUDA** (optional, for acceleration)

### 🧱 First-Time Setup

```bash
# Clone the repository
git clone https://github.com/personaos/PersonaOS.git
cd PersonaOS

# Install Python dependencies
python -m pip install -r requirements.txt

# Launch onboarding and environment setup
python core/main.py
```

---

## 7. CLI Interfaces

### 🔁 Main Loop
Interactive CLI conversation:
```bash
python core/main.py
```

### 🎯 One-shot Query
Send a one-off query to the LLM:
```bash
python cli/cli.py --query "What is PersonaOS?"
```

### 🔧 Configuration
Inspect or modify settings:
```bash
python cli/cli.py --config
python cli/cli.py --set-config LLM_MODEL mistral
```

### 🧠 DME Testing & Management
Test Direct Model Execution functionality:
```bash
# Run comprehensive DME test suite
python test_dme.py

# Test specific DME components
python -c "from core.llm.llama_cpp_handler import LlamaCppHandler; print('DME available')"

# Switch model backend via environment
MODEL_BACKEND=llama_cpp python core/main.py
```

---

## 8. Configuration & Environment

PersonaOS loads config variables from a `.env` file created by `setup_env.py`.

### 🔑 Example `.env`
```env
# LLM Backend Configuration
LLM_PROVIDER=ollama
MODEL_BACKEND=ollama              # or 'llama_cpp' for DME

# Ollama Configuration (if using Ollama backend)
OLLAMA_MODEL=openhermes
OLLAMA_API_URL=http://localhost:11434

# DME Configuration (if using llama-cpp backend)
LLAMA_CPP_MODEL_PATH=models/openhermes-2.5-mistral-7b.Q4_K_M.gguf
LLAMA_CPP_N_CTX=2048
LLAMA_CPP_N_GPU_LAYERS=0          # 0 for CPU-only, >0 for GPU acceleration
LLAMA_CPP_TEMPERATURE=0.7

# Other Settings
PICOVOICE_API_KEY=your_key_here
DEBUG_MODE=True
```

### 🧠 DME Model Configuration
DME also supports a separate `config/model_config.yaml` file for detailed model backend configuration:

```yaml
# Set default backend
default_backend: "llama_cpp"

backends:
  llama_cpp:
    type: "llama_cpp"
    model_path: "models/openhermes-2.5-mistral-7b.Q4_K_M.gguf"
    n_ctx: 2048
    n_gpu_layers: 0
    temperature: 0.7
    max_tokens: 512
```

---

## 9. Current Features (v0.1.0)

| Feature                        | Status        | Description                                     |
|-------------------------------|----------------|-------------------------------------------------|
| Modular LLM system            | ✅ Implemented  | Multi-backend system supporting Ollama and DME. |
| Direct Model Execution (DME)  | ✅ Implemented  | Local GGUF model execution via llama-cpp-python.|
| CLI input/output              | ✅ Implemented  | Text-based interaction loop.                    |
| Web UI interface              | ✅ Implemented  | FastAPI backend with React frontend.           |
| Config wizard & validation    | ✅ Implemented  | User-friendly onboarding and setup.             |
| Intent processing system      | ✅ Implemented  | Complete intent classification and validation.  |
| Safety validation system      | ✅ Implemented  | Configurable safety levels with validation.     |
| Memory management             | ✅ Implemented  | Encrypted conversation storage and retrieval.   |
| Tool execution engine         | ✅ Implemented  | Plugin-based tool system with safety gates.    |
| API key management            | ✅ Implemented  | Encrypted storage and management of API keys.   |
| Model management              | ✅ Implemented  | YAML-based configuration with hot-swapping.     |
| Streaming generation          | ✅ Implemented  | Real-time token streaming for DME backends.     |
| GPU acceleration              | ✅ Implemented  | Configurable GPU layer support for DME.         |
| Backend switching             | ✅ Implemented  | Runtime switching between Ollama and DME.       |
| Wake word detection           | 🟡 Partial      | Basic Porcupine wrapper implemented.           |
| STT/TTS integration           | 🟡 Placeholder  | Directory structure and placeholders ready.     |

---

## 10. Direct Model Execution (DME) Architecture

### 🧠 Overview
PersonaOS v0.1.0 introduces Direct Model Execution (DME), enabling local execution of quantized GGUF models without external dependencies like Ollama. This provides enhanced privacy, performance control, and independence from external services.

### 🏗️ Architecture Components

#### BaseModelHandler Interface
- **Location**: `core/llm/base_model_handler.py`
- **Purpose**: Abstract interface defining standard methods for all model backends
- **Key Methods**: `load_model()`, `generate()`, `generate_streaming()`, `stop()`, `unload_model()`

#### LlamaCppHandler Implementation  
- **Location**: `core/llm/llama_cpp_handler.py`
- **Purpose**: Concrete implementation using llama-cpp-python
- **Features**: 
  - CPU and GPU acceleration support
  - Streaming token generation
  - Configurable model parameters (temperature, top_p, context length)
  - Memory management and model unloading

#### Model Configuration System
- **Location**: `core/llm/model_config_loader.py` + `config/model_config.yaml`
- **Purpose**: YAML-based configuration with environment variable overrides
- **Features**:
  - Multiple backend definitions
  - Runtime backend switching
  - Model parameter tuning
  - Recommended model suggestions

### 🚀 Key Features

| Feature | Description | Configuration |
|---------|-------------|---------------|
| **Multi-Backend Support** | Switch between Ollama and DME at runtime | `MODEL_BACKEND=llama_cpp` |
| **Streaming Generation** | Real-time token output for responsive interaction | Built-in to `generate_streaming()` |
| **GPU Acceleration** | Configurable GPU layer offloading | `n_gpu_layers: 20` |
| **Memory Management** | Explicit model loading/unloading control | `load_model()` / `unload_model()` |
| **Hot Swapping** | Change backends without restart | `llm_manager.switch_backend()` |

### 📋 Supported Model Formats
- **GGUF**: Quantized LLaMA models (Q4_K_M, Q5_K_M, Q8_0, etc.)
- **Context Lengths**: 512 to 32768+ tokens
- **Model Sizes**: 1B to 70B+ parameters (hardware dependent)

### 🎯 Performance Characteristics
- **CPU-Only**: ~2-5 tokens/sec for 7B models on modern hardware
- **GPU-Accelerated**: ~10-50 tokens/sec depending on GPU memory
- **Memory Usage**: ~4-8GB RAM for 7B Q4 models
- **Cold Start**: 2-10 seconds model loading time

### 🔧 Configuration Examples

#### Basic DME Setup
```yaml
# config/model_config.yaml
default_backend: "llama_cpp"
backends:
  llama_cpp:
    type: "llama_cpp"
    model_path: "models/openhermes-2.5-mistral-7b.Q4_K_M.gguf"
    n_ctx: 2048
    temperature: 0.7
```

#### GPU-Accelerated Setup
```yaml
llama_cpp_gpu:
  type: "llama_cpp"
  model_path: "models/llama-2-13b-chat.Q4_K_M.gguf"
  n_ctx: 4096
  n_gpu_layers: 20
  temperature: 0.8
```

---

## 11. Planned Features & Roadmap

### 🧠 Phase 1: Enhanced Voice & Integration (v0.2.x)
- [ ] Integrate Whisper STT
- [ ] Add Coqui / pyttsx3 TTS
- [ ] Looping audio engine
- [x] Intent classification module ✅
- [x] Tool registry and execution ✅
- [x] Memory system with encryption ✅
- [ ] Enhanced wake word detection
- [ ] Voice-first web UI mode

### 🧩 Phase 2: Plugin Framework (v0.3.x)
- [ ] Intent safety + policy engine
- [ ] Plugin system for tools
- [ ] Dynamic skill loading
- [ ] External app integration (e.g., calendar, files)

### 🤖 Phase 3: Embodied Agent (v0.4+)
- [ ] Vision integration (OpenCV / depth)
- [ ] Servo/motor control hooks
- [ ] Multimodal LLM support
- [ ] Persona memory and long-term history

---

## 12. Development Guidelines

### 🧱 Structure

```plaintext
/core/       # Core modules
/cli/        # CLI tools
/tests/      # (Coming soon)
/assets/     # Audio, wakeword, etc.
/env/        # .env template and setup
```

### 🧼 Conventions
- Python 3.10+ only
- Use `loguru` for logs
- Use `dotenv` for env config
- Lint with `ruff` or `flake8`

---

## 13. License & Contribution

🔐 Currently closed-source, early prototype.  
📌 License TBD — likely MIT or Apache 2.0  
🧠 Contributors may be invited after v0.2 MVP is complete.

---

## 14. Appendix: OVOS Integration Plan

| OVOS Module           | Status     | Notes                                     |
|-----------------------|------------|-------------------------------------------|
| OVOS Precise Wakeword | ✅ Planned | Local wake word via Precise engine        |
| Mimic3 TTS            | ✅ Planned | High-quality offline speech synthesis     |
| Plugin system         | 🟡 Designing | Only inspiration, not direct reuse        |
| Mycroft Core          | ❌ Avoided | Avoids message bus & hardcoded pipeline   |

---

## 15. Final Thoughts

PersonaOS is not just another assistant — it’s the beginning of a **true AI personality framework** built for privacy, modularity, and embodiment.

> Designed by a solo developer with GPT-4 + Claude as copilots.  
> For questions, bugs, or collaboration, open an issue or reach out.

---
