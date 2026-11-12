// What the screen knows about one project's build, and how each new event changes it.
// Plain functions, no React and no network, so every rule is easy to test.

import type { BuildEvent } from '../api/events'
import type { BuildStep, TestResult } from '../components/BuildTimeline'
import type { Status } from '../components/StatusPill'

export type BuildState = {
  status: Status
  steps: BuildStep[]
  tests: TestResult[]
  // null means "the server has not told us". We never invent these numbers.
  attempt: number | null
  maxAttempts: number | null
}

export const emptyBuild: BuildState = {
  status: 'waiting',
  steps: [],
  tests: [],
  attempt: null,
  maxAttempts: null,
}

const STATUSES: Status[] = [
  'working',
  'waiting',
  'retrying',
  'passed',
  'ready',
  'failed',
  'stopped',
]

// The server sends words; the UI only knows these exact ones. An unknown word means
// "something is happening that we do not have a name for", so show it as working.
export function toStatus(word: string): Status {
  return STATUSES.find((status) => status === word) ?? 'working'
}

// After one of these nothing more will happen, and the server hangs up.
export function isFinal(status: Status): boolean {
  return status === 'ready' || status === 'failed' || status === 'stopped'
}

function toStep(step: NonNullable<BuildEvent['step']>): BuildStep | null {
  const { kind, text, output, state } = step
  if (kind !== 'Thinking' && kind !== 'Doing' && kind !== 'Result') return null
  const known = state === 'done' || state === 'current' || state === 'failed'
  const checked: BuildStep = { kind, text, state: known ? state : 'done' }
  return output ? { ...checked, output } : checked
}

function toTests(words: string[]): TestResult[] {
  return words.map((word) =>
    word === 'pass' || word === 'fail' ? word : 'pending',
  )
}

// Returns a NEW state (React needs a new object to notice a change).
export function applyEvent(state: BuildState, event: BuildEvent): BuildState {
  const step = event.step ? toStep(event.step) : null
  return {
    status: toStatus(event.status),
    steps: step ? [...state.steps, step] : state.steps,
    tests: event.tests ? toTests(event.tests) : state.tests,
    attempt: event.attempt ?? state.attempt,
    maxAttempts: event.maxAttempts ?? state.maxAttempts,
  }
}
