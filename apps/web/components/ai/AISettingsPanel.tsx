/**
 * AI Settings Panel
 * Configure LLM provider, token limits, routing preferences
 */

import React, { useState, useEffect } from 'react'
import { Settings, Save } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface AISettings {
  provider: 'ollama' | 'groq' | 'openai' | 'anthropic' | 'gemini'
  routing_mode: 'cost_optimized' | 'balanced' | 'quality_first'
  token_budget_per_request: number
  daily_budget_usd: number
  hallucination_confidence_threshold: number
  approval_required_for: string[]
}

export default function AISettingsPanel() {
  const [settings, setSettings] = useState<AISettings>({
    provider: 'ollama',
    routing_mode: 'balanced',
    token_budget_per_request: 4000,
    daily_budget_usd: 50,
    hallucination_confidence_threshold: 0.7,
    approval_required_for: ['code_generation', 'defect_creation'],
  })

  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    try {
      await fetch('/api/v1/ai-service/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('Failed to save settings:', error)
    }
  }

  return (
    <div className="max-w-2xl rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <div className="flex items-center gap-2 mb-6">
        <Settings size={24} />
        <h2 className="text-xl font-bold">AI Service Settings</h2>
      </div>

      <div className="space-y-6">
        {/* LLM Provider */}
        <div>
          <label className="block text-sm font-medium mb-2">LLM Provider</label>
          <select
            value={settings.provider}
            onChange={(e) => setSettings({ ...settings, provider: e.target.value as any })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
          >
            <option value="ollama">Ollama (Free, Local)</option>
            <option value="groq">Groq ($0.0002-0.0006/1K)</option>
            <option value="openai">OpenAI ($0.03-0.06/1K)</option>
            <option value="anthropic">Anthropic ($0.015-0.045/1K)</option>
            <option value="gemini">Gemini ($0.0005-0.0015/1K)</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">Choose your preferred LLM provider</p>
        </div>

        {/* Routing Mode */}
        <div>
          <label className="block text-sm font-medium mb-2">Routing Mode</label>
          <select
            value={settings.routing_mode}
            onChange={(e) => setSettings({ ...settings, routing_mode: e.target.value as any })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
          >
            <option value="cost_optimized">Cost Optimized (fastest, cheapest)</option>
            <option value="balanced">Balanced (default)</option>
            <option value="quality_first">Quality First (slower, more accurate)</option>
          </select>
        </div>

        {/* Token Budget */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Token Budget per Request: {settings.token_budget_per_request}
          </label>
          <input
            type="range"
            min="1000"
            max="10000"
            step="500"
            value={settings.token_budget_per_request}
            onChange={(e) => setSettings({ ...settings, token_budget_per_request: parseInt(e.target.value) })}
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">Higher = more context, slower + costlier</p>
        </div>

        {/* Daily Budget */}
        <div>
          <label className="block text-sm font-medium mb-2">Daily Budget: ${settings.daily_budget_usd}</label>
          <input
            type="range"
            min="10"
            max="500"
            step="10"
            value={settings.daily_budget_usd}
            onChange={(e) => setSettings({ ...settings, daily_budget_usd: parseInt(e.target.value) })}
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">Alerts when approaching limit</p>
        </div>

        {/* Hallucination Threshold */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Hallucination Confidence Threshold: {(settings.hallucination_confidence_threshold * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min="0.5"
            max="0.95"
            step="0.05"
            value={settings.hallucination_confidence_threshold}
            onChange={(e) => setSettings({ ...settings, hallucination_confidence_threshold: parseFloat(e.target.value) })}
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">Lower = stricter validation, more rejections</p>
        </div>

        {/* Approval Requirements */}
        <div>
          <label className="block text-sm font-medium mb-2">Require Approval For:</label>
          <div className="space-y-2">
            {['code_generation', 'defect_creation', 'sql_generation'].map((action) => (
              <label key={action} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings.approval_required_for.includes(action)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSettings({
                        ...settings,
                        approval_required_for: [...settings.approval_required_for, action],
                      })
                    } else {
                      setSettings({
                        ...settings,
                        approval_required_for: settings.approval_required_for.filter((a) => a !== action),
                      })
                    }
                  }}
                  className="rounded"
                />
                <span className="text-sm capitalize">{action.replace('_', ' ')}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="mt-6 flex gap-2">
        <Button onClick={handleSave} className="gap-2 bg-blue-600 hover:bg-blue-700 text-white">
          <Save size={16} />
          {saved ? '✓ Saved' : 'Save Settings'}
        </Button>
      </div>
    </div>
  )
}
