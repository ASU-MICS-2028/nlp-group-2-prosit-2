import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Button } from './Button'
import { Chip } from './Chip'
import { Notice } from './Notice'
import { RequestCard } from './RequestCard'
import { Sidebar } from './Sidebar'
import { StatusPill } from './StatusPill'

describe('Button', () => {
  it('is disabled while loading but keeps its label', () => {
    render(<Button loading>Reading your request</Button>)

    const button = screen.getByRole('button', { name: 'Reading your request' })
    expect(button).toBeDisabled()
  })
})

describe('Chip', () => {
  it('tells screen readers whether it is selected', () => {
    render(<Chip label="Yes" selected />)

    expect(screen.getByRole('button', { name: 'Yes' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })
})

describe('StatusPill', () => {
  it('shows a word, not only a colour', () => {
    render(<StatusPill status="failed" />)

    expect(screen.getByText('Failed')).toBeInTheDocument()
  })
})

describe('Notice', () => {
  it('uses the alert role for errors', () => {
    render(
      <Notice tone="error" title="Oops">
        Try again.
      </Notice>,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
  })
})

describe('RequestCard', () => {
  it('cannot be sent when empty', () => {
    render(<RequestCard value="   " onChange={() => {}} onSubmit={() => {}} />)

    expect(screen.getByRole('button', { name: /Plan my API/ })).toBeDisabled()
  })

  it('shows how many characters are over the limit and blocks sending', () => {
    render(
      <RequestCard
        value={'a'.repeat(2040)}
        onChange={() => {}}
        onSubmit={() => {}}
      />,
    )

    expect(screen.getByText('Too long by 40 characters')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Plan my API/ })).toBeDisabled()
  })

  it('sends once with Ctrl+Enter', () => {
    const onSubmit = vi.fn()
    render(
      <RequestCard
        value="A bookshop"
        onChange={() => {}}
        onSubmit={onSubmit}
      />,
    )

    fireEvent.keyDown(screen.getByRole('textbox'), {
      key: 'Enter',
      ctrlKey: true,
    })

    expect(onSubmit).toHaveBeenCalledTimes(1)
  })

  it('does not send while a request is already running', () => {
    const onSubmit = vi.fn()
    render(
      <RequestCard
        value="A bookshop"
        onChange={() => {}}
        onSubmit={onSubmit}
        loading
      />,
    )

    fireEvent.keyDown(screen.getByRole('textbox'), {
      key: 'Enter',
      ctrlKey: true,
    })

    expect(onSubmit).not.toHaveBeenCalled()
  })
})

describe('Sidebar', () => {
  it('shows the empty message when there are no projects', () => {
    render(
      <Sidebar
        projects={[]}
        activeId={null}
        onNewProject={() => {}}
        onSelect={() => {}}
      />,
    )

    expect(screen.getByText(/No projects yet/)).toBeInTheDocument()
  })

  it('marks the active project', () => {
    render(
      <Sidebar
        projects={[
          { id: '1', name: 'Bookshop API', status: 'ready', when: 'Yesterday' },
        ]}
        activeId="1"
        onNewProject={() => {}}
        onSelect={() => {}}
      />,
    )

    expect(
      screen.getByRole('button', { name: /Bookshop API/ }),
    ).toHaveAttribute('aria-current', 'true')
  })
})
