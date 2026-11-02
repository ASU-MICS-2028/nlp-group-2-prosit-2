import { CircleAlert, CircleCheck, Info, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'

type Tone = 'info' | 'warning' | 'error' | 'success'

const ICON = {
  info: Info,
  warning: TriangleAlert,
  error: CircleAlert,
  success: CircleCheck,
}

type Props = {
  tone: Tone
  title: string
  children: ReactNode
  action?: ReactNode
}

export function Notice({ tone, title, children, action }: Props) {
  const Icon = ICON[tone]
  return (
    // Errors interrupt screen readers (alert); everything else waits politely (status)
    <div
      className={`notice notice--${tone}`}
      role={tone === 'error' ? 'alert' : 'status'}
    >
      <Icon size={18} strokeWidth={1.5} aria-hidden />
      <div className="notice__body">
        <strong className="t-label">{title}</strong>
        <span className="notice__text">{children}</span>
        {action}
      </div>
    </div>
  )
}
