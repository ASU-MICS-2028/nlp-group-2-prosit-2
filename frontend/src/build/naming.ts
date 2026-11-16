// When the page may show a project's name, and when a build's result is all there is to show.
// The backend names a project from the agent's first sentence ("Building a Clinic API with…", #55);
// until then the only name it has is the start of the typed request, which we don't want to show.

import { isFinal, type BuildState } from './buildState'

// What the sidebar and the title say while we wait for the real name.
export const NAMING = 'Naming your API…'

// Has the agent spoken yet? Its first sentence is where the backend reads the API's name.
export function hasName(build: BuildState): boolean {
  return build.steps.some((step) => step.kind === 'Thinking')
}

// Wait (show "Naming your API…" instead of the Build screen) until the agent has spoken AND the project
// list has been fetched again since then, so the name we show is the real one. A build that has ended
// never waits: a refused request has no name, and its result must show at once.
export function waitingForName(
  build: BuildState,
  listUpToDate: boolean,
): boolean {
  if (isFinal(build.status)) return false
  return !(hasName(build) && listUpToDate)
}

// The build ended without the agent writing or testing anything: a refused request, or one stopped at once
// (for example by the daily limit). Then only the result is worth showing, not the timeline.
export function nothingBuilt(build: BuildState): boolean {
  const ended = build.status === 'failed' || build.status === 'stopped'
  return ended && !build.steps.some((step) => step.kind === 'Doing')
}

// The take-home zip is named after the API: "Clinic Appointment API" -> "clinic-appointment-api.zip".
// Only a-z, 0-9 and "-" are kept, so the name is safe on every computer. The same rule as the backend's
// zip_name (backend/projects.py); the project id is the fallback when nothing usable is left.
export function zipName(name: string, projectId: string): string {
  const words = name.toLowerCase().match(/[a-z0-9]+/g) ?? []
  const slug = words
    .join('-')
    .slice(0, 60)
    .replace(/^-+|-+$/g, '')
  return `${slug || projectId}.zip`
}
