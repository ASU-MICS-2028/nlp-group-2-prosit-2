import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterAll, describe, expect, it, vi } from 'vitest'
import { parseEvent } from '../api/events'
import { applyEvent, emptyBuild, type BuildState } from '../build/buildState'
import realBuild from '../build/realBuildEvents.json'

// No server needed: the app is pointed at port 1, where nothing listens, so a click really fails.
// The stub must be set before the screen is loaded, because the address is read when config.ts loads.
vi.stubEnv('VITE_API_URL', 'http://localhost:1')
const { BuildScreen } = await import('./BuildScreen')

afterAll(() => {
  vi.unstubAllEnvs()
})

// A real build from the backend (see learnings/frontend.md): ends ready.
const readyBuild: BuildState = (realBuild as unknown[]).reduce<BuildState>(
  (state, event) => {
    const parsed = parseEvent(JSON.stringify(event))
    return parsed ? applyEvent(state, parsed) : state
  },
  emptyBuild,
)

function show(build: BuildState) {
  return render(
    <BuildScreen
      projectId="p_1"
      title="A calculator API"
      build={build}
      error={null}
      onReopen={() => {}}
    />,
  )
}

const BUTTON = { name: /Download your project/ }

describe('the download button', () => {
  it('appears when the project is ready', () => {
    show(readyBuild)

    expect(screen.getByRole('button', BUTTON)).toBeEnabled()
  })

  it.each(['waiting', 'working', 'retrying', 'failed'] as const)(
    'is not offered while the project is %s',
    (status) => {
      show({ ...readyBuild, status })

      expect(screen.queryByRole('button', BUTTON)).not.toBeInTheDocument()
    },
  )

  it('says so in plain words when the server cannot be reached, and can be tried again', async () => {
    show(readyBuild)
    // The Ready screen also asks for the project's details: that one failure is already on screen.
    const before = (await screen.findAllByText(/could not reach the server/))
      .length

    fireEvent.click(screen.getByRole('button', BUTTON))

    // The real connection is refused: a second sentence appears (for the download), not a crash or a blank screen.
    await waitFor(() =>
      expect(screen.getAllByText(/could not reach the server/)).toHaveLength(
        before + 1,
      ),
    )
    await waitFor(() =>
      expect(screen.getByRole('button', BUTTON)).toBeEnabled(),
    )
  })
})
