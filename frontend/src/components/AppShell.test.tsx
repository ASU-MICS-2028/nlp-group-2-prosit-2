import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AppShell } from './AppShell'
import { Sidebar } from './Sidebar'

// The phone menu (under 768px). jsdom has no layout, so these check the open/closed state;
// how it looks on a phone is checked in a real browser (learnings/frontend.md).
function show() {
  const picked: string[] = []
  const view = render(
    <AppShell
      sidebar={
        <Sidebar
          projects={[
            { id: 'p_1', name: 'Clinic API', status: 'ready', when: 'now' },
          ]}
          activeId={null}
          onNewProject={() => picked.push('new')}
          onSelect={(id) => picked.push(id)}
        />
      }
    >
      <p>The page</p>
    </AppShell>,
  )
  return { ...view, picked }
}

const isOpen = (container: HTMLElement) =>
  container.querySelector('#sidebar')?.classList.contains('sidebar--open')

function openMenu() {
  fireEvent.click(screen.getByRole('button', { name: 'Open the project menu' }))
}

describe('the phone menu', () => {
  it('opens from the menu button', () => {
    const { container } = show()
    expect(isOpen(container)).toBe(false)

    openMenu()

    expect(isOpen(container)).toBe(true)
    expect(
      screen.getByRole('button', { name: 'Open the project menu' }),
    ).toHaveAttribute('aria-expanded', 'true')
  })

  it('"New project" does its job and closes the menu, so the Start screen shows', () => {
    const { container, picked } = show()
    openMenu()

    fireEvent.click(screen.getByRole('button', { name: /New project/ }))

    expect(picked).toEqual(['new'])
    expect(isOpen(container)).toBe(false)
  })

  it('picking a project opens it and closes the menu, even when the tap lands on its name', () => {
    const { container, picked } = show()
    openMenu()

    fireEvent.click(screen.getByText('Clinic API')) // the text inside the row's button

    expect(picked).toEqual(['p_1'])
    expect(isOpen(container)).toBe(false)
  })

  it('a tap on the dimmed page beside it closes it', () => {
    const { container } = show()
    openMenu()

    fireEvent.click(screen.getByTestId('menu-backdrop'))

    expect(isOpen(container)).toBe(false)
    expect(screen.queryByTestId('menu-backdrop')).not.toBeInTheDocument()
  })

  it('Escape closes it', () => {
    const { container } = show()
    openMenu()

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(isOpen(container)).toBe(false)
  })

  it('its own X closes it', () => {
    const { container } = show()
    openMenu()

    fireEvent.click(
      screen.getByRole('button', { name: 'Close the project menu' }),
    )

    expect(isOpen(container)).toBe(false)
  })

  it('a tap on empty space inside the menu leaves it open', () => {
    const { container } = show()
    openMenu()

    fireEvent.click(screen.getByText('Projects'))

    expect(isOpen(container)).toBe(true)
  })
})
