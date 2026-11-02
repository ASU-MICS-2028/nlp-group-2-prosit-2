import { Menu, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'

type Props = {
  sidebar: ReactNode
  children: ReactNode
}

// Sidebar on the left, content on the right. Under 768px the sidebar slides over the page.
export function AppShell({ sidebar, children }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="shell">
      <aside
        id="sidebar"
        className={`sidebar ${menuOpen ? 'sidebar--open' : ''}`}
        aria-label="Projects"
      >
        {sidebar}
      </aside>
      <main className="main haze">
        <div className="main__inner">
          <button
            type="button"
            className="btn btn--secondary menu-button"
            aria-label={
              menuOpen ? 'Close the project menu' : 'Open the project menu'
            }
            aria-expanded={menuOpen}
            aria-controls="sidebar"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? (
              <X size={16} aria-hidden />
            ) : (
              <Menu size={16} aria-hidden />
            )}
          </button>
          {children}
        </div>
      </main>
    </div>
  )
}
