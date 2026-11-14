// Turns the agent's detailed steps into a short, plain timeline for a non-developer (D-019).
//
// The server sends many technical steps ("Writing app/database.py", "Wrote app/main.py", ...).
// A person who cannot code does not need them, so by default we show one line per phase.
// We decide ONLY from the step's `phase` (a fixed word from the server), never from its sentence,
// so rewording a sentence on the server cannot break this. Every raw step is still available
// under "Show details" (BuildTimeline's `details`).

import type { BuildStep } from '../components/BuildTimeline'
import type { Status } from '../components/StatusPill'
import { isFinal } from './buildState'
import type { Phase } from './phases'

const LINE_FOR_PHASE: Record<Exclude<Phase, 'planning'>, string> = {
  writing: 'Putting your plan into action…',
  testing: 'Testing your API…',
  fixing: 'Fixing a problem and trying again…',
  finishing: 'Finalizing your API…',
}

// A step without a phase (an old server, or a kind of step we do not know yet) gets this line.
const LINE_FOR_UNKNOWN = 'Working on your API…'

// One plain line, and whether following steps of the same kind should join it.
type Plain = { line: BuildStep; joinKey: string | null }

function plainLine(step: BuildStep): Plain {
  const failed = step.state === 'failed'

  if (step.phase === 'planning') {
    // The AI's opening sentence ("Building a Bookshop API with 4 endpoints.") is already plain: keep it.
    return {
      line: { kind: 'Thinking', text: step.text, state: step.state },
      joinKey: null,
    }
  }

  if (step.phase === 'testing') {
    // Every test run is its own line, so a person can see the tests being run again after a fix.
    if (step.kind === 'Result') {
      const text = failed ? 'Some tests did not pass' : 'Tests passed'
      return {
        line: { kind: 'Result', text, state: step.state },
        joinKey: null,
      }
    }
    const text = LINE_FOR_PHASE.testing
    return { line: { kind: 'Doing', text, state: step.state }, joinKey: null }
  }

  if (step.phase === 'writing' && failed) {
    // A problem with a file stands on its own line, so it is not hidden inside "Putting your plan into action".
    const text = 'A file could not be written. Trying again.'
    return { line: { kind: 'Result', text, state: 'failed' }, joinKey: null }
  }

  // The rest are many steps that say the same thing to a non-developer, so they join into one line.
  const phase = step.phase ?? 'unknown'
  const text =
    step.phase === undefined ? LINE_FOR_UNKNOWN : LINE_FOR_PHASE[step.phase]
  const kind = phase === 'fixing' ? 'Thinking' : 'Doing'
  return { line: { kind, text, state: step.state }, joinKey: phase }
}

export function toPlainSteps(steps: BuildStep[], status: Status): BuildStep[] {
  const lines: BuildStep[] = []
  let lastJoinKey: string | null = null // the kind of the previous line, if later steps may join it

  // A try that failed ends with a "finishing" step, but the build goes on (a new try starts). "Finalizing
  // your API…" in the middle of a build would be wrong, so a "finishing" step only counts when nothing
  // else comes after it. Everything is still in the details.
  const lastOther = steps.findLastIndex((step) => step.phase !== 'finishing')

  for (const [index, step] of steps.entries()) {
    if (step.phase === 'finishing' && index < lastOther) continue
    const { line, joinKey } = plainLine(step)
    const previous = lines[lines.length - 1]

    if (joinKey !== null && joinKey === lastJoinKey && previous) {
      // Same kind as the line before: do not add a line. If any joined step failed, the line shows it.
      if (line.state === 'failed') previous.state = 'failed'
    } else {
      lines.push(line)
    }
    lastJoinKey = joinKey
  }

  // While the build is still going, the newest line is the one happening now.
  const newest = lines[lines.length - 1]
  if (newest && !isFinal(status) && newest.state === 'done') {
    newest.state = 'current'
  }
  return lines
}
