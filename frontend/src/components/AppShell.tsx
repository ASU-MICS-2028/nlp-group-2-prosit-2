import { Menu, X } from 'lucide-react'
import { useEffect, useState, type MouseEvent, type ReactNode } from 'react'

type Props = {
  sidebar: ReactNode
  children: ReactNode
}

// Sidebar on the left, content on the right. Under 768px the sidebar slides over the page as a menu.
// The menu closes when the person: picks something in it (a project, "New project"), taps the dimmed page
// beside it, presses Escape, or taps its own X. (On a wide screen the menu is always shown, so none of this matters.)
export function AppShell({ sidebar, children }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)

  // Escape closes the open menu (keyboard users). The listener exists only while the menu is open.
  useEffect(() => {
    if (!menuOpen) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey) // cleanup when it closes or the page goes away
  }, [menuOpen])

  // A tap on any button inside the menu ("New project", a project) also closes it, so the chosen screen shows.
  // closest('button') finds the button even when the tap lands on its icon or text.
  function closeAfterChoice(event: MouseEvent<HTMLElement>) {
    if (event.target instanceof Element && event.target.closest('button')) {
      setMenuOpen(false)
    }
  }

  return (
    <div className="shell">
      <aside
        id="sidebar"
        className={`sidebar ${menuOpen ? 'sidebar--open' : ''}`}
        aria-label="Projects"
        onClick={closeAfterChoice}
      >
        {/* Only shown on a phone: the menu covers the page's own button, so it has its own way out */}
        <button
          type="button"
          className="btn btn--ghost sidebar__close"
          aria-label="Close the project menu"
        >
          <X size={16} aria-hidden />
        </button>
        {sidebar}
      </aside>
      {/* The dimmed page beside the open menu: tapping it closes the menu. Only shown on a phone. */}
      {menuOpen && (
        <div
          className="menu-backdrop"
          data-testid="menu-backdrop"
          aria-hidden
          onClick={() => setMenuOpen(false)}
        />
      )}
      <main className="main haze">
        <div className="main__inner">
          <button
            type="button"
            className="btn btn--secondary menu-button"
            aria-label="Open the project menu"
            aria-expanded={menuOpen}
            aria-controls="sidebar"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={16} aria-hidden />
          </button>
          {children}
        </div>
      </main>
    </div>
  )
}
