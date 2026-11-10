import { LogOut } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { AppShell } from './components/AppShell'
import { BuildTimeline } from './components/BuildTimeline'
import { Button } from './components/Button'
import { CannotBuildNotice } from './components/CannotBuildNotice'
import { Chip } from './components/Chip'
import { Notice } from './components/Notice'
import { PlanCard } from './components/PlanCard'
import { QuestionFlow } from './components/QuestionFlow'
import { ReadyCard } from './components/ReadyCard'
import { RequestCard } from './components/RequestCard'
import { Sidebar } from './components/Sidebar'
import { LoginCard } from './prototype/LoginCard'
import { MemoryCard } from './prototype/MemoryCard'
import {
  downloadZip,
  listProjects,
  testsOf,
  toQuestion,
  toStatus,
  toSteps,
  whenText,
  type ProjectRow,
  type User,
} from './prototype/api'
import { useAuth } from './prototype/useAuth'
import {
  projectIdFromAddress,
  usePrototypeBuilder,
} from './prototype/usePrototypeBuilder'

// LOCAL ONLY: same layout as the team Start screen, wired to the prototype backend.

const EXAMPLES = [
  {
    label: 'Bookshop API',
    text: 'A bookshop where I can add books and see which ones are in stock.',
  },
  {
    label: 'Clinic appointments',
    text: 'A clinic where patients can book, change and cancel appointments.',
  },
  {
    label: 'Farm produce orders',
    text: 'A farm where buyers can order produce and I can see what to deliver.',
  },
]

// The prototype backend rejects requests shorter than this (models.py: min_length=10)
const MIN_LENGTH = 10

// Steps 4 and 5: say plainly what helped, so nothing is used behind the person's back
function helpUsed(
  understanding:
    { memories_used?: string[]; examples_used?: string[] } | undefined,
): string {
  const notes = understanding?.memories_used?.length ?? 0
  const examples = understanding?.examples_used ?? []
  const parts: string[] = []
  if (notes > 0) parts.push(`${notes} note${notes === 1 ? '' : 's'} about you`)
  if (examples.length > 0) parts.push(`similar designs: ${examples.join(', ')}`)
  return parts.length > 0 ? `I used ${parts.join(' and ')}.` : ''
}

// The page before logging in: no sidebar or menu (there are no projects to show yet),
// just the brand, one headline and the login card, centred.
function AuthPage({ children }: { children: ReactNode }) {
  return (
    <main className="auth haze">
      <div className="auth__panel">
        <div className="auth__brand">
          <span className="logo-tile" aria-hidden>
            {'{ }'}
          </span>
          <span className="t-title">Mesora</span>
        </div>
        {children}
      </div>
    </main>
  )
}

// Step 2: nobody reaches the builder without logging in
function App() {
  const auth = useAuth()

  if (auth.checking) {
    return (
      <AuthPage>
        <p className="muted" role="status">
          Checking your login…
        </p>
      </AuthPage>
    )
  }

  if (!auth.user) {
    return (
      <AuthPage>
        <div className="auth__intro">
          <h1 className="auth__title">Log in to build your API</h1>
          <p className="hero__subtitle">
            Describe an API in plain words, check the plan, and download a
            tested project.
          </p>
        </div>
        <LoginCard
          busy={auth.busy}
          error={auth.error}
          onLogIn={auth.logIn}
          onSignUp={auth.signUp}
        />
      </AuthPage>
    )
  }

  // key: a different person gets a fresh builder, never the last person's half-finished project
  return <Builder key={auth.user.id} user={auth.user} onLogOut={auth.logOut} />
}

// The slim account bar at the very top of the main column
function AccountBar({ user, onLogOut }: { user: User; onLogOut: () => void }) {
  return (
    <header className="topbar">
      <div className="account" aria-label="Your account">
        <span className="avatar" aria-hidden>
          {user.email.charAt(0).toUpperCase()}
        </span>
        <span className="account__text">
          <span className="t-label">{user.email}</span>
          <span className="t-caption muted">
            {user.role === 'admin' ? 'Admin' : 'Signed in'}
          </span>
        </span>
        <Button variant="ghost" onClick={onLogOut}>
          <LogOut size={16} aria-hidden />
          Log out
        </Button>
      </div>
    </header>
  )
}

