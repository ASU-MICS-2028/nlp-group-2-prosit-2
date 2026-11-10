// LOCAL ONLY. Talks to Nana's prototype backend (coding_agent, port 8001) and converts its
// shapes into the team components' shapes. The team backend uses docs/api-contract.md instead,
// so this file must never be copied into the real frontend/.
import type { BuildStep, TestResult } from '../components/BuildTimeline'
import type { Plan } from '../components/PlanCard'
import type { Question } from '../components/QuestionCard'
import type { AnswerItem } from '../components/answers'
import type { FieldType, PlanField } from '../components/fields'
import type { Status } from '../components/StatusPill'
import { API_URL } from '../config'

// ---- Shapes the prototype backend sends (copied from coding_agent/backend/app/models.py) ----

type ProtoField = {
  name: string
  type: FieldType
  required: boolean
  default: string | null
  description: string
  auto: boolean
  links_to?: string | null // only for type "link": the record type it points at
}

// One type of record, e.g. student / students
export type ProtoResource = {
  name: string
  plural: string
  description: string
  fields: ProtoField[]
}

// The whole design: one or more linked record types
export type Blueprint = {
  title: string
  description: string
  resources: ProtoResource[]
}

type ProtoKind =
  'single_choice' | 'multi_choice' | 'yes_no' | 'short_text' | 'editable_list'

export type ProtoQuestion = {
  id: string
  text: string
  kind: ProtoKind
  options: string[]
  allow_other: boolean
  default: string | string[] | null
  why: string
}

type Understanding = {
  verdict: 'clear' | 'vague' | 'reducible' | 'unsupported' | 'disallowed'
  message: string
  blueprint: Blueprint | null
  not_included: { category: string; text: string }[]
  questions: ProtoQuestion[]
  alternative: string | null
  // Steps 4 and 5: what helped the builder understand this request (shown to the person)
  memories_used?: string[]
  examples_used?: string[]
}

export type Session = {
  id: string
  requirement: string
  status: 'needs_answers' | 'ready' | 'unsupported' | 'refused'
  understanding: Understanding
  job_id: string | null
}

export type Job = {
  id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  stage: string
  error: string | null
  title: string | null
  files: string[]
  latency_s: number | null
  // The build timeline and the generated project's own test results (missing on older builds)
  steps?: BuildStep[]
  tests?: { name: string; passed: boolean; message: string }[]
}

// One row in the sidebar (GET /projects)
export type ProjectRow = {
  id: string
  name: string
  status: 'waiting' | 'working' | 'ready' | 'failed' | 'stopped'
  created_at: string
}

// ---- Calling the backend ----

// FastAPI errors look like {"detail": "..."} (or a list of problems for bad input)
function detailOf(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) {
    return null
  }
  const detail = body.detail
  if (typeof detail === 'string') {
    return detail
  }
  return 'Some details are not filled in correctly. Please check the names.'
}

// ---- The login token (step 2) ----
// Kept in sessionStorage: it survives a page refresh but is gone when the tab closes.
// Trade-off: any script running on this page could read it, so the page must never run untrusted code.
const TOKEN_KEY = 'builder-token'

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token)
  } else {
    sessionStorage.removeItem(TOKEN_KEY)
  }
}

// Called when the backend says the login has ended (401), so the app can show the login card
let onLoggedOut: () => void = () => {}
export function setLoggedOutHandler(handler: () => void): void {
  onLoggedOut = handler
}

const UNREACHABLE =
  'Could not reach the prototype backend. Is local/prototype-backend/run.ps1 running?'

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  // Remember which login this request used: a late answer to an old login must not end a newer one
  const usedToken = getToken()
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
    })
  } catch {
    // fetch only throws when the server cannot be reached at all
    throw new Error(UNREACHABLE)
  }
  if (
    response.status === 401 &&
    usedToken !== null &&
    usedToken === getToken()
  ) {
    // The login this request used is still the current one, and the backend no longer accepts it:
    // forget it and go back to the login page
    setToken(null)
    onLoggedOut()
  }
  return response
}

export async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await send(path, init)
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(detailOf(body) ?? 'Something went wrong. Please try again.')
  }
  // We trust our own local backend's shape here; the team app will use a generated, checked client (W-6)
  return body as T
}

