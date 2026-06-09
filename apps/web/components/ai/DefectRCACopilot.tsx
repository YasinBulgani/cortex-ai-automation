/**
 * Defect RCA (Root Cause Analysis) Copilot
 * Inline AI suggestions for defect analysis
 */

import React, { useState } from 'react'
import { Lightbulb, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface DefectRCACopilotProps {
  defectId: string
  errorLog?: string
}

export default function DefectRCACopilot({ defectId, errorLog }: DefectRCACopilotProps) {
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const handleAnalyze = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/ai-service/analyze-defect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          defect_id: defectId,
          error_log: errorLog,
        }),
      })

      const data = await response.json()
      setSuggestions(data.root_causes || [])
      setIsExpanded(true)
    } catch (error) {
      console.error('RCA analysis failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="rounded-lg border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lightbulb size={18} className="text-amber-600 dark:text-amber-400" />
          <span className="text-sm font-medium text-amber-900 dark:text-amber-100">
            AI Root Cause Analysis
          </span>
        </div>
        <Button size="sm" onClick={handleAnalyze} disabled={isLoading}>
          {isLoading ? 'Analyzing...' : 'Analyze'}
        </Button>
      </div>

      {suggestions.length > 0 && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 flex items-center gap-1 text-sm text-amber-700 dark:text-amber-300"
        >
          <ChevronDown size={16} className={isExpanded ? 'rotate-180' : ''} />
          {suggestions.length} potential cause(s)
        </button>
      )}

      {isExpanded && (
        <div className="mt-3 space-y-2">
          {suggestions.map((cause, i) => (
            <div key={i} className="rounded bg-white dark:bg-gray-800 p-3 text-sm">
              <div className="font-medium text-gray-900 dark:text-white">
                {cause.description}
              </div>
              <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                Likelihood: {(cause.likelihood * 100).toFixed(0)}%
              </div>
              {cause.affected_components && (
                <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                  Components: {cause.affected_components.join(', ')}
                </div>
              )}
              {cause.suggested_fix && (
                <div className="mt-2 bg-blue-50 dark:bg-blue-950 p-2 rounded text-xs text-blue-900 dark:text-blue-100">
                  💡 {cause.suggested_fix}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
