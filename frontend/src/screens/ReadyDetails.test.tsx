import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ProjectResponse } from '../api/client'
import { factsLine } from '../build/readyFacts'
import { ReadyDetails } from './ReadyDetails'

// A project answer as the server sends it, with only the parts a test cares about changed.
function project(changes: Partial<ProjectResponse> = {}): ProjectResponse {
  return {
    id: 'p_1',
    name: 'A notes API',
    status: 'ready',
    file_count: 6,
    size_kb: 5,
    tests_passed: 4,
    tests_total: 4,
    api_url: '/apis/p_1',
    live_status: 'running',
    ...changes,
  }
}

function show(overrides: Partial<Parameters<typeof ReadyDetails>[0]> = {}) {
  const onReload = vi.fn()
  const onWake = vi.fn()
  render(
    <ReadyDetails
      project={project()}
      loading={false}
      error={null}
      onReload={onReload}
      waking={false}
      wakeError={null}
      onWake={onWake}
      {...overrides}
    />,
  )
  return { onReload, onWake }
}

describe('the Ready details', () => {
  it('says it is loading while the details are on their way', () => {
    show({ project: null, loading: true })

    expect(screen.getByRole('status')).toHaveTextContent(/Getting the details/)
  })

  it('shows why the details failed, and tries again when asked', () => {
    const { onReload } = show({
      project: null,
      error: 'We could not reach the server.',
    })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'We could not reach the server.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onReload).toHaveBeenCalledOnce()
  })

  it('shows the facts of the finished project', () => {
    show()

    expect(
      screen.getByText('6 files · 5 KB · 4 of 4 tests passed'),
    ).toBeInTheDocument()
  })

  it('a running API gets a link that opens its own Swagger page in a new tab', () => {
    show()

    const link = screen.getByRole('link', { name: /Open your live API/ })
    expect(link).toHaveAttribute(
      'href',
      expect.stringMatching(/\/apis\/p_1\/docs$/),
    )
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener')) // the new tab cannot reach back into ours
    expect(
      screen.queryByRole('button', { name: /Wake it up/ }),
    ).not.toBeInTheDocument()
  })

  it('a sleeping API offers "Wake it up" and no link', () => {
    const { onWake } = show({ project: project({ live_status: 'sleeping' }) })

    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Wake it up/ }))
    expect(onWake).toHaveBeenCalledOnce()
  })

  it('while waking, the button says so and cannot be clicked again', () => {
    const { onWake } = show({
      project: project({ live_status: 'sleeping' }),
      waking: true,
    })

    const button = screen.getByRole('button', { name: /Waking it up/ })
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(onWake).not.toHaveBeenCalled()
  })

  it('shows the sentence when waking failed', () => {
    show({
      project: project({ live_status: 'sleeping' }),
      wakeError: 'The API could not start. Its code has a problem.',
    })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Its code has a problem',
    )
    expect(screen.getByRole('button', { name: /Wake it up/ })).toBeEnabled() // can try again
  })

  it('a project with no live link says so, and offers neither link nor wake', () => {
    show({ project: project({ api_url: null, live_status: null }) })

    expect(
      screen.getByText(/no live link for this project/),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Wake it up/ }),
    ).not.toBeInTheDocument()
  })
})

describe('factsLine', () => {
  it('says "1 file", not "1 files"', () => {
    expect(factsLine(project({ file_count: 1 }))).toBe(
      '1 file · 5 KB · 4 of 4 tests passed',
    )
  })

  it('leaves out what the server did not send, and never writes "null"', () => {
    const line = factsLine(
      project({
        file_count: null,
        size_kb: null,
        tests_passed: null,
        tests_total: null,
      }),
    )

    expect(line).toBe('')
  })

  it('does not say "0 of 0 tests passed" when no tests were counted', () => {
    expect(factsLine(project({ tests_passed: 0, tests_total: 0 }))).toBe(
      '6 files · 5 KB',
    )
  })

  it('still says so when some tests did not pass', () => {
    expect(factsLine(project({ tests_passed: 3, tests_total: 5 }))).toBe(
      '6 files · 5 KB · 3 of 5 tests passed',
    )
  })

  it('needs both test numbers before it mentions tests', () => {
    expect(factsLine(project({ tests_total: null }))).toBe('6 files · 5 KB')
  })
})
