import { describe, expect, it } from 'vitest'
import { parseEvent } from '../api/events'
import type { BuildStep } from '../components/BuildTimeline'
import { applyEvent, emptyBuild, type BuildState } from './buildState'
import { toPlainSteps } from './plainSteps'
import realBuild from './realBuildEvents.json'

// A step as the page holds it. Only the parts a test cares about are given.
function step(
  phase: BuildStep['phase'],
  kind: BuildStep['kind'],
  text: string,
  state: BuildStep['state'] = 'done',
): BuildStep {
  return phase ? { kind, text, state, phase } : { kind, text, state }
}

function texts(lines: BuildStep[]): string[] {
  return lines.map((line) => line.text)
}

describe('a real build from the backend', () => {
  // realBuildEvents.json was made by running the backend's retry loop with a pretend AI
  // (see learnings/frontend.md). It holds the real events: three tries, a fix, then success.
  const events = realBuild as unknown[]
  const finalState: BuildState = events.reduce<BuildState>((state, event) => {
    const parsed = parseEvent(JSON.stringify(event))
    return parsed ? applyEvent(state, parsed) : state
  }, emptyBuild)

  it('ends ready, and every step kept its phase', () => {
    expect(finalState.status).toBe('ready')
    expect(finalState.steps.length).toBeGreaterThan(10)
    expect(finalState.steps.every((one) => one.phase !== undefined)).toBe(true)
  })

  it('becomes a short, plain list with no file names', () => {
    const plain = toPlainSteps(finalState.steps, finalState.status)

    expect(texts(plain)).toEqual([
      'Testing your API…',
      'Some tests did not pass',
      'Testing your API…',
      'Some tests did not pass',
      'Testing your API…',
      'Some tests did not pass',
      'Fixing a problem and trying again…',
      'Putting your plan into action…',
      'Testing your API…',
      'Tests passed',
      'Finalizing your API…',
    ])
    for (const line of plain) {
      expect(line.text).not.toMatch(/\.py|app\/|calc/)
      expect(line.output).toBeUndefined() // pytest's text is not shown in the main list
    }
  })

  it('keeps every raw step for "Show details"', () => {
    const raw = texts(finalState.steps).join('\n')

    expect(raw).toContain('Writing calc.py')
    expect(finalState.steps.some((one) => one.output)).toBe(true)
  })
})

