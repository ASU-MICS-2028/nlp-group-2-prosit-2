// The only place that calls the backend with fetch (D-001, D-004).
// The data shapes come from schema.ts, which is generated from the backend's own description
// of itself. If the backend changes a shape, `npm run api:generate` updates the types and
// TypeScript points at every line that no longer fits.

import { API_URL } from '../config'
import { parseEvent, splitMessages, type BuildEvent } from './events'
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

// For any error caught by a screen: our own sentence if it is an ApiError, a generic one otherwise.
export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : GENERIC_MESSAGE
}

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

export function eventsUrl(projectId: string): string {
  return `${API_URL}/projects/${encodeURIComponent(projectId)}/events`
}

const LOST_MESSAGE =
  'The live connection to the server was lost. Open the project again to see where it got to.'

// The live progress stream. It is not a normal request: the server keeps it open and writes
// a message each time something happens, so we read it piece by piece (D-016).
// `onEvent` is called once for every event, oldest first: the server first sends everything
// that happened so far, then new events as they happen. Returns when the server hangs up
// (after a final status) or when `signal` is used to cancel it.
export async function streamEvents(
  projectId: string,
  onEvent: (event: BuildEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let connected = false
  try {
    const response = await fetch(eventsUrl(projectId), {
      signal,
      headers: { Accept: 'text/event-stream' },
    })
    if (!response.ok || response.body === null) {
      throw new ApiError(await messageFromResponse(response), response.status)
    }
    connected = true

    const reader = response.body.getReader()
    const decoder = new TextDecoder() // turns the raw bytes into text
    let received = '' // text that has arrived but is not a finished message yet
    while (true) {
      const { done, value } = await reader.read() // waits until something arrives
      if (done) return // the server hung up
      // stream: true keeps a character that arrives in two pieces together
      received += decoder.decode(value, { stream: true })
      const { messages, rest } = splitMessages(received)
      received = rest
      for (const message of messages) {
        const event = parseEvent(message)
        if (event) onEvent(event)
      }
    }
  } catch (error) {
    if (signal.aborted) return // we hung up on purpose, so it is not a failure
    if (error instanceof ApiError) throw error
    throw new ApiError(connected ? LOST_MESSAGE : OFFLINE_MESSAGE, null)
  }
}
