// Turns the API's project row into the row the Sidebar component draws.

import type { ProjectSummary as ApiProject } from '../api/client'
import type { ProjectSummary as SidebarProject } from '../components/Sidebar'
import { toStatus } from './buildState'

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

// "just now", "5 min ago", "3 h ago", or the date for anything older.
// `now` is passed in (not read inside) so a test can use a fixed time.
export function formatWhen(isoTime: string, now: Date): string {
  const time = new Date(isoTime)
  if (Number.isNaN(time.getTime())) return '' // an unreadable time shows nothing, not "Invalid Date"

  const age = now.getTime() - time.getTime()
  if (age < MINUTE) return 'just now' // also covers a small clock difference with the server
  if (age < HOUR) return `${Math.floor(age / MINUTE)} min ago`
  if (age < DAY) return `${Math.floor(age / HOUR)} h ago`
  return time.toLocaleDateString()
}

export function toSidebarProject(
  project: ApiProject,
  now: Date,
): SidebarProject {
  return {
    id: project.id,
    name: project.name,
    status: toStatus(project.status),
    when: formatWhen(project.updated_at, now),
  }
}