describe('toPlainSteps', () => {
  it('gives nothing for no steps', () => {
    expect(toPlainSteps([], 'waiting')).toEqual([])
  })

  it('joins many file steps into one line', () => {
    const lines = toPlainSteps(
      [
        step('writing', 'Doing', 'Writing requirements.txt'),
        step('writing', 'Result', 'Wrote requirements.txt'),
        step('writing', 'Doing', 'Writing app/main.py'),
        step('writing', 'Result', 'Wrote app/main.py'),
      ],
      'ready',
    )

    expect(texts(lines)).toEqual(['Putting your plan into action…'])
  })

  it('keeps the AI’s opening sentence, because it is already plain', () => {
    const lines = toPlainSteps(
      [
        step(
          'planning',
          'Thinking',
          'Building a Bookshop API with 4 endpoints.',
        ),
      ],
      'working',
    )

    expect(texts(lines)).toEqual(['Building a Bookshop API with 4 endpoints.'])
  })

  it('shows a file problem on its own line, not hidden in the writing line', () => {
    const lines = toPlainSteps(
      [
        step('writing', 'Doing', 'Writing a.py'),
        step('writing', 'Result', 'That file name is not allowed.', 'failed'),
        step('writing', 'Doing', 'Writing b.py'),
      ],
      'working',
    )

    expect(texts(lines)).toEqual([
      'Putting your plan into action…',
      'A file could not be written. Trying again.',
      'Putting your plan into action…',
    ])
    expect(lines[1].state).toBe('failed')
  })

  it('shows every test run as its own line', () => {
    const lines = toPlainSteps(
      [
        step('testing', 'Doing', 'Running the tests'),
        step('testing', 'Result', 'Tests failed', 'failed'),
        step('testing', 'Doing', 'Running the tests'),
        step('testing', 'Result', 'Tests passed'),
      ],
      'working',
    )

    expect(texts(lines)).toEqual([
      'Testing your API…',
      'Some tests did not pass',
      'Testing your API…',
      'Tests passed',
    ])
  })

  it('gives a step with no phase a neutral line, and joins several of them', () => {
    const lines = toPlainSteps(
      [
        step(undefined, 'Doing', 'Something new'),
        step(undefined, 'Result', 'Another new thing'),
      ],
      'working',
    )

    expect(texts(lines)).toEqual(['Working on your API…'])
  })

  it('drops a "finishing" step when something comes after it', () => {
    const lines = toPlainSteps(
      [
        step(
          'finishing',
          'Result',
          'The tests still fail after 3 tries.',
          'failed',
        ),
        step('fixing', 'Thinking', 'Asking the AI to fix it.'),
      ],
      'retrying',
    )

    expect(texts(lines)).toEqual(['Fixing a problem and trying again…'])
  })

  it('keeps the last "finishing" steps as one line, and shows a failure', () => {
    const lines = toPlainSteps(
      [
        step('testing', 'Result', 'Tests failed', 'failed'),
        step('finishing', 'Thinking', 'I give up.'),
        step('finishing', 'Result', 'Still not working.', 'failed'),
      ],
      'failed',
    )

    expect(texts(lines)).toEqual([
      'Some tests did not pass',
      'Finalizing your API…',
    ])
    expect(lines[1].state).toBe('failed')
  })

  it('marks the newest line as happening now while the build is going, not after it ends', () => {
    const steps = [step('writing', 'Doing', 'Writing a.py')]

    expect(toPlainSteps(steps, 'working')[0].state).toBe('current')
    expect(toPlainSteps(steps, 'ready')[0].state).toBe('done')
  })

  it('does not change the steps it is given', () => {
    const steps = [
      step('writing', 'Doing', 'Writing a.py'),
      step('writing', 'Result', 'No.', 'failed'),
    ]
    const before = JSON.stringify(steps)

    toPlainSteps(steps, 'working')

    expect(JSON.stringify(steps)).toBe(before)
  })
})

describe('changing words while waiting', () => {
  const going = [
    step('writing', 'Doing', 'Writing a.py'),
    step('testing', 'Doing', 'Running the tests'),
  ]

  it('the line happening now uses a different wording as the tick grows', () => {
    const seen = new Set<string>()
    for (let tick = 0; tick < 8; tick++) {
      const lines = toPlainSteps(going, 'working', tick)
      seen.add(lines[lines.length - 1].text)
    }

    expect(seen.size).toBeGreaterThan(1)
    for (const wording of seen) expect(wording).not.toMatch(/\.py|app\//)
  })

  it('wraps back to the first wording after the last one', () => {
    const first = toPlainSteps(going, 'working', 0)
    const wrapped = toPlainSteps(going, 'working', 4) // testing has 4 wordings

    expect(texts(wrapped)).toEqual(texts(first))
  })

  it('earlier lines never change, so the history stays steady', () => {
    const lines = toPlainSteps(going, 'working', 3)

    expect(lines[0].text).toBe('Putting your plan into action…')
  })

  it('a finished build never changes its words', () => {
    const done = [...going, step('testing', 'Result', 'Tests passed')]

    expect(texts(toPlainSteps(done, 'ready', 3))).toEqual(
      texts(toPlainSteps(done, 'ready', 0)),
    )
  })

  it('the AI’s plan sentence and test results are never swapped', () => {
    const lines = toPlainSteps(
      [
        step('planning', 'Thinking', 'Building a Bookshop API.'),
        step('testing', 'Doing', 'Running the tests'),
        step('testing', 'Result', 'Tests passed'),
      ],
      'working',
      2,
    )

    expect(lines[0].text).toBe('Building a Bookshop API.')
    expect(lines[2].text).toBe('Tests passed')
  })
})
