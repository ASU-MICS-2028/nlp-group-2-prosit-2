// Live tests: the whole page against a REAL backend. Nothing is faked.
// They only run when VITE_LIVE_API=1 is set (CI skips them).
//
// How to run:
//   1. Terminal 1 (repo root):  source backend/.venv/bin/activate && uvicorn backend.main:app
//   2. Terminal 2 (frontend/):  VITE_LIVE_API=1 npm test -- --run App.live
//      (Windows PowerShell:     $env:VITE_LIVE_API=1; npm test -- --run App.live)

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { listProjects } from './api/client'

function typeRequest(text: string) {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: text } })
}

describe.skipIf(!import.meta.env.VITE_LIVE_API)(
  'the page against a real backend',
  () => {
    it('sends a request and shows the new project waiting, in the timeline and the sidebar', async () => {
      render(<App />)
      typeRequest('A bookshop where I can add books')

      fireEvent.click(screen.getByRole('button', { name: /Plan my API/ }))

      // The timeline's status badge (role "status") shows the real "waiting" event.
      // Several things on the page have this role (notices too), so look for the one that says "Waiting".
      await waitFor(() =>
        expect(
          screen
            .getAllByRole('status')
            .some((element) => element.textContent === 'Waiting'),
        ).toBe(true),
      )
      expect(await screen.findByText('Waiting to start')).toBeInTheDocument()
      // The sidebar lists the project under its stand-in name (the start of the request).
      // Other tests share this backend and used the same text, so there may be several rows: at least one.
      const rows = await screen.findAllByRole('button', {
        name: /A bookshop where I can add books/,
      })
      expect(rows.length).toBeGreaterThanOrEqual(1)
    })

    it('a double click creates only one project', async () => {
      const before = (await listProjects()).length
      render(<App />)
      typeRequest('A garden planner API')
      const send = screen.getByRole('button', { name: /Plan my API/ })

      fireEvent.click(send)
      fireEvent.click(send)
      await screen.findByText('Waiting to start')

      const after = (await listProjects()).length
      expect(after - before).toBe(1)
    })

    it('"New project" then picking the project again replays its timeline', async () => {
      render(<App />)
      typeRequest('A recipe book API for the sidebar test')
      fireEvent.click(screen.getByRole('button', { name: /Plan my API/ }))
      await screen.findByText('Waiting to start')

      fireEvent.click(screen.getByRole('button', { name: /New project/ }))
      expect(
        screen.getByRole('heading', { name: 'What should your API do?' }),
      ).toBeInTheDocument()

      fireEvent.click(
        await screen.findByRole('button', {
          name: /A recipe book API for the/,
        }),
      )

      expect(await screen.findByText('Waiting to start')).toBeInTheDocument()
    })
  },
)
