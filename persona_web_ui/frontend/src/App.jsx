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
  
  // History panel state
  const [historyViewMode, setHistoryViewMode] = useState('timeline') // 'timeline', 'grid', 'list'
  const [historySearchQuery, setHistorySearchQuery] = useState('')
  const [historyDateFilter, setHistoryDateFilter] = useState('all') // 'all', 'today', 'week', 'month'
  
  // Favorites/bookmarks state
  const [favorites, setFavorites] = useState([]) // Array of { id, type, conversationId, messageId?, threadId?, timestamp, note? }
  const [showFavorites, setShowFavorites] = useState(false)
  const [conversations, setConversations] = useState([
    {
      id: 1,
      name: 'Welcome Chat',
      preview: 'Getting started with PersonaOS...',
      active: true,
      messages: [
        {
          id: 1,
          sender: 'assistant',
          content: "Welcome to PersonaOS! I'm your local AI assistant. I'm running entirely on your machine, ensuring your privacy and data security. How can I help you today?",
          timestamp: new Date().toISOString(),
          threadId: null,
          parentMessageId: null
        }
      ],
      threads: [], // Array of thread objects: { id, name, branchFromMessageId, messages }
      createdAt: new Date().toISOString()
    }
  ])
  const [currentConversationId, setCurrentConversationId] = useState(1)
  const [conversationCounter, setConversationCounter] = useState(2)
  
  // Search functionality state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [showSearchResults, setShowSearchResults] = useState(false)
  const [searchType, setSearchType] = useState('all') // 'all', 'conversations', 'messages'
  const [isSearching, setIsSearching] = useState(false)
  
  // Threading functionality state
  const [currentThread, setCurrentThread] = useState(null) // { conversationId, branchPoint, threadName }
  const [showThreadSelector, setShowThreadSelector] = useState(false)
  const [threadingFromMessage, setThreadingFromMessage] = useState(null)
  
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
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('personaos-theme') || 'dark'
  })
  const [statusBarCollapsed, setStatusBarCollapsed] = useState(() => {
    return localStorage.getItem('personaos-statusbar-collapsed') === 'true'
  })
  const [statusBarLocation, setStatusBarLocation] = useState(() => {
    return localStorage.getItem('personaos-statusbar-location') || 'under-chat'
  })
  const [lastActivity, setLastActivity] = useState(new Date())
  const [responseTime, setResponseTime] = useState(null)

  const dragRef = useRef(null)
  const isDragging = useRef(false)
  
  const API_BASE_URL = 'http://localhost:8000'

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('personaos-theme', theme)
  }, [theme])

  // Status bar collapse state
  useEffect(() => {
    localStorage.setItem('personaos-statusbar-collapsed', statusBarCollapsed.toString())
  }, [statusBarCollapsed])

  // Status bar location state
  useEffect(() => {
    localStorage.setItem('personaos-statusbar-location', statusBarLocation)
  }, [statusBarLocation])

  // Theme toggle function
  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'dark' ? 'light' : 'dark')
  }

  // Status bar toggle function
  const toggleStatusBar = () => {
    setStatusBarCollapsed(prev => !prev)
  }

  // Status bar location change function
  const changeStatusBarLocation = (newLocation) => {
    setStatusBarLocation(newLocation)
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

  // Conversation Management Functions
  const createNewConversation = () => {
    const newConversation = {
      id: conversationCounter,
      name: `New Conversation`,
      preview: 'Start a new conversation...',
      active: false,
      messages: [],
      createdAt: new Date().toISOString()
    }
    
    // Deactivate current conversation
    setConversations(prev => prev.map(conv => ({ ...conv, active: false })))
    
    // Add new conversation and make it active
    setConversations(prev => [newConversation, ...prev])
    setCurrentConversationId(conversationCounter)
    setConversationCounter(prev => prev + 1)
    
    // Clear current response/error state
    setResponse(null)
    setError(null)
    
    // Save to localStorage
    saveConversationsToStorage([newConversation, ...conversations.map(conv => ({ ...conv, active: false }))])
  }

  const selectConversation = (conversationId) => {
    setConversations(prev => prev.map(conv => ({
      ...conv,
      active: conv.id === conversationId
    })))
    setCurrentConversationId(conversationId)
    
    // Load conversation messages
    const conversation = conversations.find(conv => conv.id === conversationId)
    if (conversation && conversation.messages.length > 0) {
      const lastMessage = conversation.messages[conversation.messages.length - 1]
      if (lastMessage.sender === 'assistant') {
        setResponse(lastMessage.content)
      }
    } else {
      setResponse(null)
    }
    setError(null)
    
    // Save to localStorage
    saveConversationsToStorage(conversations.map(conv => ({
      ...conv,
      active: conv.id === conversationId
    })))
  }

  const renameConversation = (conversationId, newName) => {
    if (!newName.trim()) return
    
    setConversations(prev => prev.map(conv => 
      conv.id === conversationId 
        ? { ...conv, name: newName.trim() }
        : conv
    ))
    
    // Save to localStorage
    const updatedConversations = conversations.map(conv => 
      conv.id === conversationId 
        ? { ...conv, name: newName.trim() }
        : conv
    )
    saveConversationsToStorage(updatedConversations)
  }

  const deleteConversation = (conversationId) => {
    if (conversations.length <= 1) {
      // Don't delete the last conversation
      return
    }
    
    const updatedConversations = conversations.filter(conv => conv.id !== conversationId)
    
    // If we're deleting the active conversation, activate the first remaining one
    if (currentConversationId === conversationId) {
      const firstConv = updatedConversations[0]
      if (firstConv) {
        firstConv.active = true
        setCurrentConversationId(firstConv.id)
        // Load its messages
        if (firstConv.messages.length > 0) {
          const lastMessage = firstConv.messages[firstConv.messages.length - 1]
          if (lastMessage.sender === 'assistant') {
            setResponse(lastMessage.content)
          }
        } else {
          setResponse(null)
        }
      }
    }
    
    setConversations(updatedConversations)
    saveConversationsToStorage(updatedConversations)
  }

  const addMessageToConversation = (conversationId, message) => {
    const updatedConversations = conversations.map(conv => {
      if (conv.id === conversationId) {
        const newMessage = {
          id: (conv.messages.length + 1),
          ...message,
          timestamp: new Date().toISOString()
        }
        const updatedMessages = [...conv.messages, newMessage]
        
        // Update preview with the latest message
        const preview = message.sender === 'user' 
          ? message.content.substring(0, 50) + (message.content.length > 50 ? '...' : '')
          : conv.preview
        
        return {
          ...conv,
          messages: updatedMessages,
          preview
        }
      }
      return conv
    })
    
    setConversations(updatedConversations)
    saveConversationsToStorage(updatedConversations)
  }

  const saveConversationsToStorage = (conversationsToSave) => {
    try {
      localStorage.setItem('personaos-conversations', JSON.stringify(conversationsToSave))
    } catch (error) {
      console.warn('Failed to save conversations to localStorage:', error)
    }
  }

  // Search functionality
  const performSearch = useCallback((query, type = 'all') => {
    if (!query.trim()) {
      setSearchResults([])
      setShowSearchResults(false)
      return
    }

    setIsSearching(true)
    
    // Debounce search to avoid excessive processing
    const searchTimeout = setTimeout(() => {
      const results = []
      const searchTerm = query.toLowerCase().trim()

      conversations.forEach(conversation => {
        // Search conversation names
        if ((type === 'all' || type === 'conversations') && 
            conversation.name.toLowerCase().includes(searchTerm)) {
          results.push({
            type: 'conversation',
            id: `conv-${conversation.id}`,
            conversationId: conversation.id,
            title: conversation.name,
            preview: conversation.preview,
            timestamp: conversation.createdAt,
            matchType: 'title'
          })
        }

        // Search message content
        if (type === 'all' || type === 'messages') {
          conversation.messages.forEach(message => {
            if (message.content.toLowerCase().includes(searchTerm)) {
              // Get context around the match
              const content = message.content
              const matchIndex = content.toLowerCase().indexOf(searchTerm)
              const contextStart = Math.max(0, matchIndex - 50)
              const contextEnd = Math.min(content.length, matchIndex + searchTerm.length + 50)
              const contextSnippet = content.substring(contextStart, contextEnd)
              
              results.push({
                type: 'message',
                id: `msg-${conversation.id}-${message.id}`,
                conversationId: conversation.id,
                conversationName: conversation.name,
                messageId: message.id,
                title: `${message.sender === 'user' ? 'You' : 'Assistant'}: ${contextSnippet}${contextEnd < content.length ? '...' : ''}`,
                preview: contextSnippet,
                timestamp: message.timestamp,
                sender: message.sender,
                matchType: 'content',
                fullContent: content
              })
            }
          })
        }
      })

      // Sort results by relevance and recency
      results.sort((a, b) => {
        // Prioritize exact title matches
        if (a.matchType === 'title' && b.matchType === 'content') return -1
        if (a.matchType === 'content' && b.matchType === 'title') return 1
        
        // Then by timestamp (most recent first)
        return new Date(b.timestamp) - new Date(a.timestamp)
      })

      setSearchResults(results)
      setShowSearchResults(true)
      setIsSearching(false)
    }, 300)

    return () => clearTimeout(searchTimeout)
  }, [conversations])

  // Handle search input changes
  const handleSearchChange = (query) => {
    setSearchQuery(query)
    performSearch(query, searchType)
  }

  // Handle search type changes
  const handleSearchTypeChange = (type) => {
    setSearchType(type)
    if (searchQuery.trim()) {
      performSearch(searchQuery, type)
    }
  }

  // Navigate to search result
  const navigateToSearchResult = (result) => {
    if (result.type === 'conversation') {
      selectConversation(result.conversationId)
      setShowSearchResults(false)
      setSearchQuery('')
    } else if (result.type === 'message') {
      selectConversation(result.conversationId)
      setShowSearchResults(false)
      setSearchQuery('')
      
      // Scroll to specific message (we'll implement this with message highlighting)
      setTimeout(() => {
        const messageElement = document.getElementById(`message-${result.messageId}`)
        if (messageElement) {
          messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
          messageElement.classList.add('search-highlight')
          setTimeout(() => {
            messageElement.classList.remove('search-highlight')
          }, 3000)
        }
      }, 100)
    }
  }

  // Clear search
  const clearSearch = () => {
    setSearchQuery('')
    setSearchResults([])
    setShowSearchResults(false)
  }

  // Threading functionality
  const createThread = (conversationId, branchFromMessageId, threadName) => {
    const conversation = conversations.find(conv => conv.id === conversationId)
    if (!conversation) return

    // Find the message to branch from
    const branchMessage = conversation.messages.find(msg => msg.id === branchFromMessageId)
    if (!branchMessage) return

    // Create new thread
    const newThread = {
      id: Date.now(), // Simple ID generation
      name: threadName || `Thread from message ${branchFromMessageId}`,
      branchFromMessageId,
      createdAt: new Date().toISOString(),
      messages: [] // Empty messages array for the new thread
    }

    // Update conversation with new thread
    const updatedConversations = conversations.map(conv => {
      if (conv.id === conversationId) {
        return {
          ...conv,
          threads: [...(conv.threads || []), newThread]
        }
      }
      return conv
    })

    setConversations(updatedConversations)
    saveConversationsToStorage(updatedConversations)

    // Switch to the new thread
    setCurrentThread({
      conversationId,
      threadId: newThread.id,
      branchPoint: branchFromMessageId
    })

    return newThread.id
  }

  const switchToThread = (conversationId, threadId) => {
    setCurrentThread({
      conversationId,
      threadId,
      branchPoint: null // Will be determined from thread data
    })
  }

  const switchToMainConversation = (conversationId) => {
    setCurrentThread(null)
    selectConversation(conversationId)
  }

  const getThreadMessages = (conversationId, threadId) => {
    const conversation = conversations.find(conv => conv.id === conversationId)
    if (!conversation) return []

    if (!threadId) {
      // Return main conversation messages
      return conversation.messages || []
    }

    const thread = conversation.threads?.find(t => t.id === threadId)
    if (!thread) return []

    // Get messages up to branch point from main conversation
    const branchPointIndex = conversation.messages.findIndex(msg => msg.id === thread.branchFromMessageId)
    const mainMessages = conversation.messages.slice(0, branchPointIndex + 1)

    // Add thread-specific messages
    return [...mainMessages, ...(thread.messages || [])]
  }

  const addMessageToThread = (conversationId, threadId, message) => {
    const updatedConversations = conversations.map(conv => {
      if (conv.id === conversationId) {
        if (!threadId) {
          // Add to main conversation
          const newMessage = {
            id: (conv.messages.length + 1),
            ...message,
            timestamp: new Date().toISOString(),
            threadId: null,
            parentMessageId: null
          }
          return {
            ...conv,
            messages: [...conv.messages, newMessage]
          }
        } else {
          // Add to specific thread
          const updatedThreads = (conv.threads || []).map(thread => {
            if (thread.id === threadId) {
              const newMessage = {
                id: Date.now(), // Use timestamp for thread message IDs
                ...message,
                timestamp: new Date().toISOString(),
                threadId,
                parentMessageId: thread.branchFromMessageId
              }
              return {
                ...thread,
                messages: [...(thread.messages || []), newMessage]
              }
            }
            return thread
          })
          return {
            ...conv,
            threads: updatedThreads
          }
        }
      }
      return conv
    })

    setConversations(updatedConversations)
    saveConversationsToStorage(updatedConversations)
  }

  const deleteThread = (conversationId, threadId) => {
    const updatedConversations = conversations.map(conv => {
      if (conv.id === conversationId) {
        return {
          ...conv,
          threads: (conv.threads || []).filter(thread => thread.id !== threadId)
        }
      }
      return conv
    })

    setConversations(updatedConversations)
    saveConversationsToStorage(updatedConversations)

    // If we're currently in the deleted thread, switch back to main conversation
    if (currentThread?.threadId === threadId) {
      setCurrentThread(null)
    }
  }

  const renameThread = (conversationId, threadId, newName) => {
    if (!newName.trim()) return

    const updatedConversations = conversations.map(conv => {
      if (conv.id === conversationId) {
        const updatedThreads = (conv.threads || []).map(thread => {
          if (thread.id === threadId) {
            return { ...thread, name: newName.trim() }
          }
          return thread
        })
        return { ...conv, threads: updatedThreads }
      }
      return conv
    })

    setConversations(updatedConversations)
    saveConversationsToStorage(updatedConversations)
  }

  const getCurrentMessages = () => {
    if (!currentThread) {
      // Return main conversation messages
      const conversation = conversations.find(conv => conv.id === currentConversationId)
      return conversation?.messages || []
    } else {
      // Return thread messages
      return getThreadMessages(currentThread.conversationId, currentThread.threadId)
    }
  }

  // History panel functionality
  const getFilteredConversationHistory = () => {
    let filtered = [...conversations]

    // Apply search filter
    if (historySearchQuery.trim()) {
      const query = historySearchQuery.toLowerCase()
      filtered = filtered.filter(conv => 
        conv.name.toLowerCase().includes(query) ||
        conv.preview.toLowerCase().includes(query) ||
        conv.messages.some(msg => msg.content.toLowerCase().includes(query))
      )
    }

    // Apply date filter
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const week = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
    const month = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)

    if (historyDateFilter !== 'all') {
      filtered = filtered.filter(conv => {
        const convDate = new Date(conv.createdAt)
        switch (historyDateFilter) {
          case 'today':
            return convDate >= today
          case 'week':
            return convDate >= week
          case 'month':
            return convDate >= month
          default:
            return true
        }
      })
    }

    // Sort by creation date (newest first)
    return filtered.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  }

  const getConversationStats = (conversation) => {
    const messageCount = conversation.messages.length
    const threadCount = conversation.threads?.length || 0
    const lastActivity = conversation.messages.length > 0 
      ? conversation.messages[conversation.messages.length - 1].timestamp
      : conversation.createdAt
    
    const userMessages = conversation.messages.filter(msg => msg.sender === 'user').length
    const assistantMessages = conversation.messages.filter(msg => msg.sender === 'assistant').length
    
    return {
      messageCount,
      threadCount,
      lastActivity,
      userMessages,
      assistantMessages
    }
  }

  const groupConversationsByDate = (conversations) => {
    const groups = {}
    
    conversations.forEach(conv => {
      const date = new Date(conv.createdAt)
      const dateKey = date.toDateString()
      
      if (!groups[dateKey]) {
        groups[dateKey] = []
      }
      groups[dateKey].push(conv)
    })
    
    return groups
  }

  const formatRelativeDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now - date)
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) {
      return 'Today'
    } else if (diffDays === 1) {
      return 'Yesterday'
    } else if (diffDays < 7) {
      return `${diffDays} days ago`
    } else if (diffDays < 30) {
      const weeks = Math.floor(diffDays / 7)
      return weeks === 1 ? '1 week ago' : `${weeks} weeks ago`
    } else {
      const months = Math.floor(diffDays / 30)
      return months === 1 ? '1 month ago' : `${months} months ago`
    }
  }

  // Favorites/bookmarks functionality
  const addToFavorites = (type, conversationId, messageId = null, threadId = null, note = '') => {
    const newFavorite = {
      id: Date.now(),
      type, // 'conversation' or 'message'
      conversationId,
      messageId,
      threadId,
      timestamp: new Date().toISOString(),
      note: note.trim()
    }
    
    const updatedFavorites = [...favorites, newFavorite]
    setFavorites(updatedFavorites)
    saveFavoritesToStorage(updatedFavorites)
  }

  const removeFromFavorites = (favoriteId) => {
    const updatedFavorites = favorites.filter(fav => fav.id !== favoriteId)
    setFavorites(updatedFavorites)
    saveFavoritesToStorage(updatedFavorites)
  }

  const updateFavoriteNote = (favoriteId, newNote) => {
    const updatedFavorites = favorites.map(fav => 
      fav.id === favoriteId ? { ...fav, note: newNote.trim() } : fav
    )
    setFavorites(updatedFavorites)
    saveFavoritesToStorage(updatedFavorites)
  }

  const isFavorited = (type, conversationId, messageId = null, threadId = null) => {
    return favorites.some(fav => 
      fav.type === type && 
      fav.conversationId === conversationId &&
      fav.messageId === messageId &&
      fav.threadId === threadId
    )
  }

  const getFavoriteItem = (type, conversationId, messageId = null, threadId = null) => {
    return favorites.find(fav => 
      fav.type === type && 
      fav.conversationId === conversationId &&
      fav.messageId === messageId &&
      fav.threadId === threadId
    )
  }

  const saveFavoritesToStorage = (favoritesToSave) => {
    try {
      localStorage.setItem('personaos-favorites', JSON.stringify(favoritesToSave))
    } catch (error) {
      console.warn('Failed to save favorites to localStorage:', error)
    }
  }

  const loadFavoritesFromStorage = () => {
    try {
      const saved = localStorage.getItem('personaos-favorites')
      if (saved) {
        const parsedFavorites = JSON.parse(saved)
        setFavorites(parsedFavorites)
      }
    } catch (error) {
      console.warn('Failed to load favorites from localStorage:', error)
    }
  }

  const getFavoriteDetails = (favorite) => {
    const conversation = conversations.find(conv => conv.id === favorite.conversationId)
    if (!conversation) return null

    if (favorite.type === 'conversation') {
      return {
        title: conversation.name,
        preview: conversation.preview,
        location: 'Conversation'
      }
    } else if (favorite.type === 'message') {
      let message
      if (favorite.threadId) {
        const thread = conversation.threads?.find(t => t.id === favorite.threadId)
        message = thread?.messages?.find(msg => msg.id === favorite.messageId)
      } else {
        message = conversation.messages?.find(msg => msg.id === favorite.messageId)
      }
      
      if (message) {
        return {
          title: `${message.sender === 'user' ? 'Your message' : 'Assistant response'}`,
          preview: message.content.substring(0, 100) + (message.content.length > 100 ? '...' : ''),
          location: `${conversation.name}${favorite.threadId ? ' → Thread' : ''}`
        }
      }
    }
    
    return null
  }

  const navigateToFavorite = (favorite) => {
    setActiveTab('chat')
    selectConversation(favorite.conversationId)
    
    if (favorite.threadId) {
      switchToThread(favorite.conversationId, favorite.threadId)
    } else if (favorite.type === 'conversation') {
      switchToMainConversation(favorite.conversationId)
    }
    
    // Scroll to message if it's a message favorite
    if (favorite.type === 'message' && favorite.messageId) {
      setTimeout(() => {
        const messageElement = document.getElementById(`message-${favorite.messageId}`)
        if (messageElement) {
          messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
          messageElement.classList.add('favorite-highlight')
          setTimeout(() => {
            messageElement.classList.remove('favorite-highlight')
          }, 3000)
        }
      }, 100)
    }
    
    setShowFavorites(false)
  }

  const loadConversationsFromStorage = () => {
    try {
      const saved = localStorage.getItem('personaos-conversations')
      if (saved) {
        const parsedConversations = JSON.parse(saved)
        if (parsedConversations.length > 0) {
          setConversations(parsedConversations)
          const activeConv = parsedConversations.find(conv => conv.active)
          if (activeConv) {
            setCurrentConversationId(activeConv.id)
            // Set conversation counter to be higher than the highest existing ID
            const maxId = Math.max(...parsedConversations.map(conv => conv.id))
            setConversationCounter(maxId + 1)
          }
        }
      }
    } catch (error) {
      console.warn('Failed to load conversations from localStorage:', error)
    }
  }

  // Load conversations and favorites on component mount
  useEffect(() => {
    loadConversationsFromStorage()
    loadFavoritesFromStorage()
  }, [])

  // Helper function to format message timestamps
  const formatMessageTime = (timestamp) => {
    if (!timestamp) return 'Unknown time'
    
    try {
      const date = new Date(timestamp)
      const now = new Date()
      const diffMs = now - date
      const diffMinutes = Math.floor(diffMs / 60000)
      
      if (diffMinutes < 1) return 'Just now'
      if (diffMinutes < 60) return `${diffMinutes}m ago`
      
      const diffHours = Math.floor(diffMinutes / 60)
      if (diffHours < 24) return `${diffHours}h ago`
      
      const diffDays = Math.floor(diffHours / 24)
      if (diffDays < 7) return `${diffDays}d ago`
      
      return date.toLocaleDateString()
    } catch (error) {
      return 'Unknown time'
    }
  }

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    const chatMessages = document.getElementById('chatMessages')
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight
    }
  }, [conversations, loading])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!message.trim()) return

    const startTime = Date.now()
    const userMessage = message.trim()

    // Add user message to current conversation or thread immediately
    if (currentThread) {
      addMessageToThread(currentConversationId, currentThread.threadId, {
        sender: 'user',
        content: userMessage
      })
    } else {
      addMessageToConversation(currentConversationId, {
        sender: 'user',
        content: userMessage
      })
    }

    try {
      setLoading(true)
      setError(null)
      setLastActivity(new Date())
      
      const res = await fetch(`${API_BASE_URL}/api/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      })

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }

      const data = await res.json()
      const endTime = Date.now()
      const currentResponseTime = endTime - startTime
      
      // Add assistant response to current conversation or thread
      if (currentThread) {
        addMessageToThread(currentConversationId, currentThread.threadId, {
          sender: 'assistant',
          content: data.reply
        })
      } else {
        addMessageToConversation(currentConversationId, {
          sender: 'assistant',
          content: data.reply
        })
      }
      
      setResponse(data.reply)
      setMessage('')
      setResponseTime(currentResponseTime)
      setLastActivity(new Date())
      
    } catch (err) {
      console.error('Error:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">

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
            
            {/* Status Bar - Panel Top Position */}
            {statusBarLocation === 'panel-top' && (
              <EnhancedStatusBar 
                collapsed={statusBarCollapsed}
                onToggle={toggleStatusBar}
                activeTab={activeTab}
                sidebarWidth={sidebarWidth}
                lastActivity={lastActivity}
                responseTime={responseTime}
                loading={loading}
                error={error}
                location="panel-top"
              />
            )}
            <div className="panel-controls">
              <button 
                className="panel-control-btn" 
                onClick={toggleTheme}
                title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              >
                {theme === 'dark' ? '☀️' : '🌙'}
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
                  className={`nav-tab ${activeTab === 'models' ? 'active' : ''}`}
                  onClick={() => setActiveTab('models')}
                >
                  Models
                </button>
                <button 
                  className={`nav-tab ${activeTab === 'history' ? 'active' : ''}`}
                  onClick={() => setActiveTab('history')}
                >
                  History
                </button>
                <button 
                  className={`nav-tab ${activeTab === 'favorites' ? 'active' : ''}`}
                  onClick={() => setActiveTab('favorites')}
                >
                  Favorites
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

                {/* Search Interface */}
                <div className="search-section">
                  <div className="search-input-container">
                    <input
                      type="text"
                      placeholder="Search conversations and messages..."
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(e.target.value)}
                      className="search-input"
                    />
                    {searchQuery && (
                      <button className="search-clear-btn" onClick={clearSearch}>
                        ✕
                      </button>
                    )}
                    {isSearching && (
                      <div className="search-loading">🔍</div>
                    )}
                  </div>
                  
                  {searchQuery && (
                    <div className="search-filters">
                      <button 
                        className={`search-filter-btn ${searchType === 'all' ? 'active' : ''}`}
                        onClick={() => handleSearchTypeChange('all')}
                      >
                        All
                      </button>
                      <button 
                        className={`search-filter-btn ${searchType === 'conversations' ? 'active' : ''}`}
                        onClick={() => handleSearchTypeChange('conversations')}
                      >
                        Conversations
                      </button>
                      <button 
                        className={`search-filter-btn ${searchType === 'messages' ? 'active' : ''}`}
                        onClick={() => handleSearchTypeChange('messages')}
                      >
                        Messages
                      </button>
                    </div>
                  )}
                </div>

                {/* Search Results */}
                {showSearchResults && searchResults.length > 0 && (
                  <div className="search-results">
                    <div className="search-results-header">
                      <span>Found {searchResults.length} result{searchResults.length !== 1 ? 's' : ''}</span>
                    </div>
                    {searchResults.map((result) => (
                      <div 
                        key={result.id}
                        className={`search-result-item ${result.type}`}
                        onClick={() => navigateToSearchResult(result)}
                      >
                        <div className="search-result-type">
                          {result.type === 'conversation' ? '💬' : '📝'}
                        </div>
                        <div className="search-result-content">
                          <div className="search-result-title">{result.title}</div>
                          <div className="search-result-preview">{result.preview}</div>
                          {result.type === 'message' && (
                            <div className="search-result-location">
                              in "{result.conversationName}"
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {showSearchResults && searchResults.length === 0 && searchQuery && !isSearching && (
                  <div className="search-no-results">
                    <div className="no-results-icon">🔍</div>
                    <div className="no-results-text">No results found for "{searchQuery}"</div>
                    <div className="no-results-hint">Try different keywords or check spelling</div>
                  </div>
                )}

                <div className="conversation-list">
                  {!showSearchResults && conversations.map((conversation) => (
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
                          title="Rename"
                          onClick={(e) => {
                            e.stopPropagation()
                            const newName = prompt('Enter new conversation name:', conversation.name)
                            if (newName) {
                              renameConversation(conversation.id, newName)
                            }
                          }}
                        >
                          ✏️
                        </button>
                        <button 
                          className="action-btn delete" 
                          title="Delete"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (confirm('Are you sure you want to delete this conversation?')) {
                              deleteConversation(conversation.id)
                            }
                          }}
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Threads Section */}
                {(() => {
                  const currentConversation = conversations.find(conv => conv.id === currentConversationId)
                  const threads = currentConversation?.threads || []
                  
                  if (threads.length === 0) return null
                  
                  return (
                    <div className="threads-section">
                      <div className="threads-header">
                        <div className="threads-title">Threads</div>
                      </div>
                      
                      <div className="threads-list">
                        {threads.map((thread) => (
                          <div 
                            key={thread.id}
                            className={`thread-item ${currentThread?.threadId === thread.id ? 'active' : ''}`}
                            onClick={() => switchToThread(currentConversationId, thread.id)}
                          >
                            <div className="thread-info">
                              <div className="thread-name">{thread.name}</div>
                              <div className="thread-meta">
                                {thread.messages?.length || 0} messages • Created {formatMessageTime(thread.createdAt)}
                              </div>
                            </div>
                            <div className="thread-actions">
                              <button 
                                className="action-btn" 
                                title="Rename thread"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  const newName = prompt('Enter new thread name:', thread.name)
                                  if (newName) {
                                    renameThread(currentConversationId, thread.id, newName)
                                  }
                                }}
                              >
                                ✏️
                              </button>
                              <button 
                                className="action-btn delete" 
                                title="Delete thread"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  if (confirm('Are you sure you want to delete this thread?')) {
                                    deleteThread(currentConversationId, thread.id)
                                  }
                                }}
                              >
                                🗑️
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })()}
              </div>
              )}

              {/* Models Content */}
              {activeTab === 'models' && (
                <ModelManagementPanel />
              )}

              {/* History Content */}
              {activeTab === 'history' && (
                <div className="history-section">
                  {/* History Controls */}
                  <div className="history-controls">
                    <div className="history-search">
                      <input
                        type="text"
                        placeholder="Search conversation history..."
                        value={historySearchQuery}
                        onChange={(e) => setHistorySearchQuery(e.target.value)}
                        className="search-input"
                      />
                    </div>
                    
                    <div className="history-filters">
                      <select 
                        value={historyDateFilter} 
                        onChange={(e) => setHistoryDateFilter(e.target.value)}
                        className="filter-select"
                      >
                        <option value="all">All Time</option>
                        <option value="today">Today</option>
                        <option value="week">This Week</option>
                        <option value="month">This Month</option>
                      </select>
                      
                      <div className="view-mode-selector">
                        <button
                          className={`view-btn ${historyViewMode === 'timeline' ? 'active' : ''}`}
                          onClick={() => setHistoryViewMode('timeline')}
                          title="Timeline View"
                        >
                          📅
                        </button>
                        <button
                          className={`view-btn ${historyViewMode === 'grid' ? 'active' : ''}`}
                          onClick={() => setHistoryViewMode('grid')}
                          title="Grid View"
                        >
                          ⚏
                        </button>
                        <button
                          className={`view-btn ${historyViewMode === 'list' ? 'active' : ''}`}
                          onClick={() => setHistoryViewMode('list')}
                          title="List View"
                        >
                          ☰
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* History Content */}
                  <div className={`history-content history-${historyViewMode}`}>
                    {(() => {
                      const filteredConversations = getFilteredConversationHistory()
                      
                      if (filteredConversations.length === 0) {
                        return (
                          <div className="empty-history">
                            <div className="empty-icon">📚</div>
                            <div className="empty-title">No conversations found</div>
                            <div className="empty-subtitle">
                              {historySearchQuery ? 'Try different search terms' : 'Start chatting to build your history'}
                            </div>
                          </div>
                        )
                      }

                      if (historyViewMode === 'timeline') {
                        const groupedConversations = groupConversationsByDate(filteredConversations)
                        
                        return (
                          <div className="timeline-view">
                            {Object.entries(groupedConversations).map(([dateKey, conversations]) => (
                              <div key={dateKey} className="timeline-group">
                                <div className="timeline-date">{formatRelativeDate(conversations[0].createdAt)}</div>
                                <div className="timeline-conversations">
                                  {conversations.map((conversation) => {
                                    const stats = getConversationStats(conversation)
                                    return (
                                      <div key={conversation.id} className="timeline-conversation-card">
                                        <div className="card-header">
                                          <div className="card-title" onClick={() => {
                                            setActiveTab('chat')
                                            selectConversation(conversation.id)
                                          }}>
                                            {conversation.name}
                                          </div>
                                          <div className="card-time">
                                            {formatMessageTime(conversation.createdAt)}
                                          </div>
                                        </div>
                                        <div className="card-preview">{conversation.preview}</div>
                                        <div className="card-stats">
                                          <span className="stat">💬 {stats.messageCount}</span>
                                          {stats.threadCount > 0 && <span className="stat">🧵 {stats.threadCount}</span>}
                                          <span className="stat">👤 {stats.userMessages}</span>
                                          <span className="stat">🤖 {stats.assistantMessages}</span>
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              </div>
                            ))}
                          </div>
                        )
                      }

                      if (historyViewMode === 'grid') {
                        return (
                          <div className="grid-view">
                            {filteredConversations.map((conversation) => {
                              const stats = getConversationStats(conversation)
                              return (
                                <div key={conversation.id} className="grid-conversation-card">
                                  <div className="card-header">
                                    <div className="card-title" onClick={() => {
                                      setActiveTab('chat')
                                      selectConversation(conversation.id)
                                    }}>
                                      {conversation.name}
                                    </div>
                                  </div>
                                  <div className="card-preview">{conversation.preview}</div>
                                  <div className="card-meta">
                                    <div className="card-date">{formatRelativeDate(conversation.createdAt)}</div>
                                    <div className="card-stats">
                                      <span className="stat">💬 {stats.messageCount}</span>
                                      {stats.threadCount > 0 && <span className="stat">🧵 {stats.threadCount}</span>}
                                    </div>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )
                      }

                      // List view
                      return (
                        <div className="list-view">
                          {filteredConversations.map((conversation) => {
                            const stats = getConversationStats(conversation)
                            return (
                              <div key={conversation.id} className="list-conversation-item">
                                <div className="list-main">
                                  <div className="list-title" onClick={() => {
                                    setActiveTab('chat')
                                    selectConversation(conversation.id)
                                  }}>
                                    {conversation.name}
                                  </div>
                                  <div className="list-preview">{conversation.preview}</div>
                                </div>
                                <div className="list-meta">
                                  <div className="list-date">{formatRelativeDate(conversation.createdAt)}</div>
                                  <div className="list-stats">
                                    💬 {stats.messageCount}
                                    {stats.threadCount > 0 && ` • 🧵 ${stats.threadCount}`}
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )
                    })()}
                  </div>
                </div>
              )}

              {/* Favorites Content */}
              {activeTab === 'favorites' && (
                <div className="favorites-section">
                  <div className="favorites-header">
                    <div className="favorites-title">
                      Bookmarked Items ({favorites.length})
                    </div>
                    {favorites.length > 0 && (
                      <button 
                        className="clear-favorites-btn"
                        onClick={() => {
                          if (confirm('Are you sure you want to clear all favorites?')) {
                            setFavorites([])
                            saveFavoritesToStorage([])
                          }
                        }}
                      >
                        Clear All
                      </button>
                    )}
                  </div>

                  <div className="favorites-content">
                    {favorites.length === 0 ? (
                      <div className="empty-favorites">
                        <div className="empty-icon">⭐</div>
                        <div className="empty-title">No bookmarks yet</div>
                        <div className="empty-subtitle">
                          Star messages and conversations to save them here for quick access
                        </div>
                      </div>
                    ) : (
                      <div className="favorites-list">
                        {favorites
                          .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                          .map((favorite) => {
                            const details = getFavoriteDetails(favorite)
                            if (!details) return null

                            return (
                              <div key={favorite.id} className="favorite-item">
                                <div className="favorite-icon">
                                  {favorite.type === 'conversation' ? '💬' : '📝'}
                                </div>
                                <div className="favorite-content">
                                  <div className="favorite-header">
                                    <div 
                                      className="favorite-title"
                                      onClick={() => navigateToFavorite(favorite)}
                                    >
                                      {details.title}
                                    </div>
                                    <div className="favorite-time">
                                      {formatRelativeDate(favorite.timestamp)}
                                    </div>
                                  </div>
                                  <div className="favorite-preview">{details.preview}</div>
                                  <div className="favorite-location">{details.location}</div>
                                  {favorite.note && (
                                    <div className="favorite-note">
                                      <span className="note-label">Note:</span> {favorite.note}
                                    </div>
                                  )}
                                </div>
                                <div className="favorite-actions">
                                  <button 
                                    className="action-btn"
                                    title="Edit note"
                                    onClick={() => {
                                      const newNote = prompt('Edit note:', favorite.note || '')
                                      if (newNote !== null) {
                                        updateFavoriteNote(favorite.id, newNote)
                                      }
                                    }}
                                  >
                                    ✏️
                                  </button>
                                  <button 
                                    className="action-btn delete"
                                    title="Remove from favorites"
                                    onClick={() => {
                                      if (confirm('Remove this item from favorites?')) {
                                        removeFromFavorites(favorite.id)
                                      }
                                    }}
                                  >
                                    🗑️
                                  </button>
                                </div>
                              </div>
                            )
                          })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Status Bar - Panel Bottom Position */}
              {statusBarLocation === 'panel-bottom' && (
                <EnhancedStatusBar 
                  collapsed={statusBarCollapsed}
                  onToggle={toggleStatusBar}
                  activeTab={activeTab}
                  sidebarWidth={sidebarWidth}
                  lastActivity={lastActivity}
                  responseTime={responseTime}
                  loading={loading}
                  error={error}
                  location="panel-bottom"
                />
              )}
            </div>
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
              <button 
                className="panel-control-btn settings-btn"
                onClick={() => {
                  setActiveTab('settings')
                  // Auto-expand sidebar if collapsed
                  if (sidebarCollapsed) {
                    setSidebarCollapsed(false)
                  }
                }}
                title="Open Settings"
              >
                ⚙️
              </button>
              <LayoutDropdown 
                currentLayout={currentLayout}
                onLayoutChange={applyLayout}
              />
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
            {/* Settings View */}
            {activeTab === 'settings' ? (
              <SettingsPanel 
                statusBarLocation={statusBarLocation}
                changeStatusBarLocation={changeStatusBarLocation}
              />
            ) : (
              <>
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

                {/* Thread Navigation */}
                {currentThread && (
                  <div className="thread-navigation">
                    <div className="thread-breadcrumb">
                      <button 
                        className="breadcrumb-btn" 
                        onClick={() => switchToMainConversation(currentConversationId)}
                      >
                        Main Conversation
                      </button>
                      <span className="breadcrumb-separator">→</span>
                      <span className="current-thread">
                        {conversations.find(conv => conv.id === currentConversationId)?.threads?.find(t => t.id === currentThread.threadId)?.name || 'Thread'}
                      </span>
                    </div>
                  </div>
                )}

                {/* Chat Messages */}
                <div className="chat-messages" id="chatMessages">
                  {(() => {
                    const currentMessages = getCurrentMessages();
                    
                    if (!currentMessages || currentMessages.length === 0) {
                      return (
                        <div className="empty-state">
                          <div className="empty-icon">💬</div>
                          <div className="empty-title">
                            {currentThread ? 'Start this thread' : 'Start a new conversation'}
                          </div>
                          <div className="empty-subtitle">Ask me anything! I'm here to help with coding, questions, creative tasks, and more.</div>
                        </div>
                      );
                    }

                    return currentMessages.map((msg, index) => {
                      const conversation = conversations.find(conv => conv.id === currentConversationId);
                      const isLastMainMessage = currentThread && conversation?.messages && 
                                                 index === conversation.messages.findIndex(m => m.id === currentThread.branchPoint);
                      
                      return (
                        <div key={msg.id} id={`message-${msg.id}`} className={`message ${msg.sender}`}>
                          <div className="message-header">
                            {msg.sender === 'user' ? (
                              <>
                                <span className="message-time">{formatMessageTime(msg.timestamp)}</span>
                                <span>You</span>
                                <div className="message-avatar avatar-user">U</div>
                              </>
                            ) : (
                              <>
                                <div className="message-avatar avatar-assistant">AI</div>
                                <span>PersonaOS Assistant</span>
                                <span className="message-time">{formatMessageTime(msg.timestamp)}</span>
                              </>
                            )}
                          </div>
                          <div className="message-bubble">
                            {msg.content}
                          </div>
                          
                          {/* Message Actions */}
                          <div className="message-actions">
                            {/* Favorite button */}
                            <button 
                              className={`action-btn favorite-btn ${isFavorited('message', currentConversationId, msg.id, currentThread?.threadId) ? 'favorited' : ''}`}
                              title={isFavorited('message', currentConversationId, msg.id, currentThread?.threadId) ? "Remove from favorites" : "Add to favorites"}
                              onClick={() => {
                                const isCurrentlyFavorited = isFavorited('message', currentConversationId, msg.id, currentThread?.threadId);
                                if (isCurrentlyFavorited) {
                                  const favoriteItem = getFavoriteItem('message', currentConversationId, msg.id, currentThread?.threadId);
                                  if (favoriteItem) {
                                    removeFromFavorites(favoriteItem.id);
                                  }
                                } else {
                                  const note = prompt('Add a note (optional):');
                                  if (note !== null) { // User didn't cancel
                                    addToFavorites('message', currentConversationId, msg.id, currentThread?.threadId, note);
                                  }
                                }
                              }}
                            >
                              {isFavorited('message', currentConversationId, msg.id, currentThread?.threadId) ? '⭐' : '☆'}
                            </button>
                            
                            {/* Threading button */}
                            {!currentThread && (
                              <button 
                                className="action-btn thread-btn"
                                title="Create thread from this message"
                                onClick={() => {
                                  const threadName = prompt('Enter thread name:', `Thread from ${msg.sender}`);
                                  if (threadName) {
                                    createThread(currentConversationId, msg.id, threadName);
                                  }
                                }}
                              >
                                🧵
                              </button>
                            )}
                            {isLastMainMessage && (
                              <div className="branch-indicator">
                                <span className="branch-text">Thread starts here</span>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    });
                  })()}
                  
                  {/* Typing indicator */}
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

                  {/* Error message */}
                  {error && (
                    <div className="setting-warning" style={{ margin: '20px' }}>
                      <strong>Error:</strong> {error}
                    </div>
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

            {/* Status Bar - Under Chat Position */}
            {statusBarLocation === 'under-chat' && (
              <EnhancedStatusBar 
                collapsed={statusBarCollapsed}
                onToggle={toggleStatusBar}
                activeTab={activeTab}
                sidebarWidth={sidebarWidth}
                lastActivity={lastActivity}
                responseTime={responseTime}
                loading={loading}
                error={error}
                location="under-chat"
              />
            )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Status Bar - Global Bottom Position */}
      {statusBarLocation === 'global-bottom' && (
        <EnhancedStatusBar 
          collapsed={statusBarCollapsed}
          onToggle={toggleStatusBar}
          activeTab={activeTab}
          sidebarWidth={sidebarWidth}
          lastActivity={lastActivity}
          responseTime={responseTime}
          loading={loading}
          error={error}
          location="global-bottom"
        />
      )}
    </div>
  )
}

// Enhanced Status Bar Component
function EnhancedStatusBar({ collapsed, onToggle, activeTab, sidebarWidth, lastActivity, responseTime, loading, error, location = 'global-bottom' }) {
  const [currentModel, setCurrentModel] = useState(null)
  const [backendStatus, setBackendStatus] = useState('checking')

  const API_BASE_URL = 'http://localhost:8000'

  useEffect(() => {
    checkBackendStatus()
    loadCurrentModel()
    
    // Check backend status every 30 seconds
    const interval = setInterval(checkBackendStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkBackendStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/health`, { 
        method: 'GET',
        signal: AbortSignal.timeout(5000) // 5 second timeout
      })
      setBackendStatus(response.ok ? 'online' : 'error')
    } catch (err) {
      setBackendStatus('offline')
    }
  }

  const loadCurrentModel = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/models`)
      if (response.ok) {
        const data = await response.json()
        setCurrentModel(data.current_model)
      }
    } catch (err) {
      // Silently fail if models endpoint is unavailable
    }
  }

  const formatLastActivity = (date) => {
    const now = new Date()
    const diff = now - date
    const minutes = Math.floor(diff / 60000)
    
    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    return date.toLocaleDateString()
  }

  const formatResponseTime = (ms) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'var(--success)'
      case 'offline': return 'var(--error)'
      case 'error': return 'var(--warning)'
      default: return 'var(--text-muted)'
    }
  }

  const getStatusText = (status) => {
    switch (status) {
      case 'online': return 'Connected'
      case 'offline': return 'Offline'
      case 'error': return 'Error'
      default: return 'Checking...'
    }
  }

  const getContextualInfo = () => {
    switch (activeTab) {
      case 'chat':
        return {
          primary: currentModel ? `Model: ${currentModel}` : 'No model active',
          secondary: responseTime ? `Response: ${formatResponseTime(responseTime)}` : 'No recent activity'
        }
      case 'settings':
        return {
          primary: 'Configuration',
          secondary: error ? 'Configuration error' : 'Settings ready'
        }
      case 'models':
        return {
          primary: 'Model Management',
          secondary: currentModel ? `Active: ${currentModel}` : 'No active model'
        }
      default:
        return {
          primary: 'PersonaOS',
          secondary: 'Ready'
        }
    }
  }

  const contextInfo = getContextualInfo()

  if (collapsed) {
    return (
      <div className={`status-bar collapsed status-bar-${location}`}>
        <button 
          className="status-toggle-btn"
          onClick={onToggle}
          title="Expand status bar"
        >
          <span className="toggle-icon">▲</span>
        </button>
      </div>
    )
  }

  return (
    <div className={`status-bar expanded status-bar-${location}`}>
      <div className="status-left">
        <div className="status-item">
          <div 
            className="status-indicator-small"
            style={{ backgroundColor: getStatusColor(backendStatus) }}
          ></div>
          <span>{getStatusText(backendStatus)}</span>
        </div>
        
        <div className="status-item">
          <span className="status-label">Status:</span>
          <span>{contextInfo.primary}</span>
        </div>
        
        <div className="status-item">
          <span className="status-label">Activity:</span>
          <span>{formatLastActivity(lastActivity)}</span>
        </div>
      </div>
      
      <div className="status-center">
        {loading && (
          <div className="status-item loading">
            <div className="loading-spinner"></div>
            <span>Processing...</span>
          </div>
        )}
      </div>
      
      <div className="status-right">
        <div className="status-item">
          <span>{contextInfo.secondary}</span>
        </div>
        
        <div className="status-item">
          <span className="version">PersonaOS v0.1.0</span>
        </div>
        
        <button 
          className="status-toggle-btn"
          onClick={onToggle}
          title="Collapse status bar"
        >
          <span className="toggle-icon">▼</span>
        </button>
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
  const dropdownRef = useRef(null)

  const API_BASE_URL = 'http://localhost:8000'

  useEffect(() => {
    loadModels()
    const interval = setInterval(loadModels, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
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
      const modelList = data.models || []
      
      // Add some mock external models for demonstration
      const allModels = [
        ...modelList.map(model => ({
          ...model,
          provider: 'Ollama',
          status: model.name === data.current_model ? 'active' : 'available'
        })),
        {
          name: 'GPT-4',
          provider: 'OpenAI',
          status: 'unavailable', // Requires API key
          description: 'Most capable GPT-4 model'
        },
        {
          name: 'Claude 3.5 Sonnet',
          provider: 'Anthropic', 
          status: 'unavailable', // Requires API key
          description: 'Latest Claude model'
        },
        {
          name: 'Gemini Pro',
          provider: 'Google',
          status: 'unavailable', // Requires API key
          description: "Google's advanced model"
        }
      ]
      
      setModels(allModels)
      setSelectedModel(data.current_model || allModels[0]?.name || 'No models available')
      
    } catch (err) {
      console.error('Error loading models:', err)
      setError(`Failed to load models: ${err.message}`)
      setModels([
        { name: 'Offline Mode', provider: 'Local', status: 'available', description: 'No backend connection' }
      ])
      setSelectedModel('Offline Mode')
    } finally {
      setLoading(false)
    }
  }

  const handleModelSelect = async (model) => {
    if (model.status === 'unavailable') {
      alert(`${model.name} requires an API key. Please configure it in Settings.`)
      setIsOpen(false)
      return
    }

    if (model.provider === 'Ollama') {
      try {
        const response = await fetch(`${API_BASE_URL}/api/models/load`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model_name: model.name })
        })
        
        if (response.ok) {
          setSelectedModel(model.name)
          // Refresh models to update status
          setTimeout(loadModels, 1000)
        } else {
          throw new Error(`Failed to load model: ${response.status}`)
        }
      } catch (error) {
        console.error('Error loading model:', error)
        alert(`Failed to load ${model.name}: ${error.message}`)
      }
    } else {
      setSelectedModel(model.name)
    }
    
    setIsOpen(false)
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'var(--success)'
      case 'available': return 'var(--info)'
      case 'loading': return 'var(--warning)'
      case 'unavailable': return 'var(--error)'
      default: return 'var(--text-muted)'
    }
  }

  const getStatusText = (status) => {
    switch (status) {
      case 'active': return 'Active'
      case 'available': return 'Available'
      case 'loading': return 'Loading'
      case 'unavailable': return 'API Key Required'
      default: return 'Unknown'
    }
  }

  return (
    <div className={`dropdown ${isOpen ? 'open' : ''}`} ref={dropdownRef}>
      <div 
        className="dropdown-trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{selectedModel || 'Select Model'}</span>
        <span>▼</span>
      </div>
      
      <div className="dropdown-content">
        {loading && (
          <div className="dropdown-item">
            <span>Loading models...</span>
          </div>
        )}
        
        {!loading && models.length === 0 && (
          <div className="dropdown-item">
            <span>No models available</span>
          </div>
        )}
        
        {!loading && models.map((model, index) => (
          <div
            key={`${model.provider}-${model.name}-${index}`}
            className={`dropdown-item ${model.name === selectedModel ? 'selected' : ''}`}
            onClick={() => handleModelSelect(model)}
          >
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <span>{model.provider} - {model.name}</span>
              {model.description && (
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {model.description}
                </span>
              )}
            </div>
            <span 
              className="model-status"
              style={{ 
                background: getStatusColor(model.status) + '20',
                color: getStatusColor(model.status),
                fontSize: 'var(--text-xs)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontWeight: 'var(--font-medium)'
              }}
            >
              {getStatusText(model.status)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Model Management Panel Component
function ModelManagementPanel() {
  const [models, setModels] = useState([])
  const [currentModel, setCurrentModel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState({})
  const [error, setError] = useState(null)
  const [successMessage, setSuccessMessage] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [newModelName, setNewModelName] = useState('')
  const [showDownloadForm, setShowDownloadForm] = useState(false)

  const API_BASE_URL = 'http://localhost:8000'

  useEffect(() => {
    loadModels()
    // Refresh models every 30 seconds
    const interval = setInterval(loadModels, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadModels = async () => {
    try {
      setError(null)
      
      const response = await fetch(`${API_BASE_URL}/api/models`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setModels(data.models || [])
      setCurrentModel(data.current_model)
      
    } catch (err) {
      console.error('Error loading models:', err)
      setError(`Failed to load models: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleModelAction = async (action, modelName) => {
    try {
      setActionLoading(prev => ({ ...prev, [modelName]: action }))
      setError(null)
      setSuccessMessage('')

      let url, method, body
      
      switch (action) {
        case 'load':
          url = `${API_BASE_URL}/api/models/load`
          method = 'POST'
          body = JSON.stringify({ model_name: modelName })
          break
        case 'remove':
          url = `${API_BASE_URL}/api/models/${modelName}`
          method = 'DELETE'
          break
        case 'download':
          url = `${API_BASE_URL}/api/models/${modelName}/download`
          method = 'POST'
          break
        default:
          throw new Error('Unknown action')
      }

      const response = await fetch(url, {
        method,
        headers: method === 'POST' ? { 'Content-Type': 'application/json' } : {},
        body: method === 'POST' ? body : undefined
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Failed to ${action} model`)
      }

      const result = await response.json()
      setSuccessMessage(result.message)
      
      // Refresh models list
      await loadModels()
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(''), 3000)
      
    } catch (err) {
      console.error(`Error ${action} model:`, err)
      setError(`Failed to ${action} model: ${err.message}`)
    } finally {
      setActionLoading(prev => ({ ...prev, [modelName]: null }))
    }
  }

  const handleDownloadNewModel = async () => {
    if (!newModelName.trim()) return
    
    await handleModelAction('download', newModelName.trim())
    setNewModelName('')
    setShowDownloadForm(false)
  }

  const filteredModels = models.filter(model =>
    model.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getStatusColor = (model) => {
    if (model.name === currentModel) return 'var(--success)'
    return model.status === 'available' ? 'var(--info)' : 'var(--text-muted)'
  }

  const getStatusText = (model) => {
    if (model.name === currentModel) return 'Active'
    return model.status === 'available' ? 'Available' : 'Loading'
  }

  if (loading) {
    return (
      <div className="conversation-section">
        <div className="conversation-header">
          <div className="conversation-title">Model Management</div>
        </div>
        <div className="settings-content">
          <div className="empty-state">
            <div className="empty-icon">📦</div>
            <div className="empty-title">Loading Models...</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="conversation-section">
      <div className="conversation-header">
        <div className="conversation-title">Model Management</div>
        <button 
          className="new-conversation-btn"
          onClick={() => setShowDownloadForm(!showDownloadForm)}
        >
          + Download
        </button>
      </div>

      <div className="model-management-content">
        {/* Status Messages */}
        {error && (
          <div className="setting-error">
            <strong>Error:</strong> {error}
          </div>
        )}
        
        {successMessage && (
          <div className="setting-success">
            <strong>Success:</strong> {successMessage}
          </div>
        )}

        {/* Download New Model Form */}
        {showDownloadForm && (
          <div className="download-model-form">
            <div className="form-row">
              <input
                type="text"
                className="input"
                value={newModelName}
                onChange={(e) => setNewModelName(e.target.value)}
                placeholder="Enter model name (e.g., llama2, codellama)"
                onKeyPress={(e) => e.key === 'Enter' && handleDownloadNewModel()}
              />
              <button 
                className="btn btn-primary"
                onClick={handleDownloadNewModel}
                disabled={!newModelName.trim()}
              >
                Download
              </button>
              <button 
                className="btn btn-secondary"
                onClick={() => setShowDownloadForm(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Search Bar */}
        <div className="model-search">
          <input
            type="text"
            className="input search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search models..."
          />
        </div>

        {/* Current Model Status */}
        {currentModel && (
          <div className="current-model-status">
            <div className="status-icon">🤖</div>
            <div className="status-text">
              <strong>Currently Active:</strong> {currentModel}
            </div>
          </div>
        )}

        {/* Models List */}
        <div className="models-grid">
          {filteredModels.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📦</div>
              <div className="empty-title">No Models Found</div>
              <div className="empty-subtitle">
                {searchTerm ? 'Try a different search term' : 'Download a model to get started'}
              </div>
            </div>
          ) : (
            filteredModels.map((model) => (
              <div key={model.name} className="model-card">
                <div className="model-header">
                  <div className="model-info">
                    <div className="model-name">{model.name}</div>
                    <div className="model-details">
                      {model.size && <span className="model-size">{model.size}</span>}
                      {model.family && <span className="model-family">{model.family}</span>}
                    </div>
                  </div>
                  <div 
                    className="model-status-badge"
                    style={{ color: getStatusColor(model) }}
                  >
                    {getStatusText(model)}
                  </div>
                </div>

                <div className="model-metadata">
                  {model.modified && (
                    <div className="metadata-item">
                      <span className="metadata-label">Modified:</span>
                      <span className="metadata-value">{model.modified}</span>
                    </div>
                  )}
                  {model.format && (
                    <div className="metadata-item">
                      <span className="metadata-label">Format:</span>
                      <span className="metadata-value">{model.format}</span>
                    </div>
                  )}
                </div>

                <div className="model-actions">
                  <button
                    className={`btn btn-primary ${model.name === currentModel ? 'btn-active' : ''}`}
                    onClick={() => handleModelAction('load', model.name)}
                    disabled={actionLoading[model.name] === 'load' || model.name === currentModel}
                  >
                    {actionLoading[model.name] === 'load' ? 'Loading...' : 
                     model.name === currentModel ? 'Active' : 'Load'}
                  </button>
                  
                  <button
                    className="btn btn-secondary btn-danger"
                    onClick={() => handleModelAction('remove', model.name)}
                    disabled={actionLoading[model.name] === 'remove'}
                  >
                    {actionLoading[model.name] === 'remove' ? 'Removing...' : 'Remove'}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// Status Bar Location Selector Component
function StatusBarLocationSelector({ currentLocation, onLocationChange }) {
  const locations = [
    { id: 'under-chat', name: 'Under Chat', description: 'Below chat input area (Recommended)' },
    { id: 'panel-bottom', name: 'Panel Bottom', description: 'Bottom of current panel' },
    { id: 'global-bottom', name: 'Global Bottom', description: 'Bottom of entire application' },
    { id: 'panel-top', name: 'Panel Top', description: 'Top of sidebar panel' },
    { id: 'hidden', name: 'Hidden', description: 'Hide status bar completely' }
  ]

  return (
    <div className="status-location-selector">
      <select 
        className="input"
        value={currentLocation}
        onChange={(e) => onLocationChange(e.target.value)}
      >
        {locations.map((location) => (
          <option key={location.id} value={location.id}>
            {location.name} - {location.description}
          </option>
        ))}
      </select>
      
      <div className="location-preview">
        <span className="preview-label">Current:</span>
        <span className="preview-value">
          {locations.find(loc => loc.id === currentLocation)?.name || 'Unknown'}
        </span>
      </div>
    </div>
  )
}

// Settings Panel Component
function SettingsPanel({ statusBarLocation, changeStatusBarLocation }) {
  const [activeSettingsTab, setActiveSettingsTab] = useState('llm')
  const [configData, setConfigData] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [successMessage, setSuccessMessage] = useState('')

  const API_BASE_URL = 'http://localhost:8000'

  const settingsTabs = [
    { id: 'llm', name: 'LLM Config', icon: '🤖' },
    { id: 'interface', name: 'Interface', icon: '🎨' },
    { id: 'audio', name: 'Audio', icon: '🔊' },
    { id: 'privacy', name: 'Privacy', icon: '🔒' },
    { id: 'api', name: 'API Keys', icon: '🔑' },
    { id: 'dev', name: 'Developer', icon: '⚙️' }
  ]

  useEffect(() => {
    loadConfiguration()
  }, [])

  const loadConfiguration = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Load from localStorage first
      const localSettings = loadFromLocalStorage()
      
      try {
        // Try to load from backend
        const response = await fetch(`${API_BASE_URL}/api/setup/defaults`)
        if (response.ok) {
          const data = await response.json()
          // Merge backend settings with localStorage settings (localStorage takes priority)
          const mergedSettings = { ...data.current_values, ...localSettings }
          setConfigData(mergedSettings)
        } else {
          // Backend unavailable, use localStorage only
          setConfigData(localSettings)
        }
      } catch (backendError) {
        // Backend unavailable, use localStorage only
        console.warn('Backend unavailable, using localStorage settings:', backendError)
        setConfigData(localSettings)
      }
      
    } catch (err) {
      console.error('Error loading configuration:', err)
      setError(`Failed to load configuration: ${err.message}`)
      // Fallback to localStorage if everything fails
      setConfigData(loadFromLocalStorage())
    } finally {
      setLoading(false)
    }
  }

  const saveConfiguration = async (updates) => {
    try {
      setSaving(true)
      setError(null)
      setSuccessMessage('')
      
      const response = await fetch(`${API_BASE_URL}/api/setup/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ config: updates }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setSuccessMessage('Configuration saved successfully!')
      setConfigData(prev => ({ ...prev, ...updates }))
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(''), 3000)
      
    } catch (err) {
      console.error('Error saving configuration:', err)
      setError(`Failed to save configuration: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleInputChange = (key, value) => {
    const updates = { [key]: value }
    setConfigData(prev => ({ ...prev, ...updates }))
    
    // Save to localStorage immediately
    saveToLocalStorage(updates)
    
    // Auto-save to backend after 1 second delay
    setTimeout(() => {
      saveConfiguration(updates)
    }, 1000)
  }

  const saveToLocalStorage = (updates) => {
    try {
      const existingSettings = JSON.parse(localStorage.getItem('personaos-settings') || '{}')
      const newSettings = { ...existingSettings, ...updates }
      localStorage.setItem('personaos-settings', JSON.stringify(newSettings))
    } catch (error) {
      console.warn('Failed to save settings to localStorage:', error)
    }
  }

  const loadFromLocalStorage = () => {
    try {
      const savedSettings = localStorage.getItem('personaos-settings')
      return savedSettings ? JSON.parse(savedSettings) : {}
    } catch (error) {
      console.warn('Failed to load settings from localStorage:', error)
      return {}
    }
  }

  if (loading) {
    return (
      <div className="conversation-section">
        <div className="conversation-header">
          <div className="conversation-title">Settings</div>
        </div>
        <div className="settings-content">
          <div className="empty-state">
            <div className="empty-icon">⚙️</div>
            <div className="empty-title">Loading Configuration...</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="conversation-section">
      <div className="conversation-header">
        <div className="conversation-title">Settings</div>
      </div>
      
      {/* Settings Tabs */}
      <div className="settings-tabs">
        {settingsTabs.map((tab) => (
          <button
            key={tab.id}
            className={`settings-tab ${activeSettingsTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveSettingsTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-name">{tab.name}</span>
          </button>
        ))}
      </div>

      <div className="settings-content">
        {/* Status Messages */}
        {error && (
          <div className="setting-error">
            <strong>Error:</strong> {error}
          </div>
        )}
        
        {successMessage && (
          <div className="setting-success">
            <strong>Success:</strong> {successMessage}
          </div>
        )}

        {/* LLM Configuration */}
        {activeSettingsTab === 'llm' && (
          <ConfigSection
            title="🤖 LLM Configuration"
            description="Configure your language model provider and settings"
          >
            <SettingItem
              title="LLM Provider"
              description="Choose your language model backend"
              control={
                <select 
                  className="input"
                  value={configData.LLM_PROVIDER || 'ollama'}
                  onChange={(e) => handleInputChange('LLM_PROVIDER', e.target.value)}
                >
                  <option value="ollama">Ollama (Local)</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              }
            />
            
            <SettingItem
              title="Ollama Model"
              description="Default model name for Ollama"
              control={
                <input
                  type="text"
                  className="input"
                  value={configData.OLLAMA_MODEL || ''}
                  onChange={(e) => handleInputChange('OLLAMA_MODEL', e.target.value)}
                  placeholder="openhermes"
                />
              }
            />
            
            <SettingItem
              title="Ollama API URL"
              description="Ollama API URL (leave blank for CLI mode)"
              control={
                <input
                  type="text"
                  className="input"
                  value={configData.OLLAMA_API_URL || ''}
                  onChange={(e) => handleInputChange('OLLAMA_API_URL', e.target.value)}
                  placeholder="http://localhost:11434"
                />
              }
            />
          </ConfigSection>
        )}

        {/* API Keys */}
        {activeSettingsTab === 'api' && (
          <ConfigSection
            title="🔑 API Keys"
            description="Manage your API keys for external services"
          >
            <ApiKeyInput
              title="OpenAI API Key"
              description="Your OpenAI API key for GPT models"
              value={configData.OPENAI_API_KEY || ''}
              onChange={(value) => handleInputChange('OPENAI_API_KEY', value)}
            />
            
            <ApiKeyInput
              title="Anthropic API Key"
              description="Your Anthropic API key for Claude models"
              value={configData.ANTHROPIC_API_KEY || ''}
              onChange={(value) => handleInputChange('ANTHROPIC_API_KEY', value)}
            />
            
            <ApiKeyInput
              title="Google API Key"
              description="Your Google API key for Gemini models"
              value={configData.GOOGLE_API_KEY || ''}
              onChange={(value) => handleInputChange('GOOGLE_API_KEY', value)}
            />
          </ConfigSection>
        )}

        {/* Interface Settings */}
        {activeSettingsTab === 'interface' && (
          <ConfigSection
            title="🎨 Interface Settings"
            description="Customize the user interface appearance and behavior"
          >
            <SettingItem
              title="Theme Preference"
              description="Choose your preferred color scheme"
              control={
                <select 
                  className="input"
                  value={configData.THEME_PREFERENCE || 'dark'}
                  onChange={(e) => handleInputChange('THEME_PREFERENCE', e.target.value)}
                >
                  <option value="system">System Default</option>
                  <option value="dark">Dark Mode</option>
                  <option value="light">Light Mode</option>
                </select>
              }
            />
            
            <SettingItem
              title="Font Size"
              description="Adjust the text size for better readability"
              control={
                <select 
                  className="input"
                  value={configData.FONT_SIZE || 'medium'}
                  onChange={(e) => handleInputChange('FONT_SIZE', e.target.value)}
                >
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large">Large</option>
                </select>
              }
            />
            
            <SettingItem
              title="Show Typing Indicators"
              description="Display when the AI is typing a response"
              control={
                <ToggleSwitch
                  checked={configData.SHOW_TYPING_INDICATORS === 'true'}
                  onChange={(checked) => handleInputChange('SHOW_TYPING_INDICATORS', checked ? 'true' : 'false')}
                />
              }
            />
            
            <SettingItem
              title="Auto-scroll to New Messages"
              description="Automatically scroll to the latest message"
              control={
                <ToggleSwitch
                  checked={configData.AUTO_SCROLL === 'true'}
                  onChange={(checked) => handleInputChange('AUTO_SCROLL', checked ? 'true' : 'false')}
                />
              }
            />
            
            <SettingItem
              title="Send Message Shortcut"
              description="Keyboard shortcut to send messages"
              control={
                <select 
                  className="input"
                  value={configData.SEND_SHORTCUT || 'enter'}
                  onChange={(e) => handleInputChange('SEND_SHORTCUT', e.target.value)}
                >
                  <option value="enter">Enter</option>
                  <option value="ctrl-enter">Ctrl + Enter</option>
                  <option value="shift-enter">Shift + Enter</option>
                </select>
              }
            />
          </ConfigSection>
        )}

        {/* Audio Settings */}
        {activeSettingsTab === 'audio' && (
          <ConfigSection
            title="🔊 Audio & Voice Settings"
            description="Configure microphone, speaker, and voice settings"
          >
            <SettingItem
              title="Wake Word Detection"
              description='Enable voice activation with "Hey PersonaOS"'
              control={
                <ToggleSwitch
                  checked={configData.WAKE_WORD_ENABLED === 'true'}
                  onChange={(checked) => handleInputChange('WAKE_WORD_ENABLED', checked ? 'true' : 'false')}
                />
              }
            />
            
            <SettingItem
              title="Picovoice API Key"
              description="API key for wake word detection service"
              control={
                <ApiKeyInput
                  title=""
                  description=""
                  value={configData.PICOVOICE_API_KEY || ''}
                  onChange={(value) => handleInputChange('PICOVOICE_API_KEY', value)}
                />
              }
            />
            
            <SettingItem
              title="Text-to-Speech"
              description="Enable AI voice responses"
              control={
                <ToggleSwitch
                  checked={configData.TTS_ENABLED === 'true'}
                  onChange={(checked) => handleInputChange('TTS_ENABLED', checked ? 'true' : 'false')}
                />
              }
            />
            
            <SettingItem
              title="Voice Volume"
              description="Adjust the AI voice response volume"
              control={
                <div className="voice-volume-control">
                  <input
                    type="range"
                    className="range-slider"
                    min="0"
                    max="100"
                    step="5"
                    value={configData.VOICE_VOLUME || '75'}
                    onChange={(e) => handleInputChange('VOICE_VOLUME', e.target.value)}
                  />
                  <div className="range-value">
                    <span>0%</span>
                    <span>{configData.VOICE_VOLUME || '75'}%</span>
                    <span>100%</span>
                  </div>
                </div>
              }
            />
            
            <SettingItem
              title="Microphone Device Index"
              description="Audio input device index (optional)"
              control={
                <input
                  type="number"
                  className="input"
                  value={configData.MIC_DEVICE_INDEX || ''}
                  onChange={(e) => handleInputChange('MIC_DEVICE_INDEX', e.target.value)}
                  placeholder="Auto-detect"
                />
              }
            />
            
            <SettingItem
              title="Speaker Device Index"
              description="Audio output device index (optional)"
              control={
                <input
                  type="number"
                  className="input"
                  value={configData.SPEAKER_DEVICE_INDEX || ''}
                  onChange={(e) => handleInputChange('SPEAKER_DEVICE_INDEX', e.target.value)}
                  placeholder="Auto-detect"
                />
              }
            />
          </ConfigSection>
        )}

        {/* Privacy & Security */}
        {activeSettingsTab === 'privacy' && (
          <ConfigSection
            title="🔒 Privacy & Security"
            description="Configure data privacy and security settings"
          >
            <SettingItem
              title="Local Processing"
              description="Keep all data processing on your device"
              control={
                <ToggleSwitch
                  checked={configData.LOCAL_PROCESSING !== 'false'}
                  onChange={(checked) => handleInputChange('LOCAL_PROCESSING', checked ? 'true' : 'false')}
                  disabled={true}
                />
              }
            />
            
            <SettingItem
              title="Save Conversation History"
              description="Store conversations locally for future reference"
              control={
                <ToggleSwitch
                  checked={configData.SAVE_HISTORY !== 'false'}
                  onChange={(checked) => handleInputChange('SAVE_HISTORY', checked ? 'true' : 'false')}
                />
              }
            />
            
            <SettingItem
              title="Auto-delete Old Conversations"
              description="Automatically remove conversations older than specified time"
              control={
                <select 
                  className="input"
                  value={configData.AUTO_DELETE_DAYS || 'never'}
                  onChange={(e) => handleInputChange('AUTO_DELETE_DAYS', e.target.value)}
                >
                  <option value="never">Never</option>
                  <option value="30">30 days</option>
                  <option value="90">90 days</option>
                  <option value="365">1 year</option>
                </select>
              }
            />
            
            <SettingItem
              title="Encrypt Conversations"
              description="Encrypt stored conversation data"
              control={
                <ToggleSwitch
                  checked={configData.ENCRYPT_CONVERSATIONS === 'true'}
                  onChange={(checked) => handleInputChange('ENCRYPT_CONVERSATIONS', checked ? 'true' : 'false')}
                />
              }
            />
          </ConfigSection>
        )}

        {/* Intent & Safety */}
        {activeSettingsTab === 'safety' && (
          <ConfigSection
            title="🛡️ Intent & Safety"
            description="Configure safety and tool execution settings"
          >
            <SettingItem
              title="Intent Processing"
              description="Enable intent detection and processing"
              control={
                <ToggleSwitch
                  checked={configData.INTENT_ENABLED === 'true'}
                  onChange={(checked) => handleInputChange('INTENT_ENABLED', checked ? 'true' : 'false')}
                />
              }
            />
            
            <SettingItem
              title="Safety Level"
              description="Set the safety validation level"
              control={
                <select 
                  className="input"
                  value={configData.SAFETY_LEVEL || 'standard'}
                  onChange={(e) => handleInputChange('SAFETY_LEVEL', e.target.value)}
                >
                  <option value="strict">Strict</option>
                  <option value="standard">Standard</option>
                  <option value="relaxed">Relaxed</option>
                </select>
              }
            />
            
            <SettingItem
              title="Allow Tool Execution"
              description="Allow plugins and tools to be executed"
              control={
                <ToggleSwitch
                  checked={configData.ALLOW_TOOL_EXECUTION === 'true'}
                  onChange={(checked) => handleInputChange('ALLOW_TOOL_EXECUTION', checked ? 'true' : 'false')}
                />
              }
            />
          </ConfigSection>
        )}

        {/* Developer Options */}
        {activeSettingsTab === 'dev' && (
          <ConfigSection
            title="⚙️ Developer Options"
            description="Debug and development settings"
          >
            <SettingItem
              title="Debug Mode"
              description="Enable debug logging"
              control={
                <ToggleSwitch
                  checked={configData.DEBUG_MODE === 'true'}
                  onChange={(checked) => handleInputChange('DEBUG_MODE', checked ? 'true' : 'false')}
                />
              }
            />
            
            <SettingItem
              title="Log Level"
              description="Set the logging level"
              control={
                <select 
                  className="input"
                  value={configData.LOG_LEVEL || 'INFO'}
                  onChange={(e) => handleInputChange('LOG_LEVEL', e.target.value)}
                >
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
              }
            />
          </ConfigSection>
        )}

        {/* Web UI */}
        {activeSettingsTab === 'ui' && (
          <ConfigSection
            title="🌐 Web UI Settings"
            description="Configure web interface settings"
          >
            <SettingItem
              title="Web UI Enabled"
              description="Enable the web user interface"
              control={
                <ToggleSwitch
                  checked={configData.WEB_UI_ENABLED === 'true'}
                  onChange={(checked) => handleInputChange('WEB_UI_ENABLED', checked ? 'true' : 'false')}
                />
              }
            />
            
            <SettingItem
              title="Status Bar Location"
              description="Choose where to display the status bar"
              control={
                <StatusBarLocationSelector 
                  currentLocation={statusBarLocation}
                  onLocationChange={changeStatusBarLocation}
                />
              }
            />
            
            <SettingItem
              title="Backend Port"
              description="FastAPI backend server port"
              control={
                <input
                  type="number"
                  className="input"
                  value={configData.WEB_UI_PORT || '8000'}
                  onChange={(e) => handleInputChange('WEB_UI_PORT', e.target.value)}
                />
              }
            />
            
            <SettingItem
              title="Frontend Port"
              description="Frontend development server port"
              control={
                <input
                  type="number"
                  className="input"
                  value={configData.FRONTEND_PORT || '3000'}
                  onChange={(e) => handleInputChange('FRONTEND_PORT', e.target.value)}
                />
              }
            />
          </ConfigSection>
        )}
      </div>
    </div>
  )
}

