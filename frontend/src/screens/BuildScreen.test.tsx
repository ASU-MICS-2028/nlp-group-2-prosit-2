import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { parseEvent } from '../api/events'
import { applyEvent, emptyBuild, type BuildState } from '../build/buildState'
import realBuild from '../build/realBuildEvents.json'
import { BuildScreen } from './BuildScreen'

// A real build from the backend (see learnings/frontend.md): three tries, a fix, then success.
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

describe('BuildScreen timeline', () => {
  it('shows plain lines first, with no file names', () => {
    const { container } = show(readyBuild)

    const [plainList] = container.querySelectorAll('ol.steps')
    expect(plainList.textContent).toContain('Putting your plan into action…')
    expect(plainList.textContent).toContain('Testing your API…')
    expect(plainList.textContent).toContain('Finalizing your API…')
    expect(plainList.textContent).not.toMatch(/\.py|calc/)
    expect(screen.getByText('Your API passed its tests')).toBeInTheDocument()
  })

  it('keeps the exact steps folded away under "Show details"', () => {
    const { container } = show(readyBuild)

    const details = container.querySelector('details')
    expect(details).not.toBeNull()
    expect(details).not.toHaveAttribute('open') // closed until someone opens it
    expect(screen.getByText('Show details')).toBeInTheDocument()
    expect(details?.textContent).toContain('Writing calc.py')
  })

  it('shows no details toggle while there are no steps yet', () => {
    const { container } = show(emptyBuild)

    expect(container.querySelector('details')).toBeNull()
    expect(screen.getByText('Waiting to start')).toBeInTheDocument()
  })

  it('still shows a step from a server that sends no phase', () => {
    const oldServer = applyEvent(emptyBuild, {
      status: 'working',
      step: { kind: 'Doing', text: 'Writing app/main.py', state: 'done' },
    })

    const { container } = show(oldServer)

    const [plainList] = container.querySelectorAll('ol.steps')
    expect(plainList.textContent).toContain('Working on your API…')
    expect(container.querySelector('details')?.textContent).toContain(
      'Writing app/main.py',
    )
  })
})

describe('BuildScreen for a request that was refused', () => {
  // Like the live refusal: try 1 starts, then the agent refuses without writing or testing anything.
  const refused: BuildState = [
    { status: 'working', attempt: 1, max_attempts: 3 },
    {
      status: 'failed',
      step: {
        kind: 'Result',
        text: 'This request cannot be built because it collects personal details without consent.',
        state: 'failed',
        phase: 'finishing',
      },
    },
  ].reduce<BuildState>((state, event) => {
    const parsed = parseEvent(JSON.stringify(event))
    return parsed ? applyEvent(state, parsed) : state
  }, emptyBuild)

  it('shows only the result: the reason, with no steps, no "Finalizing" and no details', () => {
    const { container } = show(refused)

    expect(screen.getByText('Nothing was built')).toBeInTheDocument()
    expect(
      screen.getByText(/cannot be built because it collects personal details/),
    ).toBeInTheDocument()
    expect(container.textContent).not.toContain('Finalizing')
    expect(container.querySelector('details')).toBeNull()
    expect(container.textContent).not.toContain('Attempt')
    expect(screen.getByText('Not built')).toBeInTheDocument() // the header's badge, not "Failed"
    expect(screen.queryByText('Failed')).toBeNull()
  })

  it('keeps the full timeline for a build that failed after real work', () => {
    const { container } = show({ ...readyBuild, status: 'failed' })

    expect(screen.getByText('The build did not finish')).toBeInTheDocument()
    expect(container.querySelector('details')).not.toBeNull()
  })
})
