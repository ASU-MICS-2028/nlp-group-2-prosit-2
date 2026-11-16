import { describe, expect, it } from 'vitest'
import { formatWhen, listRefreshKey, toSidebarProject } from './sidebar'
import { emptyBuild, type BuildState } from './buildState'

const NOW = new Date('2026-11-12T12:00:00+00:00')

describe('formatWhen', () => {
  it('says "just now" under a minute', () => {
    expect(formatWhen('2026-11-12T11:59:30+00:00', NOW)).toBe('just now')
  })

  it('says "just now" when the server clock is a little ahead of ours', () => {
    expect(formatWhen('2026-11-12T12:00:05+00:00', NOW)).toBe('just now')
  })

  it('counts minutes and hours', () => {
    expect(formatWhen('2026-11-12T11:55:00+00:00', NOW)).toBe('5 min ago')
    expect(formatWhen('2026-11-12T09:00:00+00:00', NOW)).toBe('3 h ago')
  })

  it('shows a date after a day', () => {
    const result = formatWhen('2026-11-09T12:00:00+00:00', NOW)

    expect(result).not.toContain('ago')
    expect(result).not.toBe('')
  })

  it('reads the exact time format the backend writes (with microseconds and +00:00)', () => {
    // 2 min 59.9 s old: it rounds down, so it never claims more time than has passed.
    expect(formatWhen('2026-11-12T11:57:00.123456+00:00', NOW)).toBe(
      '2 min ago',
    )
  })

  it('shows nothing for a time it cannot read', () => {
    expect(formatWhen('not a time', NOW)).toBe('')
    expect(formatWhen('', NOW)).toBe('')
  })
})

describe('toSidebarProject', () => {
  it('maps the API row to the sidebar row', () => {
    const row = toSidebarProject(
      {
        id: 'p_1',
        name: 'A bookshop where I can add books',
        status: 'working',
        updated_at: '2026-11-12T11:58:00+00:00',
      },
      NOW,
    )

    expect(row).toEqual({
      id: 'p_1',
      name: 'A bookshop where I can add books',
      status: 'working',
      when: '2 min ago',
    })
  })

  it('shows an unknown status word as working', () => {
    const row = toSidebarProject(
      {
        id: 'p_2',
        name: 'x',
        status: 'exploding',
        updated_at: '2026-11-12T11:58:00+00:00',
      },
      NOW,
    )

    expect(row.status).toBe('working')
  })
})

describe('listRefreshKey', () => {
  const thinking = {
    kind: 'Thinking' as const,
    text: 'Building a Reading Club Library API with a books table.',
    state: 'done' as const,
  }
  const doing = {
    kind: 'Doing' as const,
    text: 'Writing app/main.py',
    state: 'done' as const,
  }
  const build = (
    status: BuildState['status'],
    steps: BuildState['steps'],
  ): BuildState => ({ ...emptyBuild, status, steps })

  it('changes when the first Thinking step arrives, so the list is fetched again and shows the API name', () => {
    const before = listRefreshKey('p_1', build('working', []))
    const after = listRefreshKey('p_1', build('working', [thinking]))

    expect(after).not.toBe(before)
  })

  it('does not change for later steps, so the list is not fetched again for every step', () => {
    const first = listRefreshKey('p_1', build('working', [thinking]))
    const later = listRefreshKey(
      'p_1',
      build('working', [thinking, doing, thinking]),
    )

    expect(later).toBe(first)
  })

  it('still changes with the project and its status', () => {
    const working = listRefreshKey('p_1', build('working', [thinking]))

    expect(listRefreshKey('p_1', build('ready', [thinking]))).not.toBe(working)
    expect(listRefreshKey('p_2', build('working', [thinking]))).not.toBe(
      working,
    )
    expect(listRefreshKey(null, build('waiting', []))).toBe(
      'none:waiting:unnamed',
    )
  })
})

describe('toSidebarProject and refused requests', () => {
  const row = (name: string, status: string) => ({
    id: 'p_1',
    name,
    status,
    updated_at: '2026-11-12T11:59:30+00:00',
  })

  it('shows "Not built" for a refused request (the backend names it "… (not built)")', () => {
    const project = toSidebarProject(
      row('Church Website (not built)', 'failed'),
      NOW,
    )

    expect(project.status).toBe('notBuilt')
  })

  it('keeps "failed" for a build that really failed', () => {
    expect(
      toSidebarProject(row('Clinic Appointment API', 'failed'), NOW).status,
    ).toBe('failed')
  })
})
