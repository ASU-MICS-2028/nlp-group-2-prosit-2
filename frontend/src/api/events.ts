// Reading the live progress stream (SSE, "Server-Sent Events").
// The server keeps one connection open and writes a message each time something happens:
//
//   data: {"status":"working","step":{...}}      <- one message: lines starting "data:"
//                                                <- a blank line ends the message
//   : ping                                       <- a comment line the server sends to keep the line open
//
// These functions are plain (no network), so they can be tested without a server.

// One thing that happened to a project (shape: docs/api-contract.md, "events").
// Everything is a plain string here; build/buildState.ts turns the words into the UI's own types.
export type BuildEvent = {
  status: string
  step?: { kind: string; text: string; output?: string; state: string }
  attempt?: number
  maxAttempts?: number
  tests?: string[]
}

// `unknown` is the safe "I don't know what this is yet" type: we must check before using it.
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function readStep(value: unknown): BuildEvent['step'] {
  if (!isRecord(value)) return undefined
  const { kind, text, output, state } = value
  if (typeof kind !== 'string' || typeof text !== 'string') return undefined
  if (typeof state !== 'string') return undefined
  return typeof output === 'string'
    ? { kind, text, output, state }
    : { kind, text, state }
}

// Turn the text of one message into an event. A message we cannot read gives null,
// so one odd message never breaks the whole timeline.
export function parseEvent(text: string): BuildEvent | null {
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch {
    return null
  }
  if (!isRecord(value) || typeof value.status !== 'string') return null

  const event: BuildEvent = { status: value.status }
  const step = readStep(value.step)
  if (step) event.step = step
  if (typeof value.attempt === 'number') event.attempt = value.attempt
  if (typeof value.max_attempts === 'number') {
    event.maxAttempts = value.max_attempts
  }
  if (
    Array.isArray(value.tests) &&
    value.tests.every((test) => typeof test === 'string')
  ) {
    event.tests = value.tests
  }
  return event
}

// Cut the text received so far into finished messages.
// `rest` is the unfinished end: it waits for the next piece of text to arrive.
export function splitMessages(received: string): {
  messages: string[]
  rest: string
} {
  // Some servers end lines with \r\n. Make them all \n so one rule works.
  const parts = received.replace(/\r\n/g, '\n').split('\n\n')
  const rest = parts.pop() ?? '' // the last piece has no blank line after it yet

  const messages: string[] = []
  for (const part of parts) {
    const dataLines = part
      .split('\n')
      .filter((line) => line.startsWith('data:')) // skips ": ping" comments
      .map((line) => line.slice('data:'.length).trimStart())
    if (dataLines.length > 0) messages.push(dataLines.join('\n'))
  }
  return { messages, rest }
}
