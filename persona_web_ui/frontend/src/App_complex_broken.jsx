import React, { useState, useEffect, useRef, useCallback } from 'react'
import OnboardingWizard from './components/OnboardingWizard'

function App() {
  const [message, setMessage] = useState('')
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [isConfigured, setIsConfigured] = useState(false)
  const [activeTab, setActiveTab] = useState('chat')
  const [conversations, setConversations] = useState([
    {
      id: 1,
      name: 'Welcome Chat',
      preview: 'Getting started with PersonaOS...',
      active: true
    },
    {
      id: 2,
      name: 'Code Review Session',
      preview: 'Help me review this Python function...',
      active: false
    },
    {
      id: 3,
      name: 'Project Planning',
      preview: "Let's plan the PersonaOS roadmap...",
      active: false
    }
  ])
  const [conversationCounter, setConversationCounter] = useState(4)

  // Panel management state
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('personaos-sidebar-width')
    return saved ? parseInt(saved) : 320
  })
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarMinimized, setSidebarMinimized] = useState(false)
  const [currentLayout, setCurrentLayout] = useState(() => {
    return localStorage.getItem('personaos-layout') || 'default'
  })

  const API_BASE_URL = 'http://localhost:8000'
  const dragRef = useRef(null)
  const isDragging = useRef(false)

  useEffect(() => {
    checkSetupStatus()
    loadTheme()
  }, [])

  const loadTheme = () => {
    const savedTheme = localStorage.getItem('theme') || 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
  }

  // Panel resize functionality
  const startResize = useCallback((e) => {
    isDragging.current = true
    const startX = e.clientX
    const startWidth = sidebarWidth

    const handleMouseMove = (e) => {
      if (!isDragging.current) return
      
      const newWidth = startWidth + (e.clientX - startX)
      const minWidth = 250
      const maxWidth = Math.min(800, window.innerWidth * 0.6)
      
      const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth))
      setSidebarWidth(constrainedWidth)
    }

    const handleMouseUp = () => {
      isDragging.current = false
      localStorage.setItem('personaos-sidebar-width', sidebarWidth.toString())
      
      if (dragRef.current) {
        dragRef.current.classList.remove('dragging')
      }
      
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    if (dragRef.current) {
      dragRef.current.classList.add('dragging')
    }
    
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [sidebarWidth])

  // Layout presets
  const applyLayout = (layoutName) => {
    setCurrentLayout(layoutName)
    localStorage.setItem('personaos-layout', layoutName)
    
    switch (layoutName) {
      case 'focused':
        setSidebarWidth(280)
        setSidebarCollapsed(false)
        setSidebarMinimized(false)
        break
      case 'wide':
        setSidebarWidth(400)
        setSidebarCollapsed(false)
        setSidebarMinimized(false)
        break
      case 'minimal':
        setSidebarMinimized(true)
        setSidebarCollapsed(false)
        break
      case 'chat-only':
        setSidebarCollapsed(true)
        break
      default: // default
        setSidebarWidth(320)
        setSidebarCollapsed(false)
        setSidebarMinimized(false)
    }
  }

  // Panel controls
  const toggleSidebarCollapse = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  const toggleSidebarMinimize = () => {
    setSidebarMinimized(!sidebarMinimized)
  }

  const checkSetupStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/setup/defaults`)
      if (response.ok) {
        const data = await response.json()
        const hasBasicConfig = data.current_values.LLM_PROVIDER || 
                              data.current_values.OLLAMA_MODEL ||
                              Object.values(data.current_values).some(val => val && val.trim())
        setIsConfigured(hasBasicConfig)
        if (!hasBasicConfig) {
          setShowOnboarding(true)
        }
      }
    } catch (err) {
      console.warn('Could not check setup status:', err)
      setShowOnboarding(true)
    }
  }

  const handleOnboardingComplete = (result) => {
    console.log('Onboarding completed:', result)
    setShowOnboarding(false)
    setIsConfigured(true)
  }

  const toggleTheme = () => {
    const html = document.documentElement
    const currentTheme = html.getAttribute('data-theme')
    const newTheme = currentTheme === 'light' ? 'dark' : 'light'
    html.setAttribute('data-theme', newTheme)
    localStorage.setItem('theme', newTheme)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!message.trim()) {
      setError('Please enter a message')
      return
    }

    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message.trim(),
          context: null
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setResponse(data)
      setMessage('')
      
    } catch (err) {
      console.error('Error sending message:', err)
      setError(`Failed to send message: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const createNewConversation = () => {
    const newConversation = {
      id: conversationCounter,
      name: `New Conversation ${conversationCounter}`,
      preview: 'Start a new conversation...',
      active: false
    }
    
    setConversations(prev => {
      const updated = prev.map(conv => ({ ...conv, active: false }))
      return [{ ...newConversation, active: true }, ...updated]
    })
    
    setConversationCounter(prev => prev + 1)
    setResponse(null)
    setError(null)
  }

  const selectConversation = (id) => {
    setConversations(prev => 
      prev.map(conv => ({ ...conv, active: conv.id === id }))
    )
    setResponse(null)
    setError(null)
  }

  const renameConversation = (id) => {
    const conversation = conversations.find(conv => conv.id === id)
    const newName = prompt('Enter new conversation name:', conversation.name)
    if (newName && newName.trim()) {
      setConversations(prev =>
        prev.map(conv =>
          conv.id === id ? { ...conv, name: newName.trim() } : conv
        )
      )
    }
  }

  const deleteConversation = (id) => {
    if (confirm('Are you sure you want to delete this conversation?')) {
      const wasActive = conversations.find(conv => conv.id === id)?.active
      setConversations(prev => prev.filter(conv => conv.id !== id))
      
      if (wasActive) {
        const remaining = conversations.filter(conv => conv.id !== id)
        if (remaining.length > 0) {
          setConversations(prev => 
            prev.map((conv, index) => 
              index === 0 ? { ...conv, active: true } : conv
            )
          )
        } else {
          setResponse(null)
          setError(null)
        }
      }
    }
  }

  if (showOnboarding) {
    return <OnboardingWizard onComplete={handleOnboardingComplete} />
  }

  return (
    <div className="app-container">
      {/* Layout Controls */}
      <div className="layout-controls">
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginRight: 'var(--space-4)' }}>
          Layout:
        </span>
        <button 
          className={`layout-preset-btn ${currentLayout === 'default' ? 'active' : ''}`}
          onClick={() => applyLayout('default')}
        >
          Default
        </button>
        <button 
          className={`layout-preset-btn ${currentLayout === 'focused' ? 'active' : ''}`}
          onClick={() => applyLayout('focused')}
        >
          Focused
        </button>
        <button 
          className={`layout-preset-btn ${currentLayout === 'wide' ? 'active' : ''}`}
          onClick={() => applyLayout('wide')}
        >
          Wide
        </button>
        <button 
          className={`layout-preset-btn ${currentLayout === 'minimal' ? 'active' : ''}`}
          onClick={() => applyLayout('minimal')}
        >
          Minimal
        </button>
        <button 
          className={`layout-preset-btn ${currentLayout === 'chat-only' ? 'active' : ''}`}
          onClick={() => applyLayout('chat-only')}
        >
          Chat Only
        </button>
      </div>

      <div className="resizable-panel-group">
        {/* Sidebar Panel */}
        <div 
          className={`resizable-panel sidebar ${sidebarCollapsed ? 'collapsed' : ''} ${sidebarMinimized ? 'panel-minimized' : ''}`}
          style={{ width: sidebarCollapsed ? 0 : sidebarMinimized ? 60 : sidebarWidth }}
        >
          {/* Panel Header */}
          <div className="panel-header">
            <div className="panel-title">
              <div className="panel-icon">🤖</div>
              <span>PersonaOS</span>
            </div>
            <div className="panel-controls">
              <button 
                className="panel-control-btn" 
                onClick={toggleTheme}
                title="Toggle Theme"
              >
                🌙
              </button>
              <button 
                className="panel-control-btn"
                onClick={toggleSidebarMinimize}
                title={sidebarMinimized ? "Expand Panel" : "Minimize Panel"}
              >
                {sidebarMinimized ? '↗️' : '↙️'}
              </button>
              <button 
                className="panel-control-btn"
                onClick={toggleSidebarCollapse}
                title="Hide Panel"
              >
                ←
              </button>
            </div>
          </div>

          {/* Panel Content */}
          <div className="panel-content">
            <div className="sidebar-nav">
              <div className="nav-tabs">
                <button 
                  className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
                  onClick={() => setActiveTab('chat')}
                >
                  Chat
                </button>
                <button 
                  className={`nav-tab ${activeTab === 'settings' ? 'active' : ''}`}
                  onClick={() => setActiveTab('settings')}
                >
                  Settings
                </button>
                <button 
                  className={`nav-tab ${activeTab === 'models' ? 'active' : ''}`}
                  onClick={() => setActiveTab('models')}
                >
                  Models
                </button>
              </div>
            {/* Chat Content (Conversation Section) */}
            {activeTab === 'chat' && (
              <div className="conversation-section">
                <div className="conversation-header">
                  <div className="conversation-title">Conversations</div>
                  <button className="new-conversation-btn" onClick={createNewConversation}>
                    + New
                  </button>
                </div>

                <div className="conversation-list">
                  {conversations.map((conversation) => (
                    <div 
                      key={conversation.id}
                      className={`conversation-item ${conversation.active ? 'active' : ''}`}
                      onClick={() => selectConversation(conversation.id)}
                    >
                      <div className="conversation-info">
                        <div className="conversation-name">{conversation.name}</div>
                        <div className="conversation-preview">{conversation.preview}</div>
                      </div>
                      <div className="conversation-actions">
                        <button 
                          className="action-btn" 
                          onClick={(e) => {
                            e.stopPropagation()
                            renameConversation(conversation.id)
                          }}
                          title="Rename"
                        >
                          ✏️
                        </button>
                        <button 
                          className="action-btn delete" 
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteConversation(conversation.id)
                          }}
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Settings Content */}
            {activeTab === 'settings' && (
              <SettingsPanel onConfigurationUpdate={() => setIsConfigured(true)} />
            )}

            {/* Models Content */}
            {activeTab === 'models' && (
              <ModelsPanel />
            )}
          </div>
        </div>

        {/* Drag Handle */}
        {!sidebarCollapsed && (
          <div 
            className="drag-handle" 
            ref={dragRef}
            onMouseDown={startResize}
            title="Drag to resize"
          />
        )}

        {/* Main Content Panel */}
        <div className="resizable-panel main-content" style={{ flex: 1 }}>
          <div className="panel-header">
            <div className="panel-title">
              <div className="panel-icon">💬</div>
              <span>Chat Interface</span>
            </div>
            <div className="panel-controls">
              {sidebarCollapsed && (
                <button 
                  className="panel-control-btn"
                  onClick={toggleSidebarCollapse}
                  title="Show Sidebar"
                >
                  →
                </button>
              )}
            </div>
          </div>

          <div className="panel-content">
            {/* Chat Header */}
            <div className="chat-header">
              <div className="llm-selector">
                <div className="llm-label">Model:</div>
                <ModelDropdown />
              </div>

              <div className="chat-status">
                <div className="status-indicator"></div>
                <span>Connected</span>
              </div>
            </div>

        {/* Chat Messages */}
        <div className="chat-messages">
          {!response && !loading && !error && conversations.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon">💬</div>
              <div className="empty-title">Start a new conversation</div>
              <div className="empty-subtitle">
                Ask me anything! I'm here to help with coding, questions, creative tasks, and more.
              </div>
            </div>
          )}

          {!response && !loading && !error && conversations.length > 0 && (
            <div className="message assistant">
              <div className="message-header">
                <div className="message-avatar avatar-assistant">AI</div>
                <span>PersonaOS Assistant</span>
                <span className="message-time">Just now</span>
              </div>
              <div className="message-bubble">
                Welcome to PersonaOS! I'm your local AI assistant. I'm running entirely on your machine, ensuring your privacy and data security. How can I help you today?
              </div>
            </div>
          )}

          {loading && (
            <div className="message assistant">
              <div className="message-header">
                <div className="message-avatar avatar-assistant">AI</div>
                <span>PersonaOS Assistant</span>
                <span className="message-time">typing...</span>
              </div>
              <div className="typing-indicator">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          )}

          {error && (
            <div className="setting-warning" style={{ margin: '20px' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {response && !loading && (
            <ResponseCard response={response} />
          )}
        </div>

        {/* Chat Input Area */}
        <div className="chat-input-area">
          <form onSubmit={handleSubmit}>
            <div className="chat-input-container">
              <textarea
                className="chat-input"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message here... (Shift+Enter for new line, Enter to send)"
                rows="1"
                disabled={loading}
              />
              <button 
                type="submit" 
                disabled={loading || !message.trim()}
                className="send-btn"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="m22 2-7 20-4-9-9-4z"/>
                  <path d="M22 2 11 13"/>
                </svg>
              </button>
            </div>
          </form>
        </div>
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="status-bar">
        <div className="status-left">
          <div className="status-item">
            <div className="status-indicator-small"></div>
            <span>Online</span>
          </div>
          <div className="status-item">
            <span>Layout: {currentLayout}</span>
          </div>
          <div className="status-item">
            <span>Panel: {sidebarWidth}px</span>
          </div>
        </div>
        <div className="status-right">
          <div className="status-item">
            <span>Conversations: {conversations.length}</span>
          </div>
          <div className="status-item">
            <span>PersonaOS v0.1.0</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// Model Dropdown Component
function ModelDropdown() {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedModel, setSelectedModel] = useState(null)
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const API_BASE_URL = 'http://localhost:8000'

  useEffect(() => {
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/models`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setModels(data.models)
      setSelectedModel(data.current_model || data.models[0]?.name || 'No models available')
      
    } catch (err) {
      console.error('Error loading models:', err)
      setError(`Failed to load models: ${err.message}`)
      setModels([])
      setSelectedModel('Error loading models')
    } finally {
      setLoading(false)
    }
  }

  const selectModel = async (modelName) => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/models/load`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_name: modelName
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      if (result.success) {
        setSelectedModel(modelName)
        setIsOpen(false)
      } else {
        throw new Error(result.message || 'Failed to load model')
      }
      
    } catch (err) {
      console.error('Error loading model:', err)
      setError(`Failed to load model: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest('.dropdown')) {
        setIsOpen(false)
      }
    }

    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [])

  return (
    <div className={`dropdown ${isOpen ? 'open' : ''}`}>
      <div className="dropdown-trigger" onClick={() => setIsOpen(!isOpen)}>
        <span>{loading ? 'Loading...' : selectedModel || 'Select Model'}</span>
        <span>▼</span>
      </div>
      <div className="dropdown-content">
        {error && (
          <div className="dropdown-item error">
            <span style={{ color: 'var(--color-error)', fontSize: '0.875rem' }}>
              {error}
            </span>
          </div>
        )}
        {models.map((model, index) => (
          <div 
            key={index}
            className={`dropdown-item ${selectedModel === model.name ? 'selected' : ''}`}
            onClick={() => selectModel(model.name)}
          >
            <span>{model.name}</span>
            <span className={`model-status status-${model.status}`}>
              {model.size && <small>({model.size})</small>}
              {model.status === 'available' && ' Available'}
              {model.status === 'loading' && ' Loading'}
              {model.status === 'error' && ' Error'}
            </span>
          </div>
        ))}
        {models.length === 0 && !loading && !error && (
          <div className="dropdown-item">
            <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              No models available
            </span>
          </div>
        )}
        <div className="dropdown-item" style={{ borderTop: '1px solid var(--border-color)', marginTop: '8px', paddingTop: '8px' }}>
          <button 
            onClick={(e) => {
              e.stopPropagation()
              loadModels()
            }}
            style={{ 
              background: 'none', 
              border: 'none', 
              color: 'var(--color-primary)', 
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            🔄 Refresh Models
          </button>
        </div>
      </div>
    </div>
  )
}

// Response Card Component
function ResponseCard({ response }) {
  const {
    reply,
    intent,
    tools_used = [],
    confidence = 0,
    processing_time_ms = 0
  } = response

  const now = new Date()
  const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <>
      <div className="message user">
        <div className="message-header">
          <span className="message-time">{timeString}</span>
          <span>You</span>
          <div className="message-avatar avatar-user">U</div>
        </div>
        <div className="message-bubble">
          What time is it?
        </div>
      </div>

      <div className="message assistant">
        <div className="message-header">
          <div className="message-avatar avatar-assistant">AI</div>
          <span>PersonaOS Assistant</span>
          <span className="message-time">{timeString}</span>
        </div>
        <div className="message-bubble">
          {reply}
          
          {(tools_used.length > 0 || confidence > 0) && (
            <div style={{ marginTop: '12px', padding: '8px', background: 'var(--bg-tertiary)', borderRadius: '0.5rem', fontSize: '0.875rem' }}>
              {intent && <div><strong>Intent:</strong> {intent}</div>}
              {confidence > 0 && <div><strong>Confidence:</strong> {Math.round(confidence * 100)}%</div>}
              {processing_time_ms > 0 && <div><strong>Processing Time:</strong> {processing_time_ms}ms</div>}
              {tools_used.length > 0 && (
                <div><strong>Tools Used:</strong> {tools_used.join(', ')}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// Collapsible Section Component
function CollapsibleSection({ title, icon, children, defaultExpanded = false }) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  
  const toggleExpanded = () => {
    setExpanded(!expanded)
  }
  
  return (
    <div className={`collapsible-section ${expanded ? 'expanded' : ''}`}>
      <div className="collapsible-header" onClick={toggleExpanded}>
        <div className="collapsible-title">
          <div className="collapsible-icon">{icon}</div>
          <span>{title}</span>
        </div>
        <div className="collapsible-chevron">▼</div>
      </div>
      <div className="collapsible-content">
        <div className="collapsible-body">
          {children}
        </div>
      </div>
    </div>
  )
}

// Settings Panel Component (Enhanced)
function SettingsPanel({ onConfigurationUpdate }) {
  const [configSections, setConfigSections] = useState({})
  const [formData, setFormData] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const API_BASE_URL = 'http://localhost:8000'

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/setup/defaults`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setConfigSections(data.config_sections)
      
      const initialFormData = {}
      Object.values(data.config_sections).forEach(section => {
        Object.entries(section).forEach(([key, config]) => {
          initialFormData[key] = data.current_values[key] || config.default || ''
        })
      })
      setFormData(initialFormData)
      
    } catch (err) {
      console.error('Error loading settings:', err)
      setError(`Failed to load settings: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (key, value) => {
    setFormData(prev => ({
      ...prev,
      [key]: value
    }))
    setSuccess(false)
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(false)
      
      const response = await fetch(`${API_BASE_URL}/api/setup/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          config: formData
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      if (result.success) {
        setSuccess(true)
        onConfigurationUpdate && onConfigurationUpdate()
      } else {
        throw new Error(result.message || 'Configuration failed')
      }
      
    } catch (err) {
      console.error('Error saving settings:', err)
      setError(`Failed to save settings: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const togglePasswordVisibility = (inputId) => {
    const input = document.getElementById(inputId)
    const button = input.nextElementSibling
    
    if (input.type === 'password') {
      input.type = 'text'
      button.textContent = '🙈'
    } else {
      input.type = 'password'
      button.textContent = '👁️'
    }
  }

  if (loading) {
    return (
      <div className="settings-content">
        <div className="empty-state">
          <div className="empty-icon">⚙️</div>
          <div className="empty-title">Loading settings...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="conversation-section">
      <div className="conversation-header">
        <div className="conversation-title">Settings</div>
      </div>
      
      <div className="settings-content">
        {error && (
          <div className="setting-warning">
            <strong>Error:</strong> {error}
          </div>
        )}

        {success && (
          <div className="setting-info-box">
            <strong>Success:</strong> Settings saved successfully!
          </div>
        )}

        {Object.entries(configSections).map(([sectionKey, section]) => {
          const getSectionIcon = (key) => {
            if (key.includes('LLM')) return '🤖'
            if (key.includes('API')) return '🔑'
            if (key.includes('Audio')) return '🔊'
            if (key.includes('Intent')) return '🛡️'
            if (key.includes('Developer')) return '⚙️'
            if (key.includes('Web')) return '🌐'
            return '⚙️'
          }

          return (
            <CollapsibleSection 
              key={sectionKey}
              title={sectionKey}
              icon={getSectionIcon(sectionKey)}
              defaultExpanded={sectionKey.includes('LLM') || sectionKey.includes('API')}
            >
              <div className="settings-grid-enhanced">
                {Object.entries(section).map(([key, config]) => (
                  <div key={key} className="setting-group">
                    <div className="setting-group-title">
                      <span className="setting-group-icon">
                        {config.sensitive ? '🔒' : '⚙️'}
                      </span>
                      <span>
                        {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                    </div>
                    
                    <div className="setting-description" style={{ marginBottom: 'var(--space-3)' }}>
                      {config.help}
                      {config.default && (
                        <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                          {' '}(Default: {config.default})
                        </span>
                      )}
                    </div>

                    <div className="setting-control">
                      {config.sensitive ? (
                        <div className="api-key-input">
                          <input
                            id={key}
                            type="password"
                            className="input"
                            value={formData[key] || ''}
                            onChange={(e) => handleInputChange(key, e.target.value)}
                            placeholder="Enter your API key..."
                          />
                          <button 
                            type="button"
                            className="api-key-toggle" 
                            onClick={() => togglePasswordVisibility(key)}
                          >
                            👁️
                          </button>
                        </div>
                      ) : (
                        <input
                          type="text"
                          className="input"
                          value={formData[key] || ''}
                          onChange={(e) => handleInputChange(key, e.target.value)}
                          placeholder={config.default}
                        />
                      )}
                    </div>
                    
                    {config.sensitive && formData[key] && (
                      <div className="setting-warning" style={{ marginTop: 'var(--space-3)' }}>
                        ⚠️ API keys are stored locally and never sent to PersonaOS servers
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )
        })}
      </div>

      <div className="settings-actions">
        <button 
          onClick={handleSave}
          disabled={saving}
          className="btn btn-primary"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
        <button 
          onClick={loadSettings}
          disabled={saving || loading}
          className="btn btn-secondary"
        >
          Reload Settings
        </button>
      </div>
    </div>
  )
}

// Models Management Panel Component
function ModelsPanel() {
  const [models, setModels] = useState([])
  const [currentModel, setCurrentModel] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [downloadModel, setDownloadModel] = useState('')
  const [downloadLoading, setDownloadLoading] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState('')
  const [selectedModel, setSelectedModel] = useState(null)
  const [promptLoading, setPromptLoading] = useState(false)
  const [modelSettings, setModelSettings] = useState({})
  const [settingsLoading, setSettingsLoading] = useState(false)

  const API_BASE_URL = 'http://localhost:8000'

  useEffect(() => {
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/models`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setModels(data.models)
      setCurrentModel(data.current_model)
      
    } catch (err) {
      console.error('Error loading models:', err)
      setError(`Failed to load models: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadModel = async () => {
    if (!downloadModel.trim()) return
    
    try {
      setDownloadLoading(true)
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/models/${downloadModel}/download`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      if (result.success) {
        setDownloadModel('')
        await loadModels()
      } else {
        throw new Error(result.message || 'Failed to download model')
      }
      
    } catch (err) {
      console.error('Error downloading model:', err)
      setError(`Failed to download model: ${err.message}`)
    } finally {
      setDownloadLoading(false)
    }
  }

  const handleRemoveModel = async (modelName) => {
    if (!confirm(`Are you sure you want to remove model "${modelName}"?`)) return
    
    try {
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/models/${modelName}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      if (result.success) {
        await loadModels()
      } else {
        throw new Error(result.message || 'Failed to remove model')
      }
      
    } catch (err) {
      console.error('Error removing model:', err)
      setError(`Failed to remove model: ${err.message}`)
    }
  }

  const loadSystemPrompt = async (modelName) => {
    try {
      setPromptLoading(true)
      
      const response = await fetch(`${API_BASE_URL}/api/models/${modelName}/prompt`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setSystemPrompt(data.system_prompt || '')
      
    } catch (err) {
      console.error('Error loading system prompt:', err)
      setSystemPrompt('')
    } finally {
      setPromptLoading(false)
    }
  }

  const saveSystemPrompt = async () => {
    if (!selectedModel) return
    
    try {
      setPromptLoading(true)
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/models/${selectedModel}/prompt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_name: selectedModel,
          system_prompt: systemPrompt
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      if (!result.success) {
        throw new Error(result.message || 'Failed to save system prompt')
      }
      
    } catch (err) {
      console.error('Error saving system prompt:', err)
      setError(`Failed to save system prompt: ${err.message}`)
    } finally {
      setPromptLoading(false)
    }
  }

  const loadModelSettings = async (modelName) => {
    try {
      setSettingsLoading(true)
      
      const response = await fetch(`${API_BASE_URL}/api/models/${modelName}/settings`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setModelSettings(data.settings || {})
      
    } catch (err) {
      console.error('Error loading model settings:', err)
      setModelSettings({})
    } finally {
      setSettingsLoading(false)
    }
  }

  const saveModelSettings = async () => {
    if (!selectedModel) return
    
    try {
      setSettingsLoading(true)
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/models/${selectedModel}/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_name: selectedModel,
          settings: modelSettings
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      if (!result.success) {
        throw new Error(result.message || 'Failed to save model settings')
      }
      
    } catch (err) {
      console.error('Error saving model settings:', err)
      setError(`Failed to save model settings: ${err.message}`)
    } finally {
      setSettingsLoading(false)
    }
  }

  const handleModelSelect = (modelName) => {
    setSelectedModel(modelName)
    loadSystemPrompt(modelName)
    loadModelSettings(modelName)
  }

  return (
    <div className="conversation-section">
      <div className="conversation-header">
        <div className="conversation-title">Model Management</div>
      </div>
      
      <div className="settings-content">
        {error && (
          <div className="setting-warning">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Installed Models Section */}
        <CollapsibleSection
          title="Installed Models"
          subtitle={`${models.length} model${models.length !== 1 ? 's' : ''} available`}
          icon="📦"
          isCollapsed={false}
          onToggle={() => {}}
        >
          <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'flex-end' }}>
            <button 
              onClick={loadModels}
              disabled={loading}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
            >
              {loading ? 'Refreshing...' : '🔄 Refresh'}
            </button>
          </div>

          {loading ? (
            <div className="empty-state">
              <div className="empty-icon">⏳</div>
              <div className="empty-title">Loading models...</div>
            </div>
          ) : models.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📦</div>
              <div className="empty-title">No models installed</div>
              <div className="empty-subtitle">Download a model to get started</div>
            </div>
          ) : (
            <div className="settings-grid">
              {models.map((model, index) => (
                <div key={index} className="setting-item" style={{ cursor: 'pointer' }} onClick={() => handleModelSelect(model.name)}>
                  <div className="setting-header">
                    <div className="setting-info">
                      <div className="setting-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span>{model.name}</span>
                        {currentModel === model.name && (
                          <span style={{ 
                            background: 'var(--color-primary)', 
                            color: 'white', 
                            padding: '2px 6px', 
                            borderRadius: '4px', 
                            fontSize: '0.75rem' 
                          }}>
                            Current
                          </span>
                        )}
                        {selectedModel === model.name && (
                          <span style={{ 
                            background: 'var(--color-secondary)', 
                            color: 'white', 
                            padding: '2px 6px', 
                            borderRadius: '4px', 
                            fontSize: '0.75rem' 
                          }}>
                            Selected
                          </span>
                        )}
                      </div>
                      <div className="setting-description">
                        {model.size && `Size: ${model.size}`}
                        {model.modified && ` • Modified: ${model.modified}`}
                      </div>
                    </div>
                    <div className="setting-control">
                      <button 
                        className="btn btn-danger"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleRemoveModel(model.name)
                        }}
                        style={{ padding: '4px 8px', fontSize: '0.875rem' }}
                      >
                        🗑️ Remove
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CollapsibleSection>

        {/* Download Models Section */}
        <CollapsibleSection
          title="Download Models"
          subtitle="Add new models from Ollama repository"
          icon="📥"
          isCollapsed={true}
          onToggle={() => {}}
        >
          <div style={{ marginBottom: '16px' }}>
            <div className="setting-description">
              Enter a model name to download from Ollama (e.g., llama3:8b, mistral:7b, codellama:13b)
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
            <input
              type="text"
              className="input"
              value={downloadModel}
              onChange={(e) => setDownloadModel(e.target.value)}
              placeholder="Enter model name (e.g., llama3:8b)"
              style={{ flex: 1 }}
            />
            <button 
              onClick={handleDownloadModel}
              disabled={downloadLoading || !downloadModel.trim()}
              className="btn btn-primary"
            >
              {downloadLoading ? 'Downloading...' : '📥 Download'}
            </button>
          </div>

          <div className="setting-info-box">
            <strong>Popular Models:</strong>
            <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
              <li><code>llama3:8b</code> - General purpose, good balance of speed and capability</li>
              <li><code>mistral:7b</code> - Fast and efficient, great for coding</li>
              <li><code>codellama:13b</code> - Specialized for programming tasks</li>
              <li><code>llama3:70b</code> - Most capable, requires more resources</li>
            </ul>
          </div>
        </CollapsibleSection>

        {/* Model Configuration Section */}
        {selectedModel && (
          <CollapsibleSection
            title="Model Configuration"
            subtitle={`Configure ${selectedModel}`}
            icon="⚙️"
            isCollapsed={false}
            onToggle={() => {}}
          >
            <div style={{ marginBottom: '24px' }}>
              <div className="setting-description">
                Customize system prompt and generation settings for {selectedModel}
              </div>
            </div>

            {/* System Prompt Editor */}
            <div className="settings-section">
              <div className="settings-section-title">
                <div className="settings-section-icon">💬</div>
                <span>System Prompt</span>
              </div>
              
              <div style={{ marginBottom: '16px' }}>
                <textarea
                  className="input"
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="Enter system prompt for this model..."
                  rows="6"
                  style={{ width: '100%', resize: 'vertical' }}
                  disabled={promptLoading}
                />
              </div>
              
              <button 
                onClick={saveSystemPrompt}
                disabled={promptLoading}
                className="btn btn-primary"
                style={{ marginBottom: '24px' }}
              >
                {promptLoading ? 'Saving...' : '💾 Save System Prompt'}
              </button>
            </div>

            {/* Model Settings */}
            <div className="settings-section">
              <div className="settings-section-title">
                <div className="settings-section-icon">⚙️</div>
                <span>Generation Settings</span>
              </div>
              
              <div className="settings-grid">
                <div className="setting-item">
                  <div className="setting-header">
                    <div className="setting-info">
                      <div className="setting-title">Temperature</div>
                      <div className="setting-description">Controls randomness (0.0 = deterministic, 1.0 = very random)</div>
                    </div>
                    <div className="setting-control">
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={modelSettings.temperature || 0.7}
                        onChange={(e) => setModelSettings(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                        style={{ width: '100px' }}
                      />
                      <span style={{ marginLeft: '8px', minWidth: '40px' }}>{modelSettings.temperature || 0.7}</span>
                    </div>
                  </div>
                </div>

                <div className="setting-item">
                  <div className="setting-header">
                    <div className="setting-info">
                      <div className="setting-title">Top P</div>
                      <div className="setting-description">Controls diversity (0.1 = focused, 1.0 = diverse)</div>
                    </div>
                    <div className="setting-control">
                      <input
                        type="range"
                        min="0.1"
                        max="1"
                        step="0.05"
                        value={modelSettings.top_p || 0.9}
                        onChange={(e) => setModelSettings(prev => ({ ...prev, top_p: parseFloat(e.target.value) }))}
                        style={{ width: '100px' }}
                      />
                      <span style={{ marginLeft: '8px', minWidth: '40px' }}>{modelSettings.top_p || 0.9}</span>
                    </div>
                  </div>
                </div>

                <div className="setting-item">
                  <div className="setting-header">
                    <div className="setting-info">
                      <div className="setting-title">Max Tokens</div>
                      <div className="setting-description">Maximum response length</div>
                    </div>
                    <div className="setting-control">
                      <input
                        type="number"
                        min="100"
                        max="8192"
                        step="100"
                        value={modelSettings.max_tokens || 2048}
                        onChange={(e) => setModelSettings(prev => ({ ...prev, max_tokens: parseInt(e.target.value) }))}
                        className="input"
                        style={{ width: '100px' }}
                      />
                    </div>
                  </div>
                </div>
              </div>
              
              <button 
                onClick={saveModelSettings}
                disabled={settingsLoading}
                className="btn btn-primary"
                style={{ marginTop: '16px' }}
              >
                {settingsLoading ? 'Saving...' : '💾 Save Settings'}
              </button>
            </div>
          </CollapsibleSection>
        )}
      </div>
    </div>
  )
}

export default App