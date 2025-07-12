# 🤖 PersonaOS

**PersonaOS** is an open, modular AI personality operating system designed to bring humanoid robots and embodied agents to life.

It connects language models, speech, and vision into a unified pipeline that enables machines to talk, think, and eventually feel — starting with basic x86 hardware (like Intel NUCs or Mini PCs).

This is the early-stage prototype of a system that aims to be:
- 🤝 Human-centric
- ⚙️ Hardware-agnostic
- 🧠 Emotion-aware
- 🧩 Open and extensible

---

## ✨ Key Features (MVP v0.1)

✅ Voice Loop (WIP):
- 🎤 Speech-to-text using [Whisper](https://github.com/openai/whisper)
- 🧠 AI responses via GPT-4 / local LLMs (Ollama, Mistral, etc)
- 🔊 Text-to-speech via Coqui TTS / pyttsx3

🧱 Modular Codebase:
- Built in Python with Docker-based services
- Structured for STT / LLM / TTS and future vision, memory, persona modules

💻 Hardware-Ready:
- x86-compatible (Intel NUC, Beelink, Minisforum)
- Webcam + mic + speaker = enough to prototype

---

## 🧪 MVP Roadmap (Q3 2025)

- [x] Week 1: Core voice loop working locally
- [ ] Week 2: Add facial detection / emotion API input
- [ ] Week 3–4: Add memory + persistent persona module
- [ ] Week 5+: Connect to servo SDK (e.g. for eyes, mouth, head tracking)

---

## 🚀 Getting Started

Clone the repo:
```bash
git clone https://github.com/your-username/personaOS.git
cd personaOS
