# 🔧 PersonaOS Troubleshooting Guide

This guide helps you solve common PersonaOS issues quickly and effectively.

## 🚨 Quick Diagnosis

**First, run the system health check:**
```bash
python start.py --health
```

This will automatically detect and often fix common issues.

---

## 📋 Common Issues & Solutions

### 🐍 Python Issues

#### "Python is not recognized as an internal or external command"
**Problem:** Python not installed or not in PATH  
**Solution:**
1. Install Python from https://python.org
2. During installation, check "Add Python to PATH"
3. Restart your terminal/command prompt

#### "No module named 'requests' (or other module)"
**Problem:** Missing Python dependencies  
**Solution:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt

# Or run the full installer
python install.py
```

#### "Permission denied" when installing packages
**Problem:** Need administrator rights  
**Solution:**
```bash
# Windows: Run terminal as Administrator
# Linux/macOS: Use sudo
sudo pip install -r requirements.txt
```

---

### 🤖 Ollama Issues

#### "Ollama not found" or "Ollama command not recognized"
**Problem:** Ollama not installed  
**Solution:**
```bash
# Automatic installation
python install.py

# Manual installation
# Windows: Download from https://ollama.com/download
# Linux/macOS: curl -fsSL https://ollama.com/install.sh | sh
```

#### "No models available" or "Model not found"
**Problem:** No AI models downloaded  
**Solution:**
```bash
# Download the default model
ollama pull openhermes

# List available models
ollama list

# Download other models
ollama pull llama2
ollama pull codellama
```

#### "Ollama service not responding"
**Problem:** Ollama service not running  
**Solution:**
```bash
# Windows: Restart Ollama from Start Menu
# Linux/macOS: 
systemctl restart ollama
# Or start manually:
ollama serve
```

#### "Model loading timeout"
**Problem:** Large model taking too long to load  
**Solution:**
- Wait longer (first load can take 2-5 minutes)
- Try a smaller model: `ollama pull openhermes:7b`
- Check available RAM (models need 4-16GB)

---

### 🌐 Web UI Issues

#### "Web UI not loading" or "Cannot connect to server"
**Problem:** Frontend or backend not starting  
**Solution:**
1. **Check Node.js installation:**
   ```bash
   node --version
   npm --version
   ```
   If not installed: Download from https://nodejs.org

2. **Install frontend dependencies:**
   ```bash
   cd persona_web_ui/frontend
   npm install
   ```

3. **Use the smart launcher:**
   ```bash
   python start.py --web
   ```

#### "Port already in use" errors
**Problem:** Configured ports are occupied  
**Solution:**
```bash
# Use auto port detection
python start.py

# Or check what's using ports
netstat -an | grep :8000
netstat -an | grep :5173

# Kill processes using ports (if safe)
# Windows: taskkill /F /PID <process_id>
# Linux/macOS: kill -9 <process_id>
```

#### "CORS error" or "Failed to fetch" in browser
**Problem:** Frontend can't connect to backend  
**Solution:**
1. **Check both services are running:**
   - Backend: http://localhost:8000/api/health
   - Frontend: http://localhost:5173

2. **Restart with the launcher:**
   ```bash
   python start.py --web
   ```

3. **Check CORS configuration:**
   - Backend automatically allows frontend ports
   - Make sure you're using the URLs shown by the launcher

#### "Module build failed" or Vite errors
**Problem:** Frontend build issues  
**Solution:**
```bash
cd persona_web_ui/frontend

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# If still failing, update Node.js
```

---

### ⚙️ Configuration Issues

#### "Configuration file (.env) missing"
**Problem:** No environment configuration  
**Solution:**
```bash
# Run setup wizard
python core/main.py

# Or use quick defaults
python install.py --defaults
```

#### "Invalid configuration" errors
**Problem:** Corrupted or invalid .env file  
**Solution:**
```bash
# Reset configuration
python core/main.py --reset-env