// Configuration Section Component
function ConfigSection({ title, description, children }) {
  return (
    <div className="config-section">
      <div className="config-section-header">
        <h3 className="config-section-title">{title}</h3>
        <p className="config-section-description">{description}</p>
      </div>
      <div className="config-section-content">
        {children}
      </div>
    </div>
  )
}

// Setting Item Component
function SettingItem({ title, description, control }) {
  return (
    <div className="setting-item">
      <div className="setting-info">
        <div className="setting-title">{title}</div>
        <div className="setting-description">{description}</div>
      </div>
      <div className="setting-control">
        {control}
      </div>
    </div>
  )
}

// API Key Input Component
function ApiKeyInput({ title, description, value, onChange }) {
  const [showKey, setShowKey] = useState(false)

  return (
    <SettingItem
      title={title}
      description={description}
      control={
        <div className="api-key-input">
          <input
            type={showKey ? "text" : "password"}
            className="input"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Enter API key..."
          />
          <button
            type="button"
            className="api-key-toggle"
            onClick={() => setShowKey(!showKey)}
          >
            {showKey ? '👁️' : '🔒'}
          </button>
        </div>
      }
    />
  )
}

// Toggle Switch Component
function ToggleSwitch({ checked, onChange, disabled = false }) {
  return (
    <label className={`toggle ${disabled ? 'disabled' : ''}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange && onChange(e.target.checked)}
        disabled={disabled}
      />
      <span className="toggle-slider"></span>
    </label>
  )
}

// Layout Dropdown Component
function LayoutDropdown({ currentLayout, onLayoutChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  const layouts = [
    { id: 'default', name: 'Default', icon: '⚏' },
    { id: 'focused', name: 'Focused', icon: '⚎' },
    { id: 'wide', name: 'Wide', icon: '⬌' },
    { id: 'minimal', name: 'Minimal', icon: '⚍' },
    { id: 'chat-only', name: 'Chat Only', icon: '💬' }
  ]

  const currentLayoutInfo = layouts.find(layout => layout.id === currentLayout) || layouts[0]

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLayoutSelect = (layoutId) => {
    onLayoutChange(layoutId)
    setIsOpen(false)
  }

  return (
    <div className={`dropdown layout-dropdown ${isOpen ? 'open' : ''}`} ref={dropdownRef}>
      <button 
        className="dropdown-trigger layout-trigger"
        onClick={() => setIsOpen(!isOpen)}
        title="Change Layout"
      >
        <span className="layout-current">
          <span className="layout-icon">{currentLayoutInfo.icon}</span>
          <span className="layout-name">{currentLayoutInfo.name}</span>
        </span>
        <span className="dropdown-arrow">▼</span>
      </button>
      
      <div className="dropdown-content layout-dropdown-content">
        {layouts.map((layout) => (
          <div
            key={layout.id}
            className={`dropdown-item layout-item ${layout.id === currentLayout ? 'selected' : ''}`}
            onClick={() => handleLayoutSelect(layout.id)}
          >
            <span className="layout-item-info">
              <span className="layout-icon">{layout.icon}</span>
              <span className="layout-name">{layout.name}</span>
            </span>
            {layout.id === currentLayout && <span className="check-mark">✓</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

export default App