function Builder({ user, onLogOut }: { user: User; onLogOut: () => void }) {
  const [request, setRequest] = useState('')
  const [downloadError, setDownloadError] = useState<string | undefined>()
  const [projects, setProjects] = useState<ProjectRow[]>([])
  const builder = usePrototypeBuilder()
  const { step, session, plan, job, busy, error } = builder
  const tooShort =
    request.trim().length > 0 && request.trim().length < MIN_LENGTH
  const understanding = session?.understanding
  const tests = job?.tests ?? []
  const openProject = builder.open

  // After a refresh, reopen the project named in the address (#project=<id>). Once, on load.
  useEffect(() => {
    const saved = projectIdFromAddress()
    if (saved) openProject(saved)
    // openProject is deliberately left out: this must run only once, when the page loads
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Keep the sidebar list fresh whenever the open project moves on
  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setProjects([])) // the sidebar then shows its empty message
  }, [session?.id, step, job?.status])

  function startOver() {
    setDownloadError(undefined)
    builder.startOver()
  }

  async function download(jobId: string, title: string) {
    setDownloadError(undefined)
    try {
      await downloadZip(
        jobId,
        `${title.toLowerCase().replace(/\s+/g, '-')}.zip`,
      )
    } catch (caught) {
      setDownloadError(
        caught instanceof Error
          ? caught.message
          : 'The download did not start.',
      )
    }
  }

  return (
    <AppShell
      sidebar={
        <Sidebar
          projects={projects.map((project) => ({
            id: project.id,
            name: project.name,
            status: project.status,
            when: whenText(project.created_at),
          }))}
          activeId={session?.id ?? null}
          onNewProject={() => {
            setRequest('')
            startOver()
          }}
          onSelect={(id) => {
            setDownloadError(undefined)
            openProject(id)
          }}
        />
      }
    >
      <div className="workspace">
        <AccountBar user={user} onLogOut={onLogOut} />

        {step === 'start' && (
          <>
            <div className="hero">
              <span className="t-caption accent-text">New project</span>
              <h1 className="t-display hero__title">
                What should your API do?
              </h1>
              <p className="hero__subtitle">
                Describe it in your own words. I will ask a few quick questions,
                show you a plan to check, then build and test the API for you to
                download.
              </p>
            </div>
            <RequestCard
              value={request}
              onChange={setRequest}
              loading={busy}
              onSubmit={() => {
                if (!tooShort) builder.start(request.trim())
              }}
            />
            <div className="start__chips" aria-label="Example requests">
              {EXAMPLES.map((example) => (
                <Chip
                  key={example.label}
                  label={example.label}
                  onClick={() => setRequest(example.text)}
                />
              ))}
            </div>
            {tooShort && (
              <Notice tone="info" title="Tell us a little more">
                Use at least {MIN_LENGTH} characters so the builder understands
                what you need.
              </Notice>
            )}
            <MemoryCard />
          </>
        )}

        {step !== 'start' && session && (
          <div className="recap">
            <span className="t-caption accent-text">Your request</span>
            <p className="recap__text">{session.requirement}</p>
          </div>
        )}

        {step === 'cannot' && understanding && (
          <CannotBuildNotice
            reason={session?.status === 'refused' ? 'refused' : 'unsupported'}
            message={understanding.message}
            alternative={understanding.alternative ?? undefined}
            onStartOver={startOver}
          />
        )}

        {step === 'questions' && understanding && (
          <>
            {understanding.message && (
              <Notice tone="info" title="A few quick questions">
                {understanding.message}
              </Notice>
            )}
            <QuestionFlow
              // A new session means new questions, so start the flow afresh
              key={session?.id}
              questions={understanding.questions.map(toQuestion)}
              busy={busy}
              onSubmit={builder.answer}
            />
          </>
        )}

        {step === 'plan' && plan && (
          <>
            {helpUsed(understanding) && (
              <span className="t-caption muted">{helpUsed(understanding)}</span>
            )}
            {/* The prototype can offer a smaller plan when the request was too big */}
            {understanding?.verdict === 'unsupported' && (
              <CannotBuildNotice
                reason="unsupported"
                message={understanding.message}
                alternative={understanding.alternative ?? undefined}
                onStartOver={startOver}
              />
            )}
            <PlanCard
              plan={plan}
              onPlanChange={builder.setPlan}
              onApprove={builder.approve}
              onChange={startOver}
            />
          </>
        )}

        {/* While building: one line per stage. When it is done, the ready card takes its place. */}
        {step === 'building' && job && job.status !== 'succeeded' && (
          <>
            <BuildTimeline
              title={`Building ${job.title ?? plan?.name ?? 'your API'}`}
              status={toStatus(job)}
              tests={testsOf(job)}
              steps={toSteps(job)}
            />
            {job.status === 'failed' && (
              <div>
                <Button onClick={builder.backToPlan}>Back to the plan</Button>
              </div>
            )}
          </>
        )}

        {step === 'building' && job?.status === 'succeeded' && (
          <>
            <ReadyCard
              fileCount={job.files.length}
              testsPassed={
                tests.length > 0
                  ? tests.filter((test) => test.passed).length
                  : undefined
              }
              testsTotal={tests.length > 0 ? tests.length : undefined}
              runCommand="Start.bat"
              onDownload={() => download(job.id, job.title ?? 'api-project')}
              downloadError={downloadError}
            />
            {/* Step 3: each generated API has its own two keys, in the zip's .env file */}
            <Notice tone="info" title="Your API has two keys">
              They are in the .env file inside the zip (open it with Notepad).
              EDITOR_KEY can add, edit and delete: keep it private. READER_KEY
              can only look: you can share it.
            </Notice>
          </>
        )}

        {/* While building, the timeline itself shows progress, so no extra notice */}
        {busy && step !== 'start' && step !== 'building' && (
          <Notice tone="info" title="Working on it">
            The builder is thinking. This usually takes under a minute.
          </Notice>
        )}

        {error && (
          <Notice tone="error" title="We could not finish that step">
            {error}
          </Notice>
        )}
      </div>
    </AppShell>
  )
}

export default App
