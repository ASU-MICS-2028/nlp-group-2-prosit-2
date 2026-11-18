import { fireEvent, render, screen } from '@testing-library/react'
import { afterAll, describe, expect, it, vi } from 'vitest'
import { emptyBuild, type BuildState } from '../build/buildState'

// No server needed: the app is pointed at port 1, where nothing listens, so "Yes, stop it" really fails.
// The real stop is tested against a real backend in client.live.test.ts.
vi.stubEnv('VITE_API_URL', 'http://localhost:1')
const { BuildScreen } = await import('./BuildScreen')

afterAll(() => {
  vi.unstubAllEnvs()
})

const thinking = {
  kind: 'Thinking',
  text: 'Building a Notes API.',
  state: 'done',
} as const
const working: BuildState = {
  ...emptyBuild,
  status: 'working',
  steps: [{ ...thinking }],
} as BuildState

function show(build: BuildState, error: string | null = null) {
  return render(
    <BuildScreen
      projectId="p_1"
      title="Notes API"
      build={build}
      error={error}
      onReopen={() => {}}
    />,
  )
}

const STOP = { name: /Stop build/ }

describe('stopping a build (F-18)', () => {
  it.each(['waiting', 'working', 'retrying'] as const)(
    'offers Stop while the build is %s',
    (status) => {
      show({ ...working, status })

      expect(screen.getByRole('button', STOP)).toBeEnabled()
    },
  )

  it.each(['ready', 'failed', 'stopped'] as const)(
    'offers no Stop once the build is %s',
    (status) => {
      show({ ...working, status })

      expect(screen.queryByRole('button', STOP)).not.toBeInTheDocument()
    },
  )

  it('offers no Stop when the live stream is lost (we do not know if it still runs)', () => {
    show(working, 'The live connection to the server was lost.')

    expect(screen.queryByRole('button', STOP)).not.toBeInTheDocument()
  })

  it('asks first, and "Keep building" goes back without stopping', () => {
    show(working)

    fireEvent.click(screen.getByRole('button', STOP))
    expect(screen.getByText('Stop this build?')).toBeInTheDocument()
    expect(screen.getByText(/Nothing will be kept/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Keep building' }))
    expect(screen.queryByText('Stop this build?')).not.toBeInTheDocument()
    expect(screen.getByRole('button', STOP)).toBeEnabled()
  })

  it('says so in plain words when the server cannot be reached, and can be tried again', async () => {
    show(working)

    fireEvent.click(screen.getByRole('button', STOP))
    fireEvent.click(screen.getByRole('button', { name: 'Yes, stop it' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /could not reach the server/,
    )
    expect(screen.getByRole('button', { name: 'Yes, stop it' })).toBeEnabled()
  })

  it('a stopped build says it was stopped, even if the agent had done nothing yet', () => {
    const stoppedAtOnce: BuildState = {
      ...emptyBuild,
      status: 'stopped',
      steps: [
        {
          kind: 'Result',
          text: 'You stopped this build. Nothing was kept.',
          state: 'failed',
        },
      ],
    } as BuildState
    show(stoppedAtOnce)

    expect(screen.getByText('The build was stopped')).toBeInTheDocument()
    // On the timeline's last line and in the notice.
    expect(
      screen.getAllByText('You stopped this build. Nothing was kept.').length,
    ).toBeGreaterThan(0)
    expect(screen.queryByText('Nothing was built')).not.toBeInTheDocument()
  })
})
