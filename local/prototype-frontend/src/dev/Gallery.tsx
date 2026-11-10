import { FolderOpen } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { AppShell } from '../components/AppShell'
import { BuildTimeline } from '../components/BuildTimeline'
import { Button } from '../components/Button'
import { CannotBuildNotice } from '../components/CannotBuildNotice'
import { Chip } from '../components/Chip'
import { IconTile } from '../components/IconTile'
import { MethodBadge, type Method } from '../components/MethodBadge'
import { Notice } from '../components/Notice'
import { PlanCard, type Plan } from '../components/PlanCard'
import {
  QuestionCard,
  type Answer,
  type Question,
} from '../components/QuestionCard'
import { QuestionFlow } from '../components/QuestionFlow'
import { ReadyCard } from '../components/ReadyCard'
import { RequestCard } from '../components/RequestCard'
import { Sidebar, type ProjectSummary } from '../components/Sidebar'
import { StatusPill, type Status } from '../components/StatusPill'

// Developer-only page (open /dev/gallery while running `npm run dev`).
// It shows every component in its states so the team can review the design in one place.

const STATUSES: Status[] = [
  'working',
  'waiting',
  'retrying',
  'passed',
  'ready',
  'failed',
  'stopped',
]
const METHODS: Method[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

const PROJECTS: ProjectSummary[] = [
  { id: '1', name: 'Bookshop API', status: 'ready', when: 'Yesterday' },
  { id: '2', name: 'Clinic appointments', status: 'working', when: 'Just now' },
  {
    id: '3',
    name: 'Farm produce orders',
    status: 'stopped',
    when: '3 days ago',
  },
]

const PLAN: Plan = {
  name: 'Bookshop API',
  summary: 'Add books, list them, and see which ones are in stock.',
  endpoints: [
    { method: 'GET', path: '/books', description: 'See all books' },
    { method: 'POST', path: '/books', description: 'Add a new book' },
    { method: 'PUT', path: '/books/{id}', description: 'Change a book' },
    { method: 'DELETE', path: '/books/{id}', description: 'Remove a book' },
  ],
  tables: [
    {
      name: 'books',
      fields: [
        { name: 'id', type: 'int', required: true, auto: true },
        { name: 'title', type: 'str', required: true },
        { name: 'author', type: 'str', required: false },
        { name: 'price', type: 'float', required: false },
        { name: 'in_stock', type: 'bool', required: true },
      ],
    },
  ],
  testCount: 5,
  notIncluded: ['Taking card payments', 'Sending emails to customers'],
}

// One question of each kind, so every layout can be checked
const QUESTIONS: Question[] = [
  {
    id: 'q1',
    text: 'Should each book have a price?',
    why: 'This decides whether we store prices and let you search by price.',
    kind: 'single_choice',
    options: ['Yes, with a price', 'No, just titles'],
  },
  {
    id: 'q2',
    text: 'What else should each book have?',
    why: 'Each one becomes a detail you can fill in.',
    kind: 'multi_choice',
    options: ['Author', 'Year published', 'Cover photo link'],
  },
  {
    id: 'q3',
    text: 'Can people delete books?',
    why: 'Some shops prefer to keep every record.',
    kind: 'yes_no',
    options: [],
  },
  {
    id: 'q4',
    text: 'What is your shop called?',
    why: 'We use it as the name of your API.',
    kind: 'short_text',
    options: [],
  },
]

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="t-title" style={{ margin: 0 }}>
        {title}
      </h2>
      {children}
    </section>
  )
}

