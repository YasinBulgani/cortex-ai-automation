/**
 * useAIChat Hook - Multi-turn AI conversation
 */

import { useState } from 'react'
import { apiClient } from '@/lib/api-client'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatRequest {
  messages: ChatMessage[]
  projectId: string
}

interface ChatResponse {
  content: string
  confidence_score: number
}

export default function useAIChat() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const chat = async (request: ChatRequest): Promise<ChatResponse> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.post<ChatResponse>('/api/v1/ai-service/generate-bdd', {
        story: request.messages[request.messages.length - 1].content,
        project_id: request.projectId,
        context: {
          history: request.messages.slice(0, -1),
        },
      })

      return response.data
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Chat failed'
      setError(errorMsg)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return {
    chat,
    isLoading,
    error,
  }
}
