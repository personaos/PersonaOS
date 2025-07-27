import React, { useState, useEffect } from 'react'
import OnboardingWizard from './components/OnboardingWizard'

function App() {
  const [message, setMessage] = useState('')
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [isConfigured, setIsConfigured] = useState(false)

  // TODO: Replace with actual PersonaOS API endpoint
  const API_BASE_URL = 'http://localhost:8000'

  // Check if setup is needed on mount
  useEffect(() => {
    checkSetupStatus()
  }, [])

  const checkSetupStatus = async () => {
    try {
      // Check if configuration exists by trying to load defaults
      const response = await fetch(`${API_BASE_URL}/api/setup/defaults`)
      if (response.ok) {
        const data = await response.json()
        // Check if at least basic configuration exists
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
      // If we can't check, assume we need setup
      setShowOnboarding(true)
    }
  }

  const handleOnboardingComplete = (result) => {
    console.log('Onboarding completed:', result)
    setShowOnboarding(false)
    setIsConfigured(true)
  }

  const handleShowSetup = () => {
    setShowOnboarding(true)
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
          context: null // TODO: Add conversation context tracking
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setResponse(data)
      
      // Clear the input after successful response
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

  // Show onboarding wizard if needed
  if (showOnboarding) {
    return <OnboardingWizard onComplete={handleOnboardingComplete} />
  }

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <h1>PersonaOS</h1>
        <p>Local AI Assistant - Web Interface</p>
        
        {/* Setup button for configured users */}
        {isConfigured && (
          <button 
            onClick={handleShowSetup} 
            className="setup-button"
            title="Reconfigure PersonaOS"
          >
            ⚙️ Setup
          </button>
        )}
      </header>

      {/* Main Chat Interface */}
      <main className="chat-container">
        
        {/* Input Section */}
        <section className="input-section">
          <form onSubmit={handleSubmit}>
            <div className="input-group">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask PersonaOS anything... (e.g., 'What time is it?')"
                className="message-input"
                disabled={loading}
                maxLength={500}
              />
              <button 
                type="submit" 
                disabled={loading || !message.trim()}
                className="send-button"
              >
                {loading ? 'Processing...' : 'Send'}
              </button>
            </div>
          </form>
          
          {/* Quick examples */}
          <div style={{ fontSize: '0.9rem', color: '#6c757d', marginTop: '10px' }}>
            <strong>Try asking:</strong> "What time is it?", "Hello PersonaOS", "Help me with something"
          </div>
        </section>

        {/* Loading State */}
        {loading && (
          <div className="loading">
            <p>🤖 PersonaOS is thinking...</p>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Response Display */}
        {response && !loading && (
          <ResponseCard response={response} />
        )}

        {/* Empty State */}
        {!response && !loading && !error && (
          <div className="empty-state">
            <p>Start a conversation with PersonaOS by typing a message above.</p>
          </div>
        )}

      </main>

      {/* Footer with system info */}
      <footer style={{ textAlign: 'center', marginTop: '20px', color: '#6c757d' }}>
        <p>PersonaOS v0.1.0 | Local-first AI Assistant</p>
      </footer>
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

  return (
    <div className="response-card">
      {/* Response Header */}
      <div className="response-header">
        <div className="response-title">PersonaOS Response</div>
        <div className="intent-badge">{intent}</div>
      </div>

      {/* Main Response Text */}
      <div className="response-text">
        {reply}
      </div>

      {/* Metadata Section */}
      <div className="metadata">
        <div className="metadata-item">
          <div className="metadata-label">Confidence</div>
          <div className="metadata-value">
            {Math.round(confidence * 100)}%
          </div>
        </div>
        
        <div className="metadata-item">
          <div className="metadata-label">Processing Time</div>
          <div className="metadata-value">
            {processing_time_ms}ms
          </div>
        </div>
        
        <div className="metadata-item">
          <div className="metadata-label">Tools Used</div>
          <div className="metadata-value">
            {tools_used.length > 0 ? (
              <div className="tools-list">
                {tools_used.map((tool, index) => (
                  <span key={index} className="tool-tag">
                    {tool}
                  </span>
                ))}
              </div>
            ) : (
              <span style={{ color: '#6c757d', fontStyle: 'italic' }}>None</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

// TODO: Future enhancements:
// 1. Add conversation history/context tracking
// 2. Implement real-time WebSocket communication
// 3. Add voice input/output capabilities
// 4. Create settings panel for PersonaOS configuration
// 5. Add tool execution visualization
// 6. Implement user authentication if needed
// 7. Add export/import for conversation history
// 8. Create mobile-responsive design improvements
// 9. Add theme switching (dark/light mode)
// 10. Integrate with PersonaOS plugin system for dynamic tool discovery