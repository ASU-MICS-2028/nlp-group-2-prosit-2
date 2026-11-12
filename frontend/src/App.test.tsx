import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterAll, describe, expect, it, vi } from 'vitest'

// These tests need NO server. We point the app at port 1, where nothing is listening,
// so every call really fails (connection refused). Nothing is faked.
// The stub must be set before App is loaded, because the address is read when config.ts loads.
vi.stubEnv('VITE_API_URL', 'http://localhost:1')
const { default: App } = await import('./App')

afterAll(() => {
  vi.unstubAllEnvs()
})

function typeRequest(text: string) {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: text } })
}

describe('Start screen, server unreachable', () => {
  it('asks the one question and shows the empty project list', async () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'What should your API do?' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/No projects yet/)).toBeInTheDocument()
    // The sidebar could not load, and it says so in plain words.
    expect(
      await screen.findByText('We could not load your projects'),
    ).toBeInTheDocument()
  })

  it('fills the box when an example is chosen', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Bookshop API' }))

    expect(screen.getByRole('textbox')).toHaveValue(
      'A bookshop where I can add books and see which ones are in stock.',
    )
  })

  it('does not allow sending an empty or spaces-only request', () => {
    render(<App />)

    const send = screen.getByRole('button', { name: /Plan my API/ })
    expect(send).toBeDisabled()

    typeRequest('     ')
    expect(send).toBeDisabled()
  })

  it('does not allow sending a request over 2000 characters', () => {
    render(<App />)

    typeRequest('a'.repeat(2001))

    expect(screen.getByRole('button', { name: /Plan my API/ })).toBeDisabled()
    expect(screen.getByText(/Too long by 1 characters/)).toBeInTheDocument()
  })

  it('shows a plain error, keeps the text, and lets the person try again', async () => {
    render(<App />)
    typeRequest('A to-do list API')

    fireEvent.click(screen.getByRole('button', { name: /Plan my API/ }))

    expect(
      await screen.findByText('We could not start your project'),
    ).toBeInTheDocument()
    // Errors use role "alert". (The sidebar's own warning has the same sentence, so look inside the alert.)
    expect(
      within(screen.getByRole('alert')).getByText(/could not reach the server/),
    ).toBeInTheDocument()
    // The text is still there, and the button works again.
    expect(screen.getByRole('textbox')).toHaveValue('A to-do list API')
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Plan my API/ })).toBeEnabled(),
    )
  })

  it('sends with the keyboard (Ctrl + Enter) without touching the mouse', async () => {
    render(<App />)
    typeRequest('A clinic API')

    fireEvent.keyDown(screen.getByRole('textbox'), {
      key: 'Enter',
      ctrlKey: true,
    })

    expect(
      await screen.findByText('We could not start your project'),
    ).toBeInTheDocument()
  })

  it('"New project" goes back to the Start screen', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /New project/ }))

    expect(
      screen.getByRole('heading', { name: 'What should your API do?' }),
    ).toBeInTheDocument()
  })
})
