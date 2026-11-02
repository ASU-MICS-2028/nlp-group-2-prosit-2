type Props = {
  label: string
  // Only used when the chip is an answer choice
  selected?: boolean
  onClick?: () => void
}

export function Chip({ label, selected, onClick }: Props) {
  const glow = selected ? 'glow-edge glow-edge--strong' : 'glow-edge'
  return (
    <button
      type="button"
      className={`chip ${glow}`}
      aria-pressed={selected}
      onClick={onClick}
    >
      {label}
    </button>
  )
}
