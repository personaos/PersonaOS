import React, { useState, useEffect } from 'react'

function TestComponent() {
  const [loading, setLoading] = useState(false)
  const API_BASE_URL = 'http://localhost:8000'

  const loadModels = async () => {
    try {
      setLoading(true)
      
      const response = await fetch(`${API_BASE_URL}/api/models`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      console.log(data)
      
    } catch (err) {
      console.error('Error loading models:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <button onClick={loadModels}>
        {loading ? 'Loading...' : 'Test API'}
      </button>
    </div>
  )
}

export default TestComponent