// A plain link cannot send the Authorization header, so fetch the zip and save it from memory
export async function downloadZip(
  jobId: string,
  filename: string,
): Promise<void> {
  const response = await send(`/jobs/${jobId}/download`)
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    throw new Error(
      detailOf(body) ?? 'The download did not start. Please try again.',
    )
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  // Free the memory a little later: revoking at once can cancel the save in some browsers.
  // Nothing else changes on the page, so the person can download again or refresh at any time.
  setTimeout(() => URL.revokeObjectURL(url), 30_000)
}

const PROJECT_STATUSES: ProjectRow['status'][] = [
  'waiting',
  'working',
  'ready',
  'failed',
  'stopped',
]

// Rows with a status the sidebar does not know are shown as "waiting" instead of breaking the page
export async function listProjects(): Promise<ProjectRow[]> {
  const rows = await call<ProjectRow[]>('/projects')
  if (!Array.isArray(rows)) return []
  return rows.map((row) => ({
    ...row,
    status: PROJECT_STATUSES.includes(row.status) ? row.status : 'waiting',
  }))
}

// "Just now", "5 minutes ago", "Yesterday", "3 days ago": the sidebar's "when" line
export function whenText(iso: string, now: Date = new Date()): string {
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return ''
  const minutes = Math.floor((now.getTime() - then.getTime()) / 60_000)
  if (minutes < 2) return 'Just now'
  if (minutes < 60) return `${minutes} minutes ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return hours === 1 ? '1 hour ago' : `${hours} hours ago`
  const days = Math.floor(hours / 24)
  return days === 1 ? 'Yesterday' : `${days} days ago`
}

// ---- Accounts (step 2) ----

export type User = { id: number; email: string; role: 'user' | 'admin' }

export async function logIn(email: string, password: string): Promise<User> {
  const result = await call<{ token: string; user: User }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  setToken(result.token)
  return result.user
}

export async function signUp(email: string, password: string): Promise<User> {
  await call<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  return logIn(email, password)
}

export async function logOut(): Promise<void> {
  // Forget the token even if the backend cannot be reached
  await call<null>('/auth/logout', { method: 'POST' }).catch(() => null)
  setToken(null)
}

// ---- Memory (step 4) ----

export type Memory = { id: number; fact: string; created_at: string }

export function listMemories(): Promise<Memory[]> {
  return call<Memory[]>('/memories')
}

export async function forgetMemory(id: number): Promise<void> {
  await call<null>(`/memories/${id}`, { method: 'DELETE' })
}

export async function forgetAllMemories(): Promise<void> {
  await call<null>('/memories', { method: 'DELETE' })
}

export function whoAmI(): Promise<User> {
  return call<User>('/auth/me')
}

// ---- Converting prototype shapes into component shapes ----

export function toQuestion(question: ProtoQuestion): Question {
  // Our components have no "editable list" yet, so it is asked as short text ("a, b, c")
  const kind = question.kind === 'editable_list' ? 'short_text' : question.kind
  return {
    id: question.id,
    text: question.text,
    why: question.why,
    kind,
    options: question.kind === 'editable_list' ? [] : question.options,
  }
}

// QuestionFlow sends text; the prototype wants lists for multi-choice and editable lists
export function toProtoAnswers(
  questions: ProtoQuestion[],
  items: AnswerItem[],
): Record<string, string | string[]> {
  const result: Record<string, string | string[]> = {}
  for (const item of items) {
    const question = questions.find((q) => q.id === item.question_id)
    const isList =
      question?.kind === 'multi_choice' || question?.kind === 'editable_list'
    result[item.question_id] = isList
      ? item.answer
          .split(',')
          .map((part) => part.trim())
          .filter(Boolean)
      : item.answer
  }
  return result
}

// How many checks the generated project runs. Must match count_checks() in the backend's
// scaffold_code.py: 6 for keys and roles, 5 per record type, 3 per link.
export function countChecks(blueprint: Blueprint): number {
  const links = blueprint.resources.reduce(
    (total, resource) =>
      total + resource.fields.filter((field) => field.type === 'link').length,
    0,
  )
  return 6 + 5 * blueprint.resources.length + 3 * links
}

// Before the first build the backend runs, the bar shows this many grey segments
const PROTOTYPE_TEST_COUNT = 11

// "an appointment", "a book": "an" before a vowel sound (good enough for plain record names)
function withArticle(noun: string): string {
  return `${/^[aeiou]/i.test(noun) ? 'an' : 'a'} ${noun}`
}

// The 5 routes the prototype's scaffold creates for each record type
function endpointsFor(resource: ProtoResource): Plan['endpoints'] {
  const path = `/${resource.plural}`
  const one = resource.name.replace(/_/g, ' ')
  const many = resource.plural.replace(/_/g, ' ')
  return [
    { method: 'GET', path, description: `See all ${many}` },
    { method: 'POST', path, description: `Add a new ${one}` },
    { method: 'GET', path: `${path}/{id}`, description: `See one ${one}` },
    {
      method: 'PUT',
      path: `${path}/{id}`,
      description: `Change ${withArticle(one)}`,
    },
    {
      method: 'DELETE',
      path: `${path}/{id}`,
      description: `Remove ${withArticle(one)}`,
    },
  ]
}

export function toPlan(blueprint: Blueprint, notIncluded: string[]): Plan {
  return {
    name: blueprint.title,
    summary: blueprint.description,
    endpoints: blueprint.resources.flatMap(endpointsFor),
    tables: blueprint.resources.map((resource) => ({
      name: resource.plural,
      resourceName: resource.name,
      description: resource.description,
      fields: resource.fields.map((field): PlanField => ({
        name: field.name,
        type: field.type,
        required: field.required,
        auto: field.auto,
        linksTo: field.links_to ?? undefined,
      })),
    })),
    testCount: countChecks(blueprint),
    notIncluded,
  }
}

// Puts the person's edits back into the prototype's blueprint. Tables and record types are in the
// same order (toPlan made one table per record type), and extra details (default, description)
// are kept for fields that kept their name.
export function toBlueprint(plan: Plan, original: Blueprint): Blueprint {
  return {
    ...original,
    title: plan.name,
    resources: original.resources.map((resource, position) => {
      const edited = plan.tables[position]?.fields ?? []
      return {
        ...resource,
        fields: edited.map((field) => {
          const before = resource.fields.find((f) => f.name === field.name)
          return {
            name: field.name.trim(),
            type: field.type,
            required: field.required,
            default: before?.default ?? null,
            description: before?.description ?? '',
            auto: field.auto ?? false,
            links_to: field.type === 'link' ? (field.linksTo ?? null) : null,
          }
        }),
      }
    }),
  }
}

// ---- Turning a job into the build timeline ----

export function toStatus(job: Job): Status {
  if (job.status === 'failed') return 'failed'
  if (job.status !== 'succeeded') return 'working'
  // Built, but some of its own tests failed: say so instead of "Ready"
  return (job.tests ?? []).some((test) => !test.passed) ? 'failed' : 'ready'
}

// The build's stages, in order, one plain line each (the procedure the person watches)
const STAGES: { stage: string; text: string }[] = [
  { stage: 'analyzing', text: 'Reading your design' },
  { stage: 'generating_openapi', text: 'Writing the API description' },
  { stage: 'generating_code', text: 'Building the project files' },
  { stage: 'testing', text: 'Running the tests' },
  { stage: 'packaging', text: 'Packaging the download' },
]

// Stages already passed are "done", the one running now is "current"; later ones are not shown yet
export function toSteps(job: Job): BuildStep[] {
  const reached = STAGES.findIndex((s) => s.stage === job.stage)
  const finished = job.status === 'succeeded'
  const steps: BuildStep[] = []
  STAGES.forEach((s, index) => {
    if (finished || index < reached) {
      steps.push({ kind: 'Doing', text: s.text, state: 'done' })
    } else if (index === reached) {
      steps.push({ kind: 'Doing', text: s.text, state: 'current' })
    }
  })
  if (job.status === 'queued' || (job.status === 'running' && reached === -1)) {
    steps.push({ kind: 'Thinking', text: 'Waiting to start', state: 'current' })
  }
  if (job.status === 'failed') {
    steps.push({
      kind: 'Result',
      text: 'Building stopped. Approve the plan again to retry.',
      output: job.error ?? 'No details were given.',
      state: 'failed',
    })
  }
  return steps
}

// One bar segment per test: real results once they have run, grey "pending" before that
export function testsOf(job: Job): TestResult[] {
  if (job.tests && job.tests.length > 0) {
    return job.tests.map((test): TestResult => (test.passed ? 'pass' : 'fail'))
  }
  return Array.from(
    { length: PROTOTYPE_TEST_COUNT },
    (): TestResult => 'pending',
  )
}
