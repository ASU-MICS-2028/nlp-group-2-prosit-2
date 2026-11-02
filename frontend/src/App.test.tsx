import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App (Start screen)', () => {
  it('asks the one question and shows the empty project list', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'What should your API do?' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/No projects yet/)).toBeInTheDocument()
  })

  it('fills the box when an example is chosen', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Bookshop API' }))

    expect(screen.getByRole('textbox')).toHaveValue(
      'A bookshop where I can add books and see which ones are in stock.',
    )
  })

  it('says planning is not connected instead of pretending to work', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Clinic appointments' }))
    fireEvent.click(screen.getByRole('button', { name: /Plan my API/ }))

    expect(
      screen.getByText('Planning is not connected yet'),
    ).toBeInTheDocument()
  })
})
