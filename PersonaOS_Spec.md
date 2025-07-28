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
10. [Planned Features & Roadmap](#10-planned-features--roadmap)  
11. [Development Guidelines](#11-development-guidelines)  
12. [License & Contribution](#12-license--contribution)  
13. [Appendix: OVOS Integration Plan](#13-appendix-ovos-integration-plan)  
14. [Final Thoughts](#14-final-thoughts)  

---

## 1. Overview

PersonaOS is a modular, privacy-focused AI personality operating system designed to run on local hardware with optional embodiment capabilities (e.g. voice interface, robotics, smart search tools).

Version 0.1.0 includes both CLI and web UI interfaces, supporting conversation with local LLMs via Ollama, with comprehensive intent processing, safety validation, and tool execution capabilities.

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
| LLM Manager             | `core/llm/llm_handler.py`     | ✅ Implemented  | Connects to Ollama LLM backend (CLI and API modes).    |
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
- Ollama (for local LLMs)
- Git

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

---

## 8. Configuration & Environment

PersonaOS loads config variables from a `.env` file created by `setup_env.py`.

### 🔑 Example `.env`
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=openhermes
OLLAMA_API_URL=http://localhost:11434
PICOVOICE_API_KEY=your_key_here
DEBUG_MODE=True
```

---

## 9. Current Features (v0.1.0)

| Feature                        | Status        | Description                                     |
|-------------------------------|----------------|-------------------------------------------------|
| Modular LLM system            | ✅ Implemented  | Uses `OllamaHandler` under the `LLMManager`.    |
| CLI input/output              | ✅ Implemented  | Text-based interaction loop.                    |
| Web UI interface              | ✅ Implemented  | FastAPI backend with React frontend.           |
| Config wizard & validation    | ✅ Implemented  | User-friendly onboarding and setup.             |
| Intent processing system      | ✅ Implemented  | Complete intent classification and validation.  |
| Safety validation system      | ✅ Implemented  | Configurable safety levels with validation.     |
| Memory management             | ✅ Implemented  | Encrypted conversation storage and retrieval.   |
| Tool execution engine         | ✅ Implemented  | Plugin-based tool system with safety gates.    |
| API key management            | ✅ Implemented  | Encrypted storage and management of API keys.   |
| Model management              | ✅ Implemented  | Web UI for loading/downloading/removing models. |
| Wake word detection           | 🟡 Partial      | Basic Porcupine wrapper implemented.           |
| STT/TTS integration           | 🟡 Placeholder  | Directory structure and placeholders ready.     |

---

## 10. Planned Features & Roadmap

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

## 11. Development Guidelines

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

## 12. License & Contribution

🔐 Currently closed-source, early prototype.  
📌 License TBD — likely MIT or Apache 2.0  
🧠 Contributors may be invited after v0.2 MVP is complete.

---

## 13. Appendix: OVOS Integration Plan

| OVOS Module           | Status     | Notes                                     |
|-----------------------|------------|-------------------------------------------|
| OVOS Precise Wakeword | ✅ Planned | Local wake word via Precise engine        |
| Mimic3 TTS            | ✅ Planned | High-quality offline speech synthesis     |
| Plugin system         | 🟡 Designing | Only inspiration, not direct reuse        |
| Mycroft Core          | ❌ Avoided | Avoids message bus & hardcoded pipeline   |

---

## 14. Final Thoughts

PersonaOS is not just another assistant — it’s the beginning of a **true AI personality framework** built for privacy, modularity, and embodiment.

> Designed by a solo developer with GPT-4 + Claude as copilots.  
> For questions, bugs, or collaboration, open an issue or reach out.

---
