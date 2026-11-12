import { describe, expect, it } from 'vitest'
import { formatWhen, toSidebarProject } from './sidebar'

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
