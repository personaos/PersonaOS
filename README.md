# 🤖 PersonaOS v0.1.0

**PersonaOS** is an open, modular AI personality operating system designed to bring humanoid robots and embodied agents to life.

It connects language models, speech, and vision into a unified pipeline that enables machines to talk, think, and eventually feel — starting with basic x86 hardware (like Intel NUCs or Mini PCs).

This is the early-stage prototype of a system that aims to be:
- 🤝 Human-centric  
- ⚙️ Hardware-agnostic  
- 🧠 Emotion-aware  
- 🧩 Open and extensible  

---

## ✨ Key Features (MVP v0.1.0)

✅ CLI Interaction:
- 🧠 Local LLM via [Ollama](https://ollama.com) (CLI or API)
- 🧠 Memory stub for contextual dialogue (future support)

✅ Onboarding & Config:
- 🔐 Environment setup wizard (.env) for secure config
- ⚙️ Reset option via `--reset-env` flag
- 📁 Clean config and memory handling

🧱 Modular Codebase:
- 💡 Designed to support STT / LLM / TTS / wake word / vision modules
- 🔌 Easily extendable for future features

💻 Hardware-Ready:
- 🖥️ Runs on Intel NUC / Mini PCs
- 🎙️ Just needs a webcam, mic, and speakers to begin

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/personaos/PersonaOS.git
cd PersonaOS
