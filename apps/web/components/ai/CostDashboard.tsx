/**
 * AI Cost Dashboard
 * Track LLM usage and costs in real-time
 */

import React, { useEffect, useState } from 'react'
import { DollarSign, TrendingUp } from 'lucide-react'

interface CostData {
  feature: string
  calls: number
  tokens: number
  cost_usd: number
  trend: number  // % change vs last period
}

export default function CostDashboard() {
  const [costs, setCosts] = useState<CostData[]>([])
  const [totalCost, setTotalCost] = useState(0)
  const [period, setPeriod] = useState('24h')  // 24h, 7d, 30d

  useEffect(() => {
    fetchCosts()
  }, [period])

  const fetchCosts = async () => {
    try {
      const response = await fetch(`/api/v1/ai-service/costs?period=${period}`)
      const data = await response.json()
      setCosts(data.costs || [])
      setTotalCost(data.total_cost)
    } catch (error) {
      console.error('Failed to fetch costs:', error)
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <DollarSign size={24} className="text-green-600" />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">LLM Cost Summary</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">Last {period}</p>
          </div>
        </div>

        <div className="text-right">
          <div className="text-3xl font-bold text-gray-900 dark:text-white">
            ${totalCost.toFixed(2)}
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            {costs.reduce((sum, c) => sum + c.calls, 0)} API calls
          </p>
        </div>
      </div>

      {/* Period Selector */}
      <div className="flex gap-2 mb-4">
        {['24h', '7d', '30d'].map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1 rounded text-sm ${
              period === p
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Breakdown by Feature */}
      <div className="space-y-3">
        {costs.map((cost) => (
          <div key={cost.feature} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
            <div className="flex-1">
              <p className="font-medium text-gray-900 dark:text-white capitalize">
                {cost.feature.replace('_', ' ')}
              </p>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {cost.calls} calls • {cost.tokens.toLocaleString()} tokens
              </p>
            </div>

            <div className="text-right">
              <p className="font-semibold text-gray-900 dark:text-white">
                ${cost.cost_usd.toFixed(3)}
              </p>
              {cost.trend !== 0 && (
                <p className={`text-xs flex items-center gap-1 ${
                  cost.trend > 0 ? 'text-red-600' : 'text-green-600'
                }`}>
                  <TrendingUp size={12} />
                  {cost.trend > 0 ? '+' : ''}{cost.trend.toFixed(0)}%
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Budget Alert */}
      {totalCost > 100 && (
        <div className="mt-4 p-3 bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded">
          <p className="text-sm text-orange-900 dark:text-orange-100">
            ⚠️ Monthly cost trending toward ${(totalCost * 30).toFixed(0)}
          </p>
        </div>
      )}
    </div>
  )
}
