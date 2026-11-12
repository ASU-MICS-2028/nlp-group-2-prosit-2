// The only place that calls the backend with fetch (D-001, D-004).
// The data shapes come from schema.ts, which is generated from the backend's own description
// of itself. If the backend changes a shape, `npm run api:generate` updates the types and
// TypeScript points at every line that no longer fits.

import { API_URL } from '../config'
import type { components } from './schema'

export type StartResponse = components['schemas']['StartResponse']
export type ProjectResponse = components['schemas']['ProjectResponse']
export type ProjectSummary = components['schemas']['ProjectSummary']
export type Health = components['schemas']['Health']

// A free-tier server can be asleep and take about half a minute to wake up.
const TIMEOUT_MS = 30_000

// Every failure becomes an ApiError whose message is a sentence we can show to a user as it is.
export class ApiError extends Error {
  // The HTTP status code (404, 422, ...), or null when there was no answer at all.
  status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const OFFLINE_MESSAGE =
  'We could not reach the server. Check your internet connection and try again.'
const SLOW_MESSAGE =
  'The server is taking too long. It may be waking up, so please try again in a moment.'
const GENERIC_MESSAGE = 'Something went wrong on our side. Please try again.'

// Our backend answers errors as {"detail": "a plain sentence"}. Use that sentence when it is there.
// Anything else (an HTML error page from the host, an empty body) gets the generic sentence.
async function messageFromResponse(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const detail = body.detail
      if (typeof detail === 'string' && detail !== '') return detail
    }
  } catch {
    // The body was not JSON. Fall through to the generic sentence.
  }
  return GENERIC_MESSAGE
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // AbortController lets us cancel the request when the timer runs out.
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      signal: controller.signal,
    })
    if (!response.ok) {
      throw new ApiError(await messageFromResponse(response), response.status)
    }
    try {
      return (await response.json()) as T
    } catch {
      // The server answered, but not with JSON. That is not an offline problem.
      throw new ApiError(GENERIC_MESSAGE, response.status)
    }
  } catch (error) {
    if (error instanceof ApiError) throw error
    // fetch itself failed: no answer came back.
    throw new ApiError(timedOut ? SLOW_MESSAGE : OFFLINE_MESSAGE, null)
  } finally {
    // Always stop the timer, so a finished request does not abort later.
    clearTimeout(timer)
  }
}

export function getHealth(): Promise<Health> {
  return request<Health>('/health')
}

// The sidebar list: newest first, as the backend sorts it (W-8).
export function listProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>('/projects')
}

export function startProject(requestText: string): Promise<StartResponse> {
  return request<StartResponse>('/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request: requestText }),
  })
}

export function getProject(projectId: string): Promise<ProjectResponse> {
  // encodeURIComponent keeps odd characters in an id from changing the address.
  return request<ProjectResponse>(`/projects/${encodeURIComponent(projectId)}`)
}

// The live progress stream is not a normal request: the browser's EventSource keeps it open.
// This only builds its address; the hook that reads it comes in W-7.
export function eventsUrl(projectId: string): string {
  return `${API_URL}/projects/${encodeURIComponent(projectId)}/events`
}
