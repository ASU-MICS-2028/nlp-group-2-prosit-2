import { describe, expect, it } from 'vitest'
import { emptyBuild, type BuildState } from './buildState'
import { hasName, nothingBuilt, waitingForName, zipName } from './naming'

const thinking = {
  kind: 'Thinking' as const,
  text: 'Building a Clinic API with patients and appointments tables.',
  state: 'done' as const,
}
const doing = {
  kind: 'Doing' as const,
  text: 'Writing app/main.py',
  state: 'done' as const,
}
const refusal = {
  kind: 'Result' as const,
  text: 'This request cannot be built because it collects personal details without consent.',
  state: 'failed' as const,
}
const build = (
  status: BuildState['status'],
  steps: BuildState['steps'],
): BuildState => ({ ...emptyBuild, status, steps })

describe('hasName', () => {
  it('is false until the agent has said its first sentence', () => {
    expect(hasName(build('working', []))).toBe(false)
    expect(hasName(build('working', [thinking]))).toBe(true)
  })
})

describe('waitingForName', () => {
  it('waits while the agent has not spoken yet', () => {
    expect(waitingForName(build('waiting', []), true)).toBe(true)
    expect(waitingForName(build('working', []), true)).toBe(true)
  })

  it('still waits until the project list has been fetched with the new name', () => {
    expect(waitingForName(build('working', [thinking]), false)).toBe(true)
  })

  it('stops waiting once the name is in and the list is up to date', () => {
    expect(waitingForName(build('working', [thinking]), true)).toBe(false)
  })

  it('never waits for a build that has ended, even without a name (a refusal)', () => {
    expect(waitingForName(build('failed', [refusal]), false)).toBe(false)
    expect(waitingForName(build('ready', [thinking]), false)).toBe(false)
  })
})

describe('nothingBuilt', () => {
  it('is true for a build that failed before the agent wrote or tested anything (a refusal)', () => {
    expect(nothingBuilt(build('failed', [refusal]))).toBe(true)
  })

  it('is false once the agent has done something, so the full timeline stays', () => {
    expect(nothingBuilt(build('failed', [thinking, doing, refusal]))).toBe(
      false,
    )
  })

  it('is false while a build is still going, or when it is ready', () => {
    expect(nothingBuilt(build('working', []))).toBe(false)
    expect(nothingBuilt(build('ready', [thinking, doing]))).toBe(false)
  })
})

describe('zipName', () => {
  // The same rule as the backend's zip_name (backend/projects.py), so both name the file alike.
  it('names the zip after the API', () => {
    expect(zipName('Clinic Appointment API', 'p_7')).toBe(
      'clinic-appointment-api.zip',
    )
    expect(zipName('To-Do List API', 'p_7')).toBe('to-do-list-api.zip')
    expect(zipName('Café & Bakery Orders API', 'p_7')).toBe(
      'caf-bakery-orders-api.zip',
    )
  })

  it('falls back to the project id when nothing usable is left', () => {
    expect(zipName('!!!', 'p_7')).toBe('p_7.zip')
  })
})
