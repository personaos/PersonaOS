# PersonaOS Web UI

A full-stack web interface for PersonaOS, the local-first AI assistant. This application provides a clean, responsive web interface for interacting with PersonaOS through a FastAPI backend and React frontend.

## 🏗️ Architecture

```
persona_web_ui/
├── backend/           # FastAPI server
│   ├── main.py       # API endpoints and PersonaOS integration
│   └── requirements.txt
└── frontend/         # React application
    ├── src/
    │   ├── App.jsx   # Main application component
    │   ├── main.jsx  # React entry point
    │   └── index.css # Styling
    ├── package.json
    ├── vite.config.js
    └── index.html
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ 
- Node.js 18+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd persona_web_ui/backend
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```

   The API will be available at: http://localhost:8000
   
   **API Documentation:** http://localhost:8000/docs

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd persona_web_ui/frontend
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

   The web interface will be available at: http://localhost:3000

## 🔧 API Endpoints

### Core Endpoints

- **`POST /api/message`** - Send message to PersonaOS
  ```json
  {
    "message": "What time is it?",
    "context": null
  }
  ```

- **`GET /api/health`** - Health check and system status
- **`GET /api/tools`** - List available PersonaOS tools
- **`GET /`** - Basic API status

### Setup & Configuration Endpoints

- **`GET /api/setup/defaults`** - Get configuration sections and current values
- **`POST /api/setup/submit`** - Submit configuration and save to .env

### Response Format

```json
{
  "reply": "It's 3:45 PM on Friday, July 26, 2025.",
  "intent": "inform_time",
  "tools_used": ["clock"],
  "confidence": 0.95,
  "processing_time_ms": 150
}
```

## 🎯 Features

### Current Features

- **🛠️ Interactive Onboarding:** Web-based setup wizard to configure PersonaOS environment
- **⚙️ Configuration Management:** Easy setup and reconfiguration of PersonaOS settings
- **🔒 Security:** API key masking and secure server-side .env management
- **Message Input:** Clean text input with send button
- **Response Display:** Formatted response cards with metadata
- **Intent Detection:** Shows detected user intent
- **Tool Tracking:** Displays which PersonaOS tools were used
- **Error Handling:** User-friendly error messages
- **Loading States:** Visual feedback during processing
- **Responsive Design:** Works on desktop and mobile

### Placeholder Features (Ready for Integration)

- **PersonaOS Core Integration:** Structured for easy plugin with actual PersonaOS
- **Tool Registry:** Backend ready to list and execute PersonaOS tools
- **Safety Validation:** Framework for intent-based safety checks
- **Configuration API:** Endpoints ready for PersonaOS settings

## 🔌 PersonaOS Integration Points

### Backend Integration (`main.py`)

```python
# TODO: Replace PersonaCore placeholder with actual PersonaOS imports
from core.llm.llm_handler import LLMManager
from core.tools.clock import ClockTool
from core.llm.prompt_engine import PromptEngineTool

class PersonaCore:
    def __init__(self):
        self.llm_manager = LLMManager()
        self.tools = {
            'clock': ClockTool(),
            'prompt_engine': PromptEngineTool()
        }
    
    def respond(self, message: str, context: dict = None) -> dict:
        # Integrate with actual PersonaOS processing pipeline
        pass
```

### Frontend Integration (`App.jsx`)

```javascript
// TODO: Add conversation context tracking
const [conversationHistory, setConversationHistory] = useState([])

// TODO: Add real-time WebSocket connection for streaming responses
// TODO: Add voice input/output integration
// TODO: Add tool execution visualization
```

## 🛠️ Development

### Backend Development

- **Framework:** FastAPI with Pydantic models
- **CORS:** Configured for React dev server
- **Logging:** Structured logging with PersonaOS integration points
- **Validation:** Request/response validation with clear error messages

### Frontend Development

- **Framework:** React 18 with Hooks
- **Build Tool:** Vite for fast development
- **Styling:** Custom CSS with responsive design
- **State Management:** React hooks (expandable to Redux if needed)

### Development Commands

```bash
# Backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend  
cd frontend
npm run dev          # Development server
npm run build        # Production build
npm run preview      # Preview production build
```

## 🎨 Customization

### Styling

The interface uses a modern, clean design with:
- **Colors:** Purple gradient theme matching PersonaOS branding
- **Typography:** System font stack for optimal readability
- **Layout:** Responsive grid system
- **Components:** Modular CSS classes for easy customization

### Configuration

- **API Base URL:** Configurable in `App.jsx`
- **Server Ports:** Backend (8000), Frontend (3000)
- **CORS Origins:** Configured for development servers

## 🔮 Future Enhancements

### Planned Features

1. **Real-time Communication:** WebSocket support for streaming responses
2. **Voice Interface:** Speech-to-text and text-to-speech integration
3. **Conversation History:** Persistent chat history with search
4. **Settings Panel:** PersonaOS configuration through web UI
5. **Plugin Management:** Dynamic tool discovery and management
6. **Authentication:** User authentication if multi-user support needed
7. **Mobile App:** React Native companion app
8. **Theme System:** Dark/light mode with custom themes

### Integration Roadmap

1. **Phase 1:** Connect to actual PersonaOS core (current placeholder)
2. **Phase 2:** Integrate tool system and plugin architecture  
3. **Phase 3:** Add voice capabilities and real-time features
4. **Phase 4:** Advanced features and mobile support

## 📝 Notes

- **Local-First:** Designed to work entirely offline with local PersonaOS
- **Privacy-Focused:** No external API calls or data collection
- **Modular:** Easy to extend with additional PersonaOS features
- **Developer-Friendly:** Clear separation of concerns and integration points

## 🤝 Contributing

This web UI is designed as a modular scaffold for PersonaOS. Key integration points are marked with `TODO` comments for easy identification of where actual PersonaOS functionality should be plugged in.

---

**PersonaOS Web UI v0.1.0** | Local-first AI Assistant Interface