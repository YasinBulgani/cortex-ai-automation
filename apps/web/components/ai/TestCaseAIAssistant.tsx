/**
 * Test Case AI Assistant Copilot
 * Inline suggestions for test improvements, missing tests, etc.
 */

import React, { useState } from 'react'
import { Sparkles, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Suggestion {
  id: string
  type: 'improvement' | 'missing' | 'risk'
  title: string
  description: string
  action?: () => void
}

interface TestCaseAIAssistantProps {
  testCaseId: string
  projectId: string
  onApply?: (suggestion: Suggestion) => void
}

export default function TestCaseAIAssistant({
  testCaseId,
  projectId,
  onApply,
}: TestCaseAIAssistantProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const handleAnalyze = async () => {
    setIsLoading(true)
    try {
      // Call AI service to get suggestions
      const response = await fetch('/api/v1/ai-service/improve-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_case_id: testCaseId,
          project_id: projectId,
        }),
      })

      const data = await response.json()

      // Convert API response to suggestions
      const newSuggestions: Suggestion[] = (data.suggestions || []).map(
        (s: any, idx: number) => ({
          id: `suggestion-${idx}`,
          type: s.type || 'improvement',
          title: s.description,
          description: s.suggested_change,
        })
      )

      setSuggestions(newSuggestions)
      setIsExpanded(true)
    } catch (error) {
      console.error('Error getting suggestions:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="rounded-lg border border-blue-200 dark:border-blue-900 bg-blue-50 dark:bg-blue-950 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-blue-600 dark:text-blue-400" />
          <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
            AI Suggestions
          </span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleAnalyze}
          disabled={isLoading}
        >
          {isLoading ? 'Analyzing...' : 'Analyze'}
        </Button>
      </div>

      {suggestions.length > 0 && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          <ChevronDown size={16} className={isExpanded ? 'rotate-180' : ''} />
          {suggestions.length} suggestions
        </button>
      )}

      {isExpanded && (
        <div className="mt-3 space-y-2">
          {suggestions.map((suggestion) => (
            <div
              key={suggestion.id}
              className="rounded bg-white dark:bg-gray-800 p-3 text-sm"
            >
              <div className="font-medium text-gray-900 dark:text-white">
                {suggestion.title}
              </div>
              <p className="mt-1 text-gray-600 dark:text-gray-300">
                {suggestion.description}
              </p>
              {suggestion.action && (
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-2"
                  onClick={() => {
                    suggestion.action?.()
                    onApply?.(suggestion)
                  }}
                >
                  Apply
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