# Or restore from backup
cp .env.backup .env  # If backup exists
```

#### "API key not working"
**Problem:** Invalid or expired API keys  
**Solution:**
1. **Verify API key format:**
   - OpenAI: `sk-...` (51 characters)
   - Anthropic: Various formats
   
2. **Test API key:**
   ```bash
   # For OpenAI
   curl -H "Authorization: Bearer YOUR_API_KEY" https://api.openai.com/v1/models
   ```

3. **Reconfigure:**
   ```bash
   python core/main.py --reset-env
   ```

---

### 🚀 Performance Issues

#### "PersonaOS is very slow"
**Problem:** Performance bottlenecks  
**Solutions:**

1. **Check system resources:**
   - RAM: Need 8GB+ for larger models
   - CPU: More cores = faster processing
   - Storage: SSD recommended

2. **Try smaller models:**
   ```bash
   ollama pull openhermes:7b  # Instead of larger variants
   ```

3. **Optimize settings:**
   - Set `DEBUG_MODE=false` in .env
   - Use `LOG_LEVEL=WARNING` or `ERROR`

#### "First message takes forever"
**Problem:** Model loading delay  
**Solution:**
- This is normal for first message (1-5 minutes)
- Subsequent messages are much faster
- Keep PersonaOS running to avoid reloading
- Use Web UI to keep models in memory longer

#### "Running out of memory"
**Problem:** System RAM exhausted  
**Solutions:**
1. **Use smaller models:**
   ```bash
   ollama pull openhermes:7b  # ~4GB RAM
   # Instead of larger 13B or 70B models
   ```

2. **Close other applications**

3. **Increase virtual memory/swap**

---

### 🔒 Security & Privacy Issues

#### "Certificate/SSL errors"
**Problem:** HTTPS/security warnings  
**Solution:**
- PersonaOS uses HTTP locally (safe for local use)
- If you need HTTPS, configure reverse proxy
- For local use, you can safely ignore browser warnings

#### "Firewall blocking connections"
**Problem:** Security software blocking PersonaOS  
**Solution:**
1. **Allow Python through firewall**
2. **Allow connections to localhost ports 8000, 5173**
3. **Whitelist PersonaOS directory in antivirus**

---

### 💾 Data & Storage Issues

#### "Conversation history lost"
**Problem:** Memory/conversations disappeared  
**Solution:**
1. **Check memory settings in .env:**
   ```
   MEMORY_ENABLED=true
   MEMORY_DIR=data/memory
   ```

2. **Check if memory files exist:**
   ```bash
   ls data/memory/
   ```

3. **Restore if possible:**
   - Look for `.backup` files
   - Check `onboarding_summary.txt`

#### "Disk space running low"
**Problem:** PersonaOS using too much storage  
**Solution:**
1. **Clean up old models:**
   ```bash
   ollama list
   ollama rm <unused_model_name>
   ```

2. **Clear logs (if debug mode was on):**
   ```bash
   rm *.log
   ```

3. **Clean memory (careful!):**
   ```bash
   # Backup first
   cp -r data/memory data/memory.backup
   # Then selectively delete old conversations
   ```

---

## 🛠️ Advanced Troubleshooting

### Debug Mode
Enable detailed logging:
```bash
# In .env file:
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# Or temporary:
python start.py --verbose
```

### Health Check with Details
```bash
python system_health.py --verbose
```

### Manual Component Testing

**Test Python Environment:**
```python
import sys
print(f"Python: {sys.version}")
import requests, yaml, dotenv, cryptography
print("All dependencies OK")
```

**Test Ollama Connection:**
```bash
ollama --version
ollama list
ollama run openhermes "Hello, test message"
```

**Test Web Components:**
```bash
# Test backend
cd persona_web_ui/backend
python main.py &
curl http://localhost:8000/api/health

# Test frontend
cd persona_web_ui/frontend
npm run dev
```

### Log Analysis

**Find logs:**
- Terminal output (most issues visible here)
- `.env` file for configuration
- `onboarding_summary.txt` for setup info

**Common error patterns:**
- `ModuleNotFoundError`: Missing Python package
- `Connection refused`: Service not running
- `Port already in use`: Port conflict
- `Permission denied`: Need admin rights
- `Timeout`: Service taking too long

---

## 🔄 Reset & Recovery

### Complete Reset
```bash
# Backup important data first
cp .env .env.backup
cp -r data data.backup

# Reset everything
rm .env
python install.py

# Or just reset config
python core/main.py --reset-env
```

### Recovery Steps
1. **Backup current state**
2. **Run system health check**
3. **Try automatic repair**
4. **Manual intervention if needed**
5. **Full reinstall as last resort**

---

## 📞 Getting Help

### Self-Service Tools
```bash
python start.py --health          # System diagnostics
python system_health.py --verbose  # Detailed health check
python start.py --help            # Usage help
```

### Community Support

**🐛 Bug Reports:**
- GitHub Issues: https://github.com/personaos/PersonaOS/issues
- Include: Error messages, system info, steps to reproduce

**💬 Discussions:**
- GitHub Discussions for general help
- Include: What you're trying to do, what happened instead

**📝 Information to Include:**
- Operating system (Windows 10, Ubuntu 20.04, etc.)
- Python version (`python --version`)
- PersonaOS version
- Error messages (copy exact text)
- Steps that led to the problem

### Useful System Information
```bash
# Get system info for bug reports
python --version
ollama --version
node --version  # If using Web UI
python system_health.py --json  # Detailed system state
```

---

**Remember: Most issues are resolved quickly with the system health check! 🚀**

```bash
python start.py --health
```