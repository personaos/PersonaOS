# 🤖 PersonaOS v0.1.0

**PersonaOS** is an open, modular AI personality operating system designed to bring humanoid robots and embodied agents to life.

It connects language models, speech, and vision into a unified pipeline that enables machines to talk, think, and eventually feel — starting with basic x86 hardware (like Intel NUCs or Mini PCs).

PersonaOS aims to be the foundation for privacy-first, embodied AI that runs locally and autonomously — bridging language, memory, and interaction.

---

## 🚀 Quick Start (New Users)

**Never used PersonaOS before?** Get up and running in 3 steps:

### 1. Download PersonaOS
```bash
git clone https://github.com/personaos/PersonaOS.git
cd PersonaOS
```

### 2. Run the Automated Installer
```bash
python install.py
```
*This installs all dependencies, sets up Ollama, and configures everything automatically.*

### 3. Start PersonaOS
```bash
python start.py
```
*Choose between CLI mode or Web UI mode from the interactive menu.*

**That's it!** 🎉 Your AI assistant is ready to use.

---

## 🛠️ Developer Setup

**Already familiar with AI systems?** Skip the automation:

### Manual Installation
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Ollama (https://ollama.com)
# Windows: Download installer
# Linux/macOS: curl -fsSL https://ollama.com/install.sh | sh

# 3. Setup environment
python core/main.py  # Triggers configuration wizard

# 4. For Web UI (optional)
cd persona_web_ui/frontend
npm install
```

### Direct Usage
```bash
# CLI interface
python core/main.py

# Web UI (manual startup)
cd persona_web_ui/backend && python main.py  # Terminal 1
cd persona_web_ui/frontend && npm run dev     # Terminal 2

# Or use the startup script
start_webui.bat  # Windows
./start_webui.sh # Linux/macOS
```

---

## ✨ Key Features (MVP v0.1.0)

✅ **Multiple Interfaces:**
- 🖥️ CLI mode for terminal users
- 🌐 Web UI for browser-based interaction
- 🔄 Universal launcher with smart detection

✅ **AI Integration:**
- 🧠 Local LLM via [Ollama](https://ollama.com) (CLI or API) + Direct Model Execution
- 🧠 Memory system for contextual dialogue with encryption
- 🎯 Intent processing and safety validation
- 🤖 **DevAgent**: Autonomous development assistant via natural language
- 🎤 **Voice Pipeline**: Complete STT → LLM → TTS conversation system

✅ **User Experience:**
- 🛠️ Automated installer for all prerequisites
- ⚙️ Interactive setup wizard with smart defaults
- 🔧 System health checks and auto-repair
- 📱 Desktop shortcuts and system integration

✅ **Developer Friendly:**
- 🧩 Modular architecture for easy extension
- 🔌 Plugin system for custom tools
- 📝 Comprehensive documentation
- 🔍 Debug modes and logging
- 🛠️ **DevAgent**: AI-powered development automation with `dev:` commands
- 🔄 **Hot-swappable backends**: Switch between Ollama and local GGUF models
- 🛡️ **Safe operations**: Automatic backups, rollback, and command validation

---

## 📋 Prerequisites

**Automatic Installation (Recommended):**
- Python 3.7+ 
- Internet connection
- *Everything else is installed automatically*

**Manual Installation:**
- Python 3.7+
- [Ollama](https://ollama.com) (AI model runner)
- Node.js 16+ (for Web UI)
- Git (for updates)

---

## 🎯 Usage Examples

### For Beginners
```bash
python start.py
# → Interactive menu appears
# → Choose "1" for simple chat
# → Choose "2" for web interface
```

### For Developers  
```bash
python core/main.py                    # Direct CLI access
python core/main.py --reset-env        # Reconfigure settings
python start.py --web                  # Force Web UI mode
python start.py --health               # System diagnostics

# DevAgent Commands (within PersonaOS conversation)
dev: Add error handling to API endpoints     # Autonomous development task
dev-status                                   # Show current task status
dev-history                                  # Show recent development tasks
dev-system                                   # Show DevAgent system status

# Voice Features (requires microphone/speaker)
python core/main.py --voice-only             # Voice-only interaction mode
python core/main.py --voice-status           # Check voice pipeline status
```

### Configuration
```bash
# Quick setup with defaults
python install.py --defaults

# Manual configuration
python setup_env.py

# Reset everything
python core/main.py --reset-env

# Testing Components
python test_dev_agent_simple.py        # Test DevAgent functionality
python demo_dev_agent.py              # DevAgent demonstration
python test_voice_pipeline.py         # Test voice conversation system
python test_dme.py                     # Test Direct Model Execution
```

---

## 🤖 DevAgent: AI-Powered Development

PersonaOS includes **DevAgent** - an autonomous development assistant that executes coding tasks through natural language commands:

### Key DevAgent Features
- **Natural Language Tasks**: `dev: Add error handling to user authentication`
- **Intelligent Planning**: Uses LLM to break down tasks into implementation steps
- **Safe Operations**: Automatic backups, rollback capability, command validation
- **Project Awareness**: Understands codebase structure and dependencies
- **Iterative Improvement**: Learns from test results and errors

### DevAgent Commands
```bash
# Within PersonaOS conversation
dev: Create a logging utility with different levels    # Execute development task
dev-status                                            # Show current task progress
dev-history 10                                        # Show last 10 tasks
dev-rollback task_12345                              # Undo changes from specific task
dev-cancel                                           # Cancel running task
dev-system                                           # Show system status
```

### Example DevAgent Tasks
- `dev: Add input validation to the registration form`
- `dev: Refactor the database connection handling for better error recovery`
- `dev: Create unit tests for the authentication module`
- `dev: Optimize the image processing pipeline for memory usage`
- `dev: Add logging and monitoring to the API endpoints`

---

## 🎤 Voice Interaction

PersonaOS supports natural voice conversations through its integrated voice pipeline:

### Voice Features
- **Speech-to-Text**: OpenAI Whisper-based transcription
- **Natural Conversations**: Complete STT → Intent → LLM → TTS workflow
- **Voice Commands**: All DevAgent commands work via voice
- **Audio Feedback**: Natural speech synthesis with emotion

### Voice Usage
```bash
# Enable voice-only mode
python core/main.py --voice-only

# Check voice system status
python core/main.py --voice-status

# Test text-to-speech
python core/main.py --tts-test "Hello PersonaOS"
```

---

## 🔧 Troubleshooting

### Common Issues

**"Ollama not found"**
```bash
# Run the installer to auto-install Ollama
python install.py

# Or install manually: https://ollama.com/download
```

**"Port already in use"**
```bash
# Use the smart launcher (auto-detects free ports)
python start.py

# Or check system health
python start.py --health
```

**"Missing dependencies"**
```bash
# Reinstall everything
python install.py

# Or manually
pip install -r requirements.txt
```

**Web UI not loading**
```bash
# Check if Node.js is installed
node --version

# Install frontend dependencies
cd persona_web_ui/frontend
npm install
```

**DevAgent not working**
```bash
# Test DevAgent functionality
python test_dev_agent_simple.py

# Check system status
dev-system  # (within PersonaOS conversation)

# View recent tasks
dev-history
```

**Voice features not working**
```bash
# Check voice pipeline status
python core/main.py --voice-status

# Test voice components
python test_voice_pipeline.py

# Verify microphone/speaker setup
python core/main.py --tts-test "Hello world"
```

### Getting Help
- 🆘 System health check: `python start.py --health`
- 📖 Documentation: See `docs/` folder
- 🐛 Issues: [GitHub Issues](https://github.com/personaos/PersonaOS/issues)

---

## 🏗️ Architecture Overview

**PersonaOS** is built with modularity in mind:

- **Core** (`core/`) - Main application logic, LLM integration, memory
- **DevAgent** (`core/dev_agent/`) - Autonomous development system with natural language tasks
- **Voice Pipeline** (`core/voice/`, `core/sst/`, `core/tts/`) - Complete voice conversation system
- **Web UI** (`persona_web_ui/`) - FastAPI backend + React frontend  
- **Tools** (`core/tools/`) - Plugin system for extensibility
- **Configuration** - Environment-based config with encryption support

**Entry Points:**
- `install.py` - Automated installer and setup
- `start.py` - Universal launcher with interface selection
- `core/main.py` - Direct CLI access (developer mode)
- `start_webui.bat` - Quick Web UI launcher

---

## 🤝 Contributing

PersonaOS welcomes contributions! Whether you're:
- 🆕 New to AI: Try the system and report usability issues
- 👨‍💻 Developer: Contribute code, tools, or documentation  
- 🎨 Designer: Improve the Web UI and user experience
- 📝 Writer: Help with documentation and tutorials

See `CONTRIBUTING.md` for details.

---

**PersonaOS v0.1.0** is an early-stage prototype that demonstrates:
- 🤝 **Human-centric interaction** through natural language and voice
- 🤖 **Autonomous development** via DevAgent's AI-powered coding assistance  
- ⚙️ **Hardware-agnostic deployment** on standard x86 systems
- 🧠 **Intelligent conversation** with memory and context awareness
- 🎤 **Multimodal interaction** supporting text, voice, and web interfaces
- 🛡️ **Safe operation** with automatic backups, rollback, and validation
- 🧩 **Open and extensible** modular architecture for future capabilities

**Try DevAgent**: Start PersonaOS and type `dev: Create a simple calculator function` to see autonomous development in action!
