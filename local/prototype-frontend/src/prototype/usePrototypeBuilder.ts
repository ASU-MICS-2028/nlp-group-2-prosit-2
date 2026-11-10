// LOCAL ONLY. Runs the whole flow against the prototype backend:
// request → questions → plan → building → ready. All API calls live here, not in components.
import { useEffect, useRef, useState } from 'react'
import type { Plan } from '../components/PlanCard'
import type { AnswerItem } from '../components/answers'
import {
  call,
  toBlueprint,
  toPlan,
  toProtoAnswers,
  type Job,
  type Session,
} from './api'

export type Step = 'start' | 'questions' | 'plan' | 'cannot' | 'building'

const POLL_MS = 1000
// Stop polling after 5 minutes so a stuck build does not poll forever
const MAX_POLLS = 300

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong.'
}

// The open project lives in the address (#project=<id>), so a refresh can reopen it
const HASH_PREFIX = '#project='

export function projectIdFromAddress(): string | null {
  const hash = window.location.hash
  return hash.startsWith(HASH_PREFIX)
    ? hash.slice(HASH_PREFIX.length) || null
    : null
}

function rememberInAddress(sessionId: string | null) {
  // replaceState changes the address without adding a Back-button entry or reloading
  const address = sessionId
    ? `${HASH_PREFIX}${sessionId}`
    : window.location.pathname + window.location.search
  window.history.replaceState(null, '', address)
}

// Which screen a session belongs on
function stepFor(session: Session): Step {
  if (session.status === 'needs_answers') return 'questions'
  if (session.status === 'ready') return 'plan'
  return 'cannot'
}

export function usePrototypeBuilder() {
  const [step, setStep] = useState<Step>('start')
  const [session, setSession] = useState<Session | null>(null)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Goes up on every "start over", so an old polling loop knows to stop
  const runId = useRef(0)

  // When the builder closes (log out, another person logs in, the page changes), stop any build
  // that is still being watched: otherwise its polling loop would keep calling the server.
  useEffect(() => {
    const current = runId
    return () => {
      current.current += 1
    }
  }, [])

  function show(next: Session) {
    rememberInAddress(next.id)
    setSession(next)
    const blueprint = next.understanding.blueprint
    const notIncluded = next.understanding.not_included.map((item) => item.text)
    setPlan(blueprint ? toPlan(blueprint, notIncluded) : null)
    setStep(stepFor(next))
  }

  // Wraps every action: one at a time, busy while running, errors shown as a notice
  async function run(action: () => Promise<void>) {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (caught) {
      setError(messageOf(caught))
    } finally {
      setBusy(false)
    }
  }

  function start(request: string) {
    return run(async () => {
      setJob(null)
      const created = await call<Session>('/sessions', {
        method: 'POST',
        body: JSON.stringify({ requirement: request }),
      })
      show(created)
    })
  }

  function answer(items: AnswerItem[]) {
    return run(async () => {
      if (!session) return
      const answers = toProtoAnswers(session.understanding.questions, items)
      const updated = await call<Session>(`/sessions/${session.id}/answers`, {
        method: 'POST',
        body: JSON.stringify({ answers, skip: items.length === 0 }),
      })
      show(updated)
    })
  }

  async function poll(jobId: string, myRun: number) {
    for (let count = 0; count < MAX_POLLS; count++) {
      if (runId.current !== myRun) return // the person started over
      const current = await call<Job>(`/jobs/${jobId}`).catch(() => {
        throw new Error(
          'The builder restarted and lost this build. Approve the plan again.',
        )
      })
      setJob(current)
      if (current.status === 'succeeded' || current.status === 'failed') return
      await wait(POLL_MS)
    }
    throw new Error('The build is taking too long. Please try again.')
  }

  function approve() {
    return run(async () => {
      const blueprint = session?.understanding.blueprint
      if (!session || !plan || !blueprint) return
      // Save the person's edits first, then build what they approved
      await call<Session>(`/sessions/${session.id}/blueprint`, {
        method: 'PUT',
        body: JSON.stringify(toBlueprint(plan, blueprint)),
      })
      const { job_id } = await call<{ job_id: string }>(
        `/sessions/${session.id}/build`,
        { method: 'POST' },
      )
      setStep('building')
      await poll(job_id, runId.current)
    })
  }

  function backToPlan() {
    setJob(null)
    setStep('plan')
  }

  // Opens a saved project: from the sidebar, or from the address after a refresh.
  // Not wrapped in run(): it may interrupt a build being watched, which then stops polling.
  async function open(sessionId: string) {
    runId.current += 1
    const myRun = runId.current
    const stillMine = () => runId.current === myRun // false once something newer started
    setBusy(true)
    setError(null)
    setJob(null)
    try {
      const found = await call<Session>(`/sessions/${sessionId}`)
      if (!stillMine()) return
      show(found)
      if (found.job_id) {
        const current = await call<Job>(`/jobs/${found.job_id}`)
        if (!stillMine()) return
        setJob(current)
        setStep('building')
        if (current.status === 'queued' || current.status === 'running') {
          await poll(current.id, myRun)
        }
      }
    } catch (caught) {
      if (!stillMine()) return
      // For example someone else's project, or one that no longer exists: go back to the start
      rememberInAddress(null)
      setStep('start')
      setSession(null)
      setError(messageOf(caught))
    } finally {
      if (stillMine()) setBusy(false)
    }
  }

  function startOver() {
    runId.current += 1
    rememberInAddress(null)
    setStep('start')
    setSession(null)
    setPlan(null)
    setJob(null)
    setError(null)
    setBusy(false)
  }

  return {
    step,
    session,
    plan,
    setPlan,
    job,
    busy,
    error,
    start,
    answer,
    approve,
    backToPlan,
    open,
    startOver,
  }
}
