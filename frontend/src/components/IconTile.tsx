import type { LucideIcon } from 'lucide-react'

export function IconTile({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <span className="icon-tile">
      <Icon size={16} strokeWidth={1.5} aria-hidden />
    </span>
  )
}
