# 🤖 PersonaOS v0.1.0

**PersonaOS** is an open, modular AI personality operating system designed to bring humanoid robots and embodied agents to life.

It connects language models, speech, and vision into a unified pipeline that enables machines to talk, think, and eventually feel — starting with basic x86 hardware (like Intel NUCs or Mini PCs).

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
- 🧠 Local LLM via [Ollama](https://ollama.com) (CLI or API)
- 🧠 Memory system for contextual dialogue
- 🎯 Intent processing and safety validation

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
```

### Configuration
```bash
# Quick setup with defaults
python install.py --defaults

# Manual configuration
python setup_env.py

# Reset everything
python core/main.py --reset-env
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

### Getting Help
- 🆘 System health check: `python start.py --health`
- 📖 Documentation: See `docs/` folder
- 🐛 Issues: [GitHub Issues](https://github.com/personaos/PersonaOS/issues)

---

## 🏗️ Architecture Overview

**PersonaOS** is built with modularity in mind:

- **Core** (`core/`) - Main application logic, LLM integration, memory
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

This is the early-stage prototype of a system that aims to be:
- 🤝 Human-centric  
- ⚙️ Hardware-agnostic  
- 🧠 Emotion-aware  
- 🧩 Open and extensible
