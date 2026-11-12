import { describe, expect, it } from 'vitest'
import { applyEvent, emptyBuild, isFinal, toStatus } from './buildState'

describe('applyEvent', () => {
  it('starts as waiting with nothing invented', () => {
    expect(emptyBuild).toEqual({
      status: 'waiting',
      steps: [],
      tests: [],
      attempt: null,
      maxAttempts: null,
    })
  })

  it('the real "waiting" event changes nothing but the status word', () => {
    const state = applyEvent(emptyBuild, { status: 'waiting' })

    expect(state).toEqual(emptyBuild)
  })

  it('adds each step to the end of the timeline, in order', () => {
    const one = applyEvent(emptyBuild, {
      status: 'working',
      step: { kind: 'Doing', text: 'Writing app/main.py', state: 'done' },
    })
    const two = applyEvent(one, {
      status: 'working',
      step: { kind: 'Result', text: 'Wrote app/main.py', state: 'done' },
    })

    expect(two.steps.map((step) => step.text)).toEqual([
      'Writing app/main.py',
      'Wrote app/main.py',
    ])
    expect(one.steps).toHaveLength(1) // the earlier state is not changed in place
  })

  it('keeps the test output of a failed step', () => {
    const state = applyEvent(emptyBuild, {
      status: 'working',
      step: {
        kind: 'Result',
        text: 'Tests failed',
        output: 'FAILED test_x',
        state: 'failed',
      },
    })

    expect(state.steps[0].output).toBe('FAILED test_x')
  })

  it('keeps earlier tests and attempt when an event does not carry them', () => {
    const withData = applyEvent(emptyBuild, {
      status: 'retrying',
      attempt: 2,
      maxAttempts: 3,
      tests: ['pass', 'fail'],
    })
    const later = applyEvent(withData, { status: 'working' })

    expect(later.attempt).toBe(2)
    expect(later.maxAttempts).toBe(3)
    expect(later.tests).toEqual(['pass', 'fail'])
  })

  it('shows an unknown test word as pending', () => {
    const state = applyEvent(emptyBuild, {
      status: 'working',
      tests: ['pass', 'skipped'],
    })

    expect(state.tests).toEqual(['pass', 'pending'])
  })

  it('ignores a step with an unknown kind, but still takes the status', () => {
    const state = applyEvent(emptyBuild, {
      status: 'working',
      step: { kind: 'Shouting', text: 'x', state: 'done' },
    })

    expect(state.steps).toEqual([])
    expect(state.status).toBe('working')
  })

  it('treats an unknown step state as done', () => {
    const state = applyEvent(emptyBuild, {
      status: 'working',
      step: { kind: 'Doing', text: 'x', state: 'mystery' },
    })

    expect(state.steps[0].state).toBe('done')
  })
})

describe('toStatus and isFinal', () => {
  it('knows every status word the contract names', () => {
    for (const word of [
      'waiting',
      'working',
      'retrying',
      'ready',
      'failed',
      'stopped',
    ]) {
      expect(toStatus(word)).toBe(word)
    }
  })

  it('shows an unknown word as working', () => {
    expect(toStatus('exploding')).toBe('working')
  })

  it('only ready, failed and stopped are final', () => {
    expect(isFinal('ready')).toBe(true)
    expect(isFinal('failed')).toBe(true)
    expect(isFinal('stopped')).toBe(true)
    expect(isFinal('working')).toBe(false)
    expect(isFinal('waiting')).toBe(false)
    expect(isFinal('retrying')).toBe(false)
  })
})
