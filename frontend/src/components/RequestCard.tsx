import { ArrowRight, Sparkles } from 'lucide-react'
import type { KeyboardEvent } from 'react'
import { Button } from './Button'

const MAX_LENGTH = 2000

type Props = {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  loading?: boolean
}

export function RequestCard({ value, onChange, onSubmit, loading }: Props) {
  const tooLongBy = value.length - MAX_LENGTH
  const isTooLong = tooLongBy > 0
  const canSubmit = value.trim().length > 0 && !isTooLong && !loading

  // Ctrl/Cmd + Enter sends, so people do not have to reach for the mouse
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === 'Enter' &&
      (event.ctrlKey || event.metaKey) &&
      canSubmit
    ) {
      onSubmit()
    }
  }

  return (
    <div className="card card--bordered">
      <label htmlFor="request" className="request__label t-label accent-text">
        <Sparkles size={16} strokeWidth={1.5} aria-hidden />
        Describe the API you need
      </label>
      <textarea
        id="request"
        className="request__textarea"
        rows={4}
        value={value}
        placeholder="For example: a bookshop where I can add books and see which are in stock"
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <div className="card__row">
        <span
          className="t-caption"
          style={{ color: isTooLong ? 'var(--error)' : 'var(--text-muted)' }}
        >
          {isTooLong
            ? `Too long by ${tooLongBy} characters`
            : `${value.length} / ${MAX_LENGTH}`}
        </span>
        <Button
          variant="primary"
          disabled={!canSubmit}
          loading={loading}
          onClick={onSubmit}
        >
          {loading ? 'Reading your request' : 'Plan my API'}
          {!loading && <ArrowRight size={16} aria-hidden />}
        </Button>
      </div>
    </div>
  )
}
