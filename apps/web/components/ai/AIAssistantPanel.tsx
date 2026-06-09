/**
 * Global AI Assistant Panel
 * Bottom-right floating panel for multi-turn conversations
 * Accessible from any page in the app
 */

import React, { useState, useRef, useEffect } from 'react'
import { MessageCircle, X, Send, Loader } from 'lucide-react'
import { Button } from '@/components/ui/button'
import useAIChat from '@/lib/hooks/useAIChat'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export default function AIAssistantPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { chat, isLoading: apiLoading } = useAIChat()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Call AI service
      const response = await chat({
        messages: [...messages, userMessage].map((m) => ({
          role: m.role,
          content: m.content,
        })),
        projectId: 'current',
      })

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: Date.now(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error('AI chat error:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: Date.now(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 z-40 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 p-4 text-white shadow-lg hover:shadow-xl transition-shadow"
        title="Open AI Assistant"
      >
        <MessageCircle size={24} />
      </button>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col w-96 h-[600px] bg-white dark:bg-gray-900 rounded-lg shadow-2xl border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="font-semibold text-gray-900 dark:text-white">Neurex AI Assistant</h2>
        <button
          onClick={() => setIsOpen(false)}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
        >
          <X size={20} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            <p className="text-center">
              Ask me anything about your tests, requirements, or defects. I can help generate test cases,
              analyze issues, and more!
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs px-4 py-2 rounded-lg ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-none'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-none'
              }`}
            >
              <p className="text-sm">{message.content}</p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-800 px-4 py-2 rounded-lg rounded-bl-none">
              <Loader size={16} className="animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything..."
            disabled={isLoading}
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Button
            type="submit"
            disabled={isLoading || !input.trim()}
            size="sm"
            className="bg-blue-500 hover:bg-blue-600 text-white"
          >
            <Send size={16} />
          </Button>
        </div>
      </form>
    </div>
  )
}
