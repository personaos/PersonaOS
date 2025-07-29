# PersonaOS Brownfield Enhancement Rollback Procedures

## Emergency Contact Information
- **Emergency Stop Command**: `CTRL+C` (CLI) or Emergency Voice Command: "PersonaOS Emergency Stop"
- **Safe Mode Startup**: `python core/main.py --safe-mode`
- **Full System Reset**: `python core/main.py --reset-env --disable-all`

---

# Table of Contents
1. [Emergency Response Overview](#emergency-response-overview)
2. [Epic-Level Rollback Procedures](#epic-level-rollback-procedures)
3. [Story-Level Rollback Procedures](#story-level-rollback-procedures)
4. [System Recovery Procedures](#system-recovery-procedures)
5. [Data Protection and Backup](#data-protection-and-backup)
6. [Emergency Contacts and Escalation](#emergency-contacts-and-escalation)

---

# Emergency Response Overview

## Rollback Trigger Conditions
Execute rollback procedures when:
- **System Instability**: PersonaOS becomes unresponsive or crashes repeatedly
- **Security Breach**: Plugin security violation or unauthorized system access
- **Performance Degradation**: >50% performance drop from baseline
- **Data Corruption**: Memory system or configuration corruption detected
- **User Safety**: Voice commands execute unintended or dangerous actions

## Rollback Severity Levels

### 🔴 LEVEL 1: EMERGENCY SHUTDOWN
**Triggers**: Security breach, dangerous command execution, system corruption
**Action**: Immediate system shutdown and isolation
**Response Time**: <30 seconds

### 🟡 LEVEL 2: FEATURE DISABLE
**Triggers**: Single feature malfunction, performance issues, minor instability
**Action**: Disable affected feature while maintaining core functionality
**Response Time**: <2 minutes

### 🟢 LEVEL 3: CONFIGURATION RESET
**Triggers**: Configuration conflicts, minor bugs, user preference issues
**Action**: Reset specific configurations to known good state
**Response Time**: <5 minutes

---

# Epic-Level Rollback Procedures

## Epic 1: Voice Pipeline Rollback

### Quick Disable (Level 2)
```bash
# Disable voice features immediately
export VOICE_ENABLED=false
export STT_ENABLED=false
export TTS_ENABLED=false
python core/main.py --no-voice
```

### Full Voice Pipeline Rollback (Level 1)
```bash
# 1. Emergency stop all voice processes
pkill -f "whisper"
pkill -f "tts"
pkill -f "voice_pipeline"

# 2. Disable voice in configuration
sed -i 's/VOICE_ENABLED=true/VOICE_ENABLED=false/' .env
sed -i 's/STT_ENABLED=true/STT_ENABLED=false/' .env
sed -i 's/TTS_ENABLED=true/TTS_ENABLED=false/' .env

# 3. Restart in CLI-only mode
python core/main.py --cli-only --no-voice

# 4. Verify system stability
python -c "from core.main import main; print('System stable')"
```

### Voice Pipeline Component Rollback
```bash
# Rollback individual voice components
# STT Issues
export STT_ENABLED=false
python core/main.py --no-stt

# TTS Issues  
export TTS_ENABLED=false
python core/main.py --no-tts

# Voice Controller Issues
export VOICE_CONTROLLER_ENABLED=false
python core/main.py --basic-voice
```

---

## Epic 2: Plugin Framework Rollback

### Quick Plugin Disable (Level 2)
```bash
# Disable all plugins immediately
export PLUGINS_ENABLED=false
export ALLOW_TOOL_EXECUTION=false
python core/main.py --no-plugins
```

### Emergency Plugin Shutdown (Level 1)
```bash
# 1. Emergency terminate all plugin processes
pkill -f "plugin_"
pkill -f "sandbox_"

# 2. Disable plugin system
sed -i 's/PLUGINS_ENABLED=true/PLUGINS_ENABLED=false/' .env
sed -i 's/ALLOW_TOOL_EXECUTION=true/ALLOW_TOOL_EXECUTION=false/' .env

# 3. Clear plugin cache and temporary files
rm -rf core/plugins/__pycache__/
rm -rf /tmp/persona_plugins/
rm -rf plugins/temp/

# 4. Restart with basic tool system only
python core/main.py --basic-tools-only

# 5. Verify core tool functionality
python -c "from core.tools.basic_tools import *; print('Basic tools functional')"
```

### Individual Plugin Rollback
```bash
# Disable specific problematic plugin
echo "PLUGIN_BLACKLIST=problematic_plugin_name" >> .env

# Remove plugin from registry
python -c "
from core.plugins.plugin_registry import PluginRegistry
registry = PluginRegistry()
registry.unregister_plugin('problematic_plugin_name')
"

# Clear plugin data
rm -rf plugins/problematic_plugin_name/
```

### Plugin Security Breach Response
```bash
# 1. Immediate containment
export PLUGIN_SECURITY_LEVEL=maximum
export PLUGIN_SANDBOX_STRICT=true

# 2. Quarantine all plugins
mkdir -p quarantine/
mv plugins/* quarantine/

# 3. Enable only essential plugins
mkdir -p plugins/essential/
# (manually move only verified safe plugins back)

# 4. Reset security settings
cp config/plugin_security_default.yaml config/plugin_security.yaml
```

---

## Epic 3: Web UI Voice Integration Rollback

### Quick Web Voice Disable (Level 2)
```bash
# Disable web voice features
export WEB_VOICE_ENABLED=false
export BROWSER_VOICE_API_ENABLED=false

# Restart web UI without voice
cd persona_web_ui/backend && python main.py --no-voice
```

### Full Web Voice Rollback (Level 1)
```bash
# 1. Stop web UI services
pkill -f "persona_web_ui"
pkill -f "vite"

# 2. Disable web voice in configuration
sed -i 's/WEB_VOICE_ENABLED=true/WEB_VOICE_ENABLED=false/' .env
sed -i 's/BROWSER_VOICE_API_ENABLED=true/BROWSER_VOICE_API_ENABLED=false/' .env

# 3. Start basic web UI (text-only)
cd persona_web_ui/backend
python main.py --basic-ui --no-voice

# 4. Start frontend in fallback mode
cd ../frontend
npm run dev:no-voice
```

### Browser Compatibility Fallback
```bash
# Force server-side voice processing
export FORCE_SERVER_VOICE=true
export DISABLE_BROWSER_APIS=true

# Disable problematic browser features
export DISABLE_WEB_SPEECH_API=true
export DISABLE_SPEECH_SYNTHESIS=true
```

---

# Story-Level Rollback Procedures

## Voice Pipeline Stories

### Story 1.1: STT Integration Rollback
```bash
# Disable STT and fallback to text input
export STT_ENABLED=false
export WHISPER_ENABLED=false

# Remove STT dependencies if causing issues
pip uninstall whisper-cpp-python -y

# Restart without STT
python core/main.py --no-stt
```

### Story 1.2: Audio Pipeline Controller Rollback
```bash
# Disable audio pipeline controller
export AUDIO_PIPELINE_ENABLED=false

# Use direct voice processing
export DIRECT_VOICE_MODE=true

# Clear audio pipeline cache
rm -rf core/voice/pipeline_cache/
```

### Story 1.3: TTS Integration Rollback
```bash
# Disable TTS and use text-only responses
export TTS_ENABLED=false
export MIMIC3_ENABLED=false
export COQUI_ENABLED=false

# Clear TTS cache
rm -rf core/tts/cache/
```

### Story 1.4: Voice Tool Execution Rollback
```bash
# Disable voice tool execution
export VOICE_TOOL_EXECUTION=false

# Allow only text-based tool execution
export TOOLS_VOICE_DISABLED=true

# Clear voice tool cache
rm -rf core/tools/voice_cache/
```

## Plugin Framework Stories

### Story 2.1: Plugin Loader Rollback
```bash
# Disable dynamic loading
export DYNAMIC_PLUGIN_LOADING=false

# Use static plugin loading only
export STATIC_PLUGINS_ONLY=true

# Clear plugin loader cache
rm -rf core/plugins/loader_cache/
```

### Story 2.2: Plugin Security Rollback
```bash
# Disable sandboxing (not recommended, use with caution)
export PLUGIN_SANDBOX_ENABLED=false

# Use minimal permission model
export PLUGIN_PERMISSIONS=minimal

# Reset security policies
cp config/plugin_security_minimal.yaml config/plugin_security.yaml
```

### Story 2.3: External Integration Rollback
```bash
# Disable external integrations
export EXTERNAL_INTEGRATIONS_ENABLED=false

# Disable specific integration types
export DISABLE_OAUTH=true
export DISABLE_API_INTEGRATIONS=true
export DISABLE_FILE_INTEGRATIONS=true

# Clear integration cache
rm -rf core/plugins/integrations/cache/
```

### Story 2.4: Performance Monitoring Rollback
```bash
# Disable performance monitoring
export PLUGIN_MONITORING_ENABLED=false

# Reduce monitoring overhead
export MONITORING_LEVEL=minimal

# Clear monitoring data
rm -rf core/plugins/monitoring/data/
```

## Web UI Integration Stories

### Story 3.1: Web Voice Interface Rollback
```bash
# Disable web voice interface
export WEB_VOICE_INTERFACE_ENABLED=false

# Use polling instead of WebSocket
export USE_WEBSOCKET_VOICE=false

# Clear web voice cache
rm -rf persona_web_ui/backend/voice_cache/
```

### Story 3.2: Visual Voice Flow Rollback
```bash
# Disable voice visualizations
export VOICE_VISUALIZATIONS_ENABLED=false

# Use minimal voice UI
export VOICE_UI_MINIMAL=true

# Clear visualization cache
rm -rf persona_web_ui/frontend/src/components/voice/cache/
```

### Story 3.3: Multi-Modal Interactions Rollback
```bash
# Disable multi-modal features
export MULTIMODAL_INTERACTIONS=false

# Use single input mode
export SINGLE_INPUT_MODE=true

# Clear multi-modal state
rm -rf persona_web_ui/frontend/src/utils/multimodal/cache/
```

### Story 3.4: Voice Customization Rollback
```bash
# Reset to default voice settings
export VOICE_CUSTOMIZATION_ENABLED=false

# Clear user customizations
rm -rf persona_web_ui/frontend/src/data/voice_customizations/

# Reset to default voice profile
cp config/voice_defaults.json config/voice_settings.json
```

---

# System Recovery Procedures

## Full System Recovery (Nuclear Option)

### Complete Rollback to PersonaOS v0.1.0 Baseline
```bash
# 1. Stop all processes
pkill -f "persona"
pkill -f "python.*core"

# 2. Backup current state
mkdir -p rollback_backup/$(date +%Y%m%d_%H%M%S)
cp -r . rollback_backup/$(date +%Y%m%d_%H%M%S)/

# 3. Reset to baseline configuration
cp .env.baseline .env
cp config/baseline_config.yaml config/config.yaml

# 4. Disable all enhancements
export VOICE_ENABLED=false
export PLUGINS_ENABLED=false  
export WEB_VOICE_ENABLED=false
export ENHANCED_FEATURES=false

# 5. Clean temporary files
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
rm -rf logs/enhancement_*
rm -rf temp/*

# 6. Restart in baseline mode
python core/main.py --baseline --safe-mode

# 7. Verify baseline functionality
python -c "
from core.main import main
from core.llm.llm_handler import LLMManager
print('Baseline system functional')
"
```

## Partial Recovery Procedures

### Configuration Recovery
```bash
# Reset configuration to last known good state
cp config/config_backup.yaml config/config.yaml
cp .env.backup .env

# Verify configuration
python core/config.py --validate
```

### Memory System Recovery
```bash
# Backup current memory
cp -r core/llm/memory/ core/llm/memory_backup_$(date +%Y%m%d)/

# Reset memory system
rm -rf core/llm/memory/corrupted/
python -c "
from core.llm.memory import Memory
memory = Memory()
memory.reset_to_safe_state()
"
```

### Dependency Recovery
```bash
# Reinstall dependencies from known good versions
pip freeze > current_requirements.txt
pip install -r requirements_baseline.txt --force-reinstall

# Verify critical dependencies
python -c "
import ollama
import requests
import fastapi
print('Critical dependencies functional')
"
```

---

# Data Protection and Backup

## Pre-Enhancement Backup Procedure
```bash
# Create comprehensive backup before any enhancement
BACKUP_DIR="backup/pre_enhancement_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup configuration
cp .env $BACKUP_DIR/
cp -r config/ $BACKUP_DIR/config/

# Backup memory and conversations
cp -r core/llm/memory/ $BACKUP_DIR/memory/
cp -r logs/ $BACKUP_DIR/logs/

# Backup custom configurations
cp -r plugins/ $BACKUP_DIR/plugins/ 2>/dev/null || true

# Create restoration script
cat > $BACKUP_DIR/restore.sh << 'EOL'
#!/bin/bash
echo "Restoring PersonaOS to pre-enhancement state..."
cp .env ../.env
cp -r config/ ../config/
cp -r memory/ ../core/llm/memory/
echo "Restoration complete. Restart PersonaOS."
EOL
chmod +x $BACKUP_DIR/restore.sh
```

## Automated Backup Verification
```bash
# Verify backup integrity
BACKUP_DIR=$1
if [ -f "$BACKUP_DIR/.env" ] && [ -d "$BACKUP_DIR/config" ]; then
    echo "✅ Backup verified: $BACKUP_DIR"
else
    echo "❌ Backup corrupted: $BACKUP_DIR"
    exit 1
fi
```

---

# Emergency Contacts and Escalation

## Escalation Matrix

### Level 1: User Self-Service (0-15 minutes)
- **Actions**: Follow quick disable procedures
- **Tools**: This rollback document, safe mode startup
- **Success Criteria**: System returns to stable state

### Level 2: Technical Support (15-60 minutes)  
- **Actions**: Execute story-level rollbacks, analyze logs
- **Tools**: Advanced diagnostics, configuration recovery
- **Success Criteria**: Specific functionality restored

### Level 3: Engineering Escalation (1-4 hours)
- **Actions**: Full system recovery, code-level investigation
- **Tools**: Debug tools, system analysis, backup restoration
- **Success Criteria**: Root cause identified and resolved

### Level 4: Emergency Response (Immediate)
- **Actions**: Complete system shutdown, security containment
- **Tools**: Emergency procedures, security protocols
- **Success Criteria**: System secured, damage minimized

## Rollback Success Verification

### Verification Checklist
After any rollback procedure, verify:

- [ ] **Core CLI functionality** - `python core/main.py` starts successfully
- [ ] **LLM communication** - Can complete basic conversation
- [ ] **Configuration integrity** - All settings load without errors
- [ ] **Memory system** - Conversation history accessible
- [ ] **Web UI functionality** - Backend and frontend start without errors
- [ ] **Log system** - No critical errors in recent logs
- [ ] **Performance baseline** - Response times within normal range

### Verification Commands
```bash
# Quick system health check
python -c "
try:
    from core.main import main
    from core.llm.llm_handler import LLMManager
    from core.config import Config
    print('✅ Core systems functional')
except Exception as e:
    print(f'❌ System issue: {e}')
"

# Extended verification
python core/main.py --health-check --verbose
```

---

## Important Notes

- **Always backup before rollback** - Never lose user data or customizations
- **Document rollback reasons** - Log why rollback was necessary for future prevention
- **Test after rollback** - Verify system stability before considering rollback complete
- **Monitor post-rollback** - Watch for recurring issues that might indicate incomplete rollback

**This document should be immediately accessible during any PersonaOS emergency situation. Keep a printed copy available for scenarios where the system is completely inaccessible.**