# 🚀 PersonaOS Quick Start Guide

Welcome to PersonaOS! This guide will get you up and running in just a few minutes.

## ⚡ Super Quick Start (3 Steps)

### 1. Download PersonaOS
```bash
git clone https://github.com/personaos/PersonaOS.git
cd PersonaOS
```

### 2. Run the Installer
```bash
python install.py
```
*This automatically installs everything you need!*

### 3. Start PersonaOS
```bash
python start.py
```
*Choose your preferred interface and start chatting!*

---

## 🎯 What You Get

After setup, PersonaOS provides:

### 🖥️ **CLI Mode** 
- Terminal-based chat interface
- Perfect for developers and power users
- Works entirely offline with Ollama

### 🌐 **Web UI Mode**
- Browser-based interface with modern design
- Real-time conversation management
- Message search, threading, and favorites
- Visual model management

### 🤖 **Local AI**
- Powered by Ollama (runs on your computer)
- Complete privacy - no data sent to cloud
- Multiple AI models to choose from

---

## 🛠️ First-Time Setup

### Prerequisites Check
PersonaOS installer handles most of this automatically, but here's what you need:

✅ **Python 3.7+** (required)  
✅ **Internet connection** (for initial setup)  
🔧 **Ollama** (auto-installed)  
🔧 **Node.js** (optional, for Web UI)  

### Installation Options

**🏃‍♂️ Automatic (Recommended)**
```bash
python install.py
```

**🔧 Manual (Advanced Users)**
```bash
# Install dependencies
pip install -r requirements.txt

# Install Ollama
# Windows: Download from https://ollama.com
# Linux/macOS: curl -fsSL https://ollama.com/install.sh | sh

# Configure PersonaOS
python core/main.py  # Triggers setup wizard
```

---

## 🎮 Using PersonaOS

### Starting PersonaOS

**Universal Launcher (Recommended)**
```bash
python start.py
```
*Interactive menu lets you choose CLI or Web UI*

**Direct CLI Access**
```bash
python core/main.py
```

**Web UI Only**
```bash
python start.py --web
```

### Your First Conversation

1. **Start PersonaOS** using any method above
2. **Wait for the prompt** (may take a moment to load AI model)
3. **Type your message** and press Enter
4. **Chat naturally** - PersonaOS understands context!

**Example conversation:**
```
You: Hello! What can you help me with?
PersonaOS: Hello! I'm PersonaOS, your local AI assistant. I can help with...

You: Tell me about the weather
PersonaOS: I don't have access to current weather data, but I can help you...

You: exit
PersonaOS: Goodbye! 👋
```

---

## ⚙️ Basic Configuration

### Quick Setup
Most users can use the defaults. The installer creates a working configuration automatically.

### Custom Configuration
If you need to change settings:

```bash
python core/main.py --reset-env
```

**Key Settings:**
- **LLM Provider**: ollama (local) vs cloud services
- **AI Model**: openhermes (good general model)
- **Web UI Ports**: Backend (8000) and Frontend (5173)
- **Safety Level**: standard (recommended)

### Adding AI Models

```bash
# List available models
ollama list

# Download a new model
ollama pull llama2

# PersonaOS will detect new models automatically
```

---

## 🌐 Web UI Guide

### Accessing Web UI
1. Start with `python start.py` and choose Web UI
2. Open your browser to the displayed URL
3. Default: http://localhost:5173

### Web UI Features

**💬 Chat Interface**
- Type messages in the bottom input box
- View conversation history in the main panel
- Switch between different conversations

**🔍 Search & Organization**
- Search messages with the search bar
- Create conversation threads for branching topics
- Star important messages as favorites

**🤖 Model Management**
- View available AI models
- Switch between models
- Download new models
- Configure model settings

**⚙️ Settings**
- Adjust system configuration
- Manage API keys
- View system health

---

## 🆘 Common Issues

### "Ollama not found"
```bash
# Run the installer to auto-install
python install.py

# Or install manually
# Windows: Download from https://ollama.com
# Linux: curl -fsSL https://ollama.com/install.sh | sh
```

### "Port already in use"
```bash
# Use the smart launcher (finds free ports automatically)
python start.py

# Or check what's using your ports
python start.py --health
```

### "Web UI not loading"
```bash
# Check if Node.js is installed
node --version

# Install Node.js from https://nodejs.org
# Then install frontend dependencies
cd persona_web_ui/frontend
npm install
```

### "No AI model found"
```bash
# Download the default model
ollama pull openhermes

# Or choose a different model
ollama pull llama2
```

---

## 💡 Tips & Tricks

### 🚀 **Performance Tips**
- First message may be slow (model loading)
- Subsequent messages are much faster
- Web UI keeps models loaded longer

### 🔒 **Privacy Tips**
- Ollama keeps everything local
- No internet required after setup
- You own all your conversation data

### 🛠️ **Developer Tips**
- Use `python start.py --health` for diagnostics
- Check logs in the terminal
- All configuration is in `.env` file

### ⚡ **Shortcuts**
- Create desktop shortcuts: `python create_shortcuts.py`
- Add to PATH for global access
- Use `python start.py --cli` or `--web` to skip menu

---

## 📚 Next Steps

**🎓 Learn More**
- Read the full documentation in `CLAUDE.md`
- Explore the `docs/` folder for detailed guides
- Check out the `PersonaOS_Spec.md` for technical details

**🔧 Customize**
- Try different AI models with `ollama pull`
- Configure advanced settings in the setup wizard
- Add API keys for cloud AI services (optional)

**🤝 Get Involved**
- Report issues on GitHub
- Contribute to the project
- Share your PersonaOS setup

---

## 🆘 Getting Help

**System Diagnostics**
```bash
python start.py --health
```

**Reconfigure Everything**
```bash
python core/main.py --reset-env
```

**Community Support**
- GitHub Issues: [Report bugs and get help](https://github.com/personaos/PersonaOS/issues)
- Documentation: Check the `docs/` folder
- Troubleshooting: See `docs/troubleshooting.md`

---

**Happy chatting with PersonaOS! 🤖✨**