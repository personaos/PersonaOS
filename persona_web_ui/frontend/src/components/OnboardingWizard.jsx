import React, { useState, useEffect } from 'react'
import './OnboardingWizard.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const OnboardingWizard = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0)
  const [configSections, setConfigSections] = useState({})
  const [formData, setFormData] = useState({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [skippedSections, setSkippedSections] = useState(new Set())

  // Load configuration defaults on mount
  useEffect(() => {
    loadDefaults()
  }, [])

  const loadDefaults = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/setup/defaults`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setConfigSections(data.config_sections)
      
      // Initialize form data with current values or defaults
      const initialFormData = {}
      Object.values(data.config_sections).forEach(section => {
        Object.entries(section).forEach(([key, config]) => {
          initialFormData[key] = data.current_values[key] || config.default || ''
        })
      })
      setFormData(initialFormData)
      
    } catch (err) {
      console.error('Error loading defaults:', err)
      setError(`Failed to load configuration: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const sectionKeys = Object.keys(configSections)
  const currentSectionKey = sectionKeys[currentStep]
  const currentSection = configSections[currentSectionKey]
  const isLastStep = currentStep === sectionKeys.length - 1
  const isReviewStep = currentStep === sectionKeys.length

  const handleInputChange = (key, value) => {
    setFormData(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const handleNext = () => {
    if (isLastStep) {
      setCurrentStep(sectionKeys.length) // Go to review step
    } else {
      setCurrentStep(prev => prev + 1)
    }
  }

  const handleBack = () => {
    if (isReviewStep) {
      setCurrentStep(sectionKeys.length - 1)
    } else {
      setCurrentStep(prev => Math.max(0, prev - 1))
    }
  }

  const handleSkipSection = () => {
    const sectionKey = sectionKeys[currentStep]
    setSkippedSections(prev => new Set([...prev, sectionKey]))
    handleNext()
  }

  const handleSubmit = async () => {
    try {
      setSubmitting(true)
      setError(null)
      
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
        onComplete && onComplete(result)
      } else {
        throw new Error(result.message || 'Configuration failed')
      }
      
    } catch (err) {
      console.error('Error submitting configuration:', err)
      setError(`Failed to save configuration: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="onboarding-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading configuration...</p>
        </div>
      </div>
    )
  }

  if (error && Object.keys(configSections).length === 0) {
    return (
      <div className="onboarding-container">
        <div className="error-state">
          <h2>Configuration Error</h2>
          <p>{error}</p>
          <button onClick={loadDefaults} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="onboarding-container">
      <div className="onboarding-wizard">
        {/* Header */}
        <div className="wizard-header">
          <h1>🛠️ PersonaOS Setup</h1>
          <p>Configure your PersonaOS environment settings</p>
          
          {/* Progress indicator */}
          <div className="progress-indicator">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${((currentStep + 1) / (sectionKeys.length + 1)) * 100}%` }}
              ></div>
            </div>
            <span className="progress-text">
              Step {currentStep + 1} of {sectionKeys.length + 1}
            </span>
          </div>
        </div>

        {/* Error display */}
        {error && (
          <div className="error-banner">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Step content */}
        <div className="wizard-content">
          {isReviewStep ? (
            <ReviewStep 
              configSections={configSections}
              formData={formData}
              skippedSections={skippedSections}
            />
          ) : (
            <ConfigurationStep
              sectionKey={currentSectionKey}
              section={currentSection}
              formData={formData}
              onInputChange={handleInputChange}
            />
          )}
        </div>

        {/* Navigation */}
        <div className="wizard-navigation">
          <button 
            onClick={handleBack}
            disabled={currentStep === 0 || submitting}
            className="nav-button secondary"
          >
            Back
          </button>

          <div className="nav-actions">
            {!isReviewStep && (
              <button 
                onClick={handleSkipSection}
                disabled={submitting}
                className="nav-button tertiary"
              >
                Skip Section
              </button>
            )}
            
            {isReviewStep ? (
              <button 
                onClick={handleSubmit}
                disabled={submitting}
                className="nav-button primary"
              >
                {submitting ? 'Saving...' : 'Confirm & Save'}
              </button>
            ) : (
              <button 
                onClick={handleNext}
                disabled={submitting}
                className="nav-button primary"
              >
                {isLastStep ? 'Review & Confirm' : 'Next'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Configuration step component
const ConfigurationStep = ({ sectionKey, section, formData, onInputChange }) => {
  const maskApiKey = (value) => {
    if (!value) return ''
    if (value.startsWith('sk-') && value.length > 8) {
      return value.substring(0, 7) + '*'.repeat(value.length - 11) + value.slice(-4)
    }
    return value
  }

  return (
    <div className="config-step">
      <div className="section-header">
        <h2>{sectionKey}</h2>
        <p>Configure the settings for this section</p>
      </div>

      <div className="config-fields">
        {Object.entries(section).map(([key, config]) => (
          <div key={key} className="field-group">
            <label htmlFor={key} className="field-label">
              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              {config.default && (
                <span className="default-value"> (default: {config.default})</span>
              )}
            </label>
            
            <input
              id={key}
              type={config.sensitive ? 'password' : 'text'}
              value={formData[key] || ''}
              onChange={(e) => onInputChange(key, e.target.value)}
              placeholder={config.sensitive ? 'Enter your API key...' : config.default}
              className="field-input"
            />
            
            <div className="field-help">
              💡 {config.help}
              {config.sensitive && formData[key] && (
                <div className="masked-preview">
                  Current: {maskApiKey(formData[key])}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Review step component
const ReviewStep = ({ configSections, formData, skippedSections }) => {
  const maskSensitiveValue = (value, isSensitive) => {
    if (!value || !isSensitive) return value
    if (value.length <= 8) return '*'.repeat(value.length)
    return value.substring(0, 4) + '*'.repeat(value.length - 8) + value.slice(-4)
  }

  return (
    <div className="review-step">
      <div className="section-header">
        <h2>✅ Review Your Configuration</h2>
        <p>Please review your settings before saving</p>
      </div>

      <div className="review-sections">
        {Object.entries(configSections).map(([sectionKey, section]) => {
          const isSkipped = skippedSections.has(sectionKey)
          
          return (
            <div key={sectionKey} className={`review-section ${isSkipped ? 'skipped' : ''}`}>
              <h3>{sectionKey} {isSkipped && <span className="skipped-badge">Skipped</span>}</h3>
              
              {!isSkipped && (
                <div className="review-fields">
                  {Object.entries(section).map(([key, config]) => {
                    const value = formData[key] || ''
                    const displayValue = maskSensitiveValue(value, config.sensitive)
                    
                    return (
                      <div key={key} className="review-field">
                        <span className="field-name">{key}:</span>
                        <span className="field-value">
                          {displayValue || <em>(empty)</em>}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default OnboardingWizard