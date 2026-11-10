import { LoaderCircle } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost'
  // While loading, the label stays visible and the button is disabled
  loading?: boolean
}

// Only one primary button per screen: it is the one glowing thing.
export function Button({
  variant = 'secondary',
  loading = false,
  disabled,
  className = '',
  children,
  ...rest
}: Props) {
  const glow = variant === 'primary' ? 'glow-edge glow-edge--strong' : ''
  return (
    <button
      type="button"
      className={`btn btn--${variant} ${glow} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <LoaderCircle size={16} className="spin" aria-hidden />}
      {children}
    </button>
  )
}
