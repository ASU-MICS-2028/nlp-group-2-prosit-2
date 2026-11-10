import {
  Ban,
  Check,
  CircleCheck,
  CircleX,
  Clock,
  RotateCw,
  type LucideIcon,
} from 'lucide-react'

export type Status =
  'working' | 'waiting' | 'retrying' | 'passed' | 'ready' | 'failed' | 'stopped'

// Status is never shown by colour alone: every status has a word and an icon.
const STATUS: Record<
  Status,
  { word: string; color: string; icon?: LucideIcon }
> = {
  working: { word: 'Working', color: 'var(--accent-text)' },
  waiting: { word: 'Waiting', color: 'var(--warning)', icon: Clock },
  retrying: { word: 'Retrying', color: 'var(--warning)', icon: RotateCw },
  passed: { word: 'Passed', color: 'var(--success)', icon: Check },
  ready: { word: 'Ready', color: 'var(--success)', icon: CircleCheck },
  failed: { word: 'Failed', color: 'var(--error)', icon: CircleX },
  stopped: { word: 'Stopped', color: 'var(--error)', icon: Ban },
}

export function StatusPill({ status }: { status: Status }) {
  const { word, color, icon: Icon } = STATUS[status]
  return (
    <span className="status-pill" style={{ color }}>
      {Icon ? (
        <Icon size={14} strokeWidth={1.5} aria-hidden />
      ) : (
        <span className="status-dot pulse" aria-hidden />
      )}
      {word}
    </span>
  )
}
