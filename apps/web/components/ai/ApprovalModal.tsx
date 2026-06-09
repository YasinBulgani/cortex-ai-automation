/**
 * Approval Modal for Risky AI Actions
 * User approval required for: code generation, defect creation, SQL queries
 */

import React, { useState } from 'react'
import { AlertTriangle, CheckCircle, XCircle, Copy } from 'lucide-react'
import { Button } from '@/components/ui/Button'

interface ApprovalModalProps {
  isOpen: boolean
  feature: 'code_gen' | 'defect_creation' | 'sql_gen'
  title: string
  description: string
  content: string  // Generated code/SQL/etc
  confidence: number
  risks: string[]
  onApprove: () => void
  onReject: () => void
}

export default function ApprovalModal({
  isOpen,
  feature,
  title,
  description,
  content,
  confidence,
  risks,
  onApprove,
  onReject,
}: ApprovalModalProps) {
  const [copied, setCopied] = useState(false)

  if (!isOpen) return null

  const copyToClipboard = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const riskColor = confidence > 0.85 ? 'green' : confidence > 0.7 ? 'yellow' : 'red'
  const riskLevel = confidence > 0.85 ? 'Low Risk' : confidence > 0.7 ? 'Medium Risk' : 'High Risk'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-2xl rounded-lg bg-white dark:bg-gray-900 shadow-xl">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3">
            <AlertTriangle className={`text-${riskColor}-500`} size={24} />
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">{title}</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
            </div>
          </div>
        </div>

        {/* Risk Assessment */}
        <div className="bg-orange-50 dark:bg-orange-950 border-b border-orange-200 dark:border-orange-800 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-orange-900 dark:text-orange-100">Risk Assessment</p>
              <p className="text-sm text-orange-700 dark:text-orange-300">
                Confidence: {(confidence * 100).toFixed(0)}% — {riskLevel}
              </p>
            </div>
            <div className="flex gap-2">
              {risks.length === 0 ? (
                <CheckCircle className="text-green-500" size={24} />
              ) : (
                <div className="text-right">
                  <p className="text-sm font-medium text-orange-900">⚠️ {risks.length} risk(s)</p>
                  {risks.map((risk, i) => (
                    <p key={i} className="text-xs text-orange-700">
                      • {risk}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Content Preview */}
        <div className="p-6 max-h-64 overflow-y-auto bg-gray-50 dark:bg-gray-800">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">GENERATED CONTENT</p>
          <pre className="text-sm text-gray-900 dark:text-gray-100 font-mono whitespace-pre-wrap break-words">
            {content}
          </pre>
        </div>

        {/* Actions */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-6 flex gap-3">
          <Button
            onClick={copyToClipboard}
            variant="outline"
            className="flex-1 gap-2"
          >
            <Copy size={16} />
            {copied ? 'Copied!' : 'Copy Content'}
          </Button>

          <Button
            onClick={onReject}
            variant="outline"
            className="flex-1 gap-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
          >
            <XCircle size={16} />
            Reject
          </Button>

          <Button
            onClick={onApprove}
            className="flex-1 gap-2 bg-green-600 hover:bg-green-700 text-white"
          >
            <CheckCircle size={16} />
            Approve & Execute
          </Button>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4 text-xs text-gray-600 dark:text-gray-400">
          <p>✓ This action will be logged for audit purposes</p>
          <p>✓ You can revert changes within 4 hours</p>
        </div>
      </div>
    </div>
  )
}
