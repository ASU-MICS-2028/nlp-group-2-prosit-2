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

// Each phase has a few ways to say the same thing. The FIRST one is the fixed wording: finished lines always
// use it, so the history does not change under the reader's eyes. Only the line happening now rotates
// through the others (Elise's idea: like Claude's changing words while it works), so waiting is less boring.
const WORDS: Record<string, string[]> = {
  writing: [
    'Putting your plan into action…',
    'Building the pieces of your API…',
    'Bringing your idea to life…',
    'Putting it all together…',
  ],
  testing: [
    'Testing your API…',
    'Checking that everything works…',
    'Making sure it behaves…',
    'Trying it out…',
  ],
  fixing: [
    'Fixing a problem and trying again…',
    'Smoothing out a problem…',
    'Finding a better way…',
  ],
  finishing: [
    'Finalizing your API…',
    'Adding the finishing touches…',
    'Almost there…',
  ],
  // A step without a phase (an old server, or a kind of step we do not know yet).
  unknown: ['Working on your API…', 'Still working on it…'],
}

// Which wording to show now: `tick` counts up over time, % wraps it back to the start of the list.
function wordFor(key: string, tick: number): string {
  const options = WORDS[key]
  return options[tick % options.length]
}

// One plain line, whether following steps of the same kind should join it, and which WORDS it may rotate through.
type Plain = {
  line: BuildStep
  joinKey: string | null
  wordsKey: string | null
}

function plainLine(step: BuildStep): Plain {
  const failed = step.state === 'failed'

  if (step.phase === 'planning') {
    // The AI's opening sentence ("Building a Bookshop API with 4 endpoints.") is already plain: keep it.
    return {
      line: { kind: 'Thinking', text: step.text, state: step.state },
      joinKey: null,
      wordsKey: null, // the plan sentence is the AI's own words: never swapped
    }
  }

  if (step.phase === 'testing') {
    // Every test run is its own line, so a person can see the tests being run again after a fix.
    if (step.kind === 'Result') {
      const text = failed ? 'Some tests did not pass' : 'Tests passed'
      return {
        line: { kind: 'Result', text, state: step.state },
        joinKey: null,
        wordsKey: null, // a result is a fact, not a waiting line
      }
    }
    const text = WORDS.testing[0]
    return {
      line: { kind: 'Doing', text, state: step.state },
      joinKey: null,
      wordsKey: 'testing',
    }
  }

  if (step.phase === 'writing' && failed) {
    // A problem with a file stands on its own line, so it is not hidden inside "Putting your plan into action".
    const text = 'A file could not be written. Trying again.'
    return {
      line: { kind: 'Result', text, state: 'failed' },
      joinKey: null,
      wordsKey: null,
    }
  }

  // The rest are many steps that say the same thing to a non-developer, so they join into one line.
  const phase = step.phase ?? 'unknown'
  const text = WORDS[phase][0]
  const kind = phase === 'fixing' ? 'Thinking' : 'Doing'
  return {
    line: { kind, text, state: step.state },
    joinKey: phase,
    wordsKey: phase,
  }
}

// `tick` is a number that grows over time (see useTick). It only changes the wording of the line happening now.
export function toPlainSteps(
  steps: BuildStep[],
  status: Status,
  tick = 0,
): BuildStep[] {
  const lines: BuildStep[] = []
  let lastWordsKey: string | null = null // which WORDS the newest line may rotate through, if any
  let lastJoinKey: string | null = null // the kind of the previous line, if later steps may join it

  // A try that failed ends with a "finishing" step, but the build goes on (a new try starts). "Finalizing
  // your API…" in the middle of a build would be wrong, so a "finishing" step only counts when nothing
  // else comes after it. Everything is still in the details.
  const lastOther = steps.findLastIndex((step) => step.phase !== 'finishing')

  for (const [index, step] of steps.entries()) {
    if (step.phase === 'finishing' && index < lastOther) continue
    const { line, joinKey, wordsKey } = plainLine(step)
    const previous = lines[lines.length - 1]

    if (joinKey !== null && joinKey === lastJoinKey && previous) {
      // Same kind as the line before: do not add a line. If any joined step failed, the line shows it.
      if (line.state === 'failed') previous.state = 'failed'
    } else {
      lines.push(line)
    }
    lastJoinKey = joinKey
    lastWordsKey = wordsKey
  }

  // While the build is still going, the newest line is the one happening now.
  const newest = lines[lines.length - 1]
  if (newest && !isFinal(status) && newest.state === 'done') {
    newest.state = 'current'
    if (lastWordsKey !== null && newest.state === 'current') {
      newest.text = wordFor(lastWordsKey, tick)
    }
  }
  return lines
}