export function Gallery() {
  const [request, setRequest] = useState('')
  const [tooLong, setTooLong] = useState('a'.repeat(2040))
  const [answers, setAnswers] = useState<Record<string, Answer>>({
    q1: 'Yes, with a price',
    q2: ['Author'],
    q3: '',
    q4: '',
  })
  const [plan, setPlan] = useState<Plan>(PLAN)
  const [lastSent, setLastSent] = useState('')
  const [chip, setChip] = useState(true)
  const [emptySidebar, setEmptySidebar] = useState(false)

  return (
    <AppShell
      sidebar={
        <Sidebar
          projects={emptySidebar ? [] : PROJECTS}
          activeId="2"
          onNewProject={() => setEmptySidebar(!emptySidebar)}
          onSelect={() => {}}
        />
      }
    >
      <div className="gallery">
        <h1 className="t-display">Component gallery</h1>
        <p className="muted">
          Developer page. Click “New project” in the sidebar to toggle its empty
          state.
        </p>

        <Section title="Buttons">
          <div className="gallery__row">
            <Button variant="primary">Primary</Button>
            <Button>Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="primary" loading>
              Reading your request
            </Button>
            <Button disabled>Disabled</Button>
          </div>
        </Section>

        <Section title="Chips">
          <div className="gallery__row">
            <Chip label="Bookshop API" />
            <Chip label="Clinic appointments" />
            <Chip
              label="Selected answer"
              selected={chip}
              onClick={() => setChip(!chip)}
            />
          </div>
        </Section>

        <Section title="Status pills">
          <div className="gallery__row">
            {STATUSES.map((status) => (
              <StatusPill key={status} status={status} />
            ))}
          </div>
        </Section>

        <Section title="Method badges and icon tile">
          <div className="gallery__row">
            {METHODS.map((method) => (
              <MethodBadge key={method} method={method} />
            ))}
            <IconTile icon={FolderOpen} />
          </div>
        </Section>

        <Section title="Notices">
          <Notice tone="warning" title="The server is waking up">
            The first request after a quiet spell takes about half a minute.
          </Notice>
          <Notice tone="error" title="Something went wrong">
            We could not reach the server. Check your internet and try again.
          </Notice>
          <Notice tone="info" title="Good to know">
            You can change the plan before anything is built.
          </Notice>
          <Notice tone="success" title="Saved">
            Your request was saved.
          </Notice>
        </Section>

        <Section title="Request card (empty, and too long)">
          <RequestCard
            value={request}
            onChange={setRequest}
            onSubmit={() => {}}
          />
          <RequestCard
            value={tooLong}
            onChange={setTooLong}
            onSubmit={() => {}}
          />
          <RequestCard
            value="A bookshop API"
            onChange={() => {}}
            onSubmit={() => {}}
            loading
          />
        </Section>

        <Section title="Question card (each kind)">
          {QUESTIONS.map((question, position) => (
            <QuestionCard
              key={question.id}
              index={position + 1}
              total={QUESTIONS.length}
              question={question}
              answer={answers[question.id]}
              onAnswer={(next) =>
                setAnswers({ ...answers, [question.id]: next })
              }
            />
          ))}
        </Section>

        <Section title="Question flow (one at a time, with Skip)">
          <QuestionFlow
            questions={QUESTIONS}
            onSubmit={(sent) => setLastSent(JSON.stringify(sent))}
          />
          {lastSent && <pre className="well t-code">{lastSent}</pre>}
        </Section>

        <Section title="Plan card (editable; clear a name to see Approve turn off)">
          <PlanCard
            plan={plan}
            onPlanChange={setPlan}
            onApprove={() => {}}
            onChange={() => setPlan(PLAN)}
          />
        </Section>

        <Section title="Cannot build (refused, and unsupported)">
          <CannotBuildNotice
            reason="refused"
            message="This request asks for a way to collect people's passwords without them knowing."
            onStartOver={() => {}}
          />
          <CannotBuildNotice
            reason="unsupported"
            message="Live video calls need more than a simple API."
            alternative="We could build an API that books and lists video appointments instead."
            onStartOver={() => {}}
          />
        </Section>

        <Section title="Build timeline (retrying)">
          <BuildTimeline
            title="Building Bookshop API"
            attempt={2}
            maxAttempts={3}
            status="retrying"
            tests={['pass', 'pass', 'pass', 'pass', 'fail']}
            steps={[
              {
                kind: 'Thinking',
                text: 'I will write the routes for books first.',
                state: 'done',
              },
              {
                kind: 'Doing',
                text: 'Writing app/routes/books.py',
                state: 'done',
              },
              {
                kind: 'Result',
                text: 'Test failed: deleting a missing book should return 404.',
                output:
                  'FAILED test_delete_missing_book - got 500, expected 404',
                state: 'failed',
              },
              {
                kind: 'Doing',
                text: 'Fixing the delete route and running the tests again.',
                state: 'current',
              },
            ]}
          />
        </Section>

        <Section title="Ready card (and download error)">
          <ReadyCard
            fileCount={9}
            sizeKb={14}
            testsPassed={5}
            testsTotal={5}
            runCommand="docker compose up"
            onDownload={() => {}}
          />
          <ReadyCard
            fileCount={9}
            sizeKb={14}
            testsPassed={5}
            testsTotal={5}
            runCommand="docker compose up"
            onDownload={() => {}}
            downloadError="Your browser blocked the download. Try again or allow downloads for this site."
          />
        </Section>
      </div>
    </AppShell>
  )
}
