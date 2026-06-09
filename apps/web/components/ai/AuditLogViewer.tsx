/**
 * AI Audit Log Viewer
 * View all LLM calls, approvals, costs for compliance
 */

import React, { useState, useEffect } from 'react'
import { Clock, Filter, Download } from 'lucide-react'

interface AuditLog {
  id: string
  ts: string
  feature: string
  actor_user_id: string
  tokens_input: number
  tokens_output: number
  cost_usd: number
  confidence_score: number
  approval_decision?: string
  model: string
}

export default function AuditLogViewer() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [filter, setFilter] = useState('all')  // all, approved, rejected, high-cost
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLogs()
  }, [filter])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/v1/ai-service/audit-logs?filter=${filter}&limit=100`)
      const data = await response.json()
      setLogs(data.logs || [])
    } catch (error) {
      console.error('Failed to fetch audit logs:', error)
    } finally {
      setLoading(false)
    }
  }

  const downloadCSV = () => {
    const headers = ['Timestamp', 'Feature', 'Model', 'Tokens', 'Cost', 'Confidence', 'Status']
    const rows = logs.map((log) => [
      new Date(log.ts).toLocaleString(),
      log.feature,
      log.model,
      log.tokens_input + log.tokens_output,
      `$${log.cost_usd.toFixed(4)}`,
      (log.confidence_score * 100).toFixed(0) + '%',
      log.approval_decision || 'N/A',
    ])

    const csv = [headers, ...rows].map((row) => row.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ai-audit-logs-${new Date().toISOString()}.csv`
    a.click()
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Clock size={24} />
          <h2 className="text-xl font-bold">AI Audit Log</h2>
        </div>
        <button
          onClick={downloadCSV}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
        >
          <Download size={16} />
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        {['all', 'approved', 'rejected', 'high-cost'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded text-sm capitalize ${
              filter === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Log Table */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Loading...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="text-left py-2 px-2">Time</th>
                <th className="text-left py-2 px-2">Feature</th>
                <th className="text-left py-2 px-2">Model</th>
                <th className="text-right py-2 px-2">Tokens</th>
                <th className="text-right py-2 px-2">Cost</th>
                <th className="text-right py-2 px-2">Confidence</th>
                <th className="text-center py-2 px-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="py-2 px-2 text-gray-600 dark:text-gray-400">
                    {new Date(log.ts).toLocaleTimeString()}
                  </td>
                  <td className="py-2 px-2 font-medium">{log.feature}</td>
                  <td className="py-2 px-2 text-gray-600 dark:text-gray-400">{log.model}</td>
                  <td className="py-2 px-2 text-right">{(log.tokens_input + log.tokens_output).toLocaleString()}</td>
                  <td className="py-2 px-2 text-right font-medium">${log.cost_usd.toFixed(4)}</td>
                  <td className="py-2 px-2 text-right">
                    <span className={`px-2 py-1 rounded text-xs ${
                      log.confidence_score > 0.85
                        ? 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100'
                        : log.confidence_score > 0.7
                        ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-900 dark:text-yellow-100'
                        : 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100'
                    }`}>
                      {(log.confidence_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-2 px-2 text-center">
                    {log.approval_decision && (
                      <span className={`px-2 py-1 rounded text-xs ${
                        log.approval_decision === 'approved'
                          ? 'bg-green-100 dark:bg-green-900 text-green-900 dark:text-green-100'
                          : 'bg-red-100 dark:bg-red-900 text-red-900 dark:text-red-100'
                      }`}>
                        {log.approval_decision}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
