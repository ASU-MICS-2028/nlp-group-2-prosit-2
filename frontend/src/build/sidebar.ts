// Turns the API's project row into the row the Sidebar component draws.

import type { ProjectSummary as ApiProject } from '../api/client'
import type { ProjectSummary as SidebarProject } from '../components/Sidebar'
import { toStatus, type BuildState } from './buildState'

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

// The text that tells useProjectList when to fetch the sidebar list again: when a project opens, when its
// status changes, and once more when the agent's first "Thinking" step arrives. That first sentence is where
// the backend reads the API's short name ("Building a Reading Club Library API with…"), so fetching then
// shows the name straight away instead of only when the build ends. Later steps don't change the text.
export function listRefreshKey(
  projectId: string | null,
  build: BuildState,
): string {
  const named = build.steps.some((step) => step.kind === 'Thinking')
    ? 'named'
    : 'unnamed'
  return `${projectId ?? 'none'}:${build.status}:${named}`
}
