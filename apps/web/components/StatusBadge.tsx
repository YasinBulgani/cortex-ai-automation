'use client'

type Status = 'active' | 'inactive' | 'pending' | 'failed' | 'success' | 'warning' | 'draft' | 'open' | 'closed' | 'resolved'

const statusConfig: Record<Status, { label: string; className: string }> = {
  active:   { label: 'Aktif',       className: 'bg-green-100 text-green-800' },
  inactive: { label: 'Pasif',       className: 'bg-gray-100 text-gray-800' },
  pending:  { label: 'Bekliyor',    className: 'bg-yellow-100 text-yellow-800' },
  failed:   { label: 'Başarısız',   className: 'bg-red-100 text-red-800' },
  success:  { label: 'Başarılı',    className: 'bg-green-100 text-green-800' },
  warning:  { label: 'Uyarı',       className: 'bg-orange-100 text-orange-800' },
  draft:    { label: 'Taslak',      className: 'bg-blue-100 text-blue-800' },
  open:     { label: 'Açık',        className: 'bg-red-100 text-red-800' },
  closed:   { label: 'Kapalı',      className: 'bg-gray-100 text-gray-800' },
  resolved: { label: 'Çözüldü',     className: 'bg-green-100 text-green-800' },
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const config = statusConfig[status as Status] ?? { label: status, className: 'bg-gray-100 text-gray-800' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.className}`}>
      {label ?? config.label}
    </span>
  )
}
