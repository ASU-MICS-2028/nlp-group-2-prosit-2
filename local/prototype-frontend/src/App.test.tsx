import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { toPlan, whenText } from './prototype/api'

// LOCAL ONLY: the whole flow against a fake prototype backend (fetch is stubbed).

function field(name: string, type: string, auto = false) {
  return { name, type, required: true, default: null, description: '', auto }
}

// The backend's design shape: one or more record types (this one has a single type, books)
const BLUEPRINT = {
  title: 'Bookshop API',
  description: 'Add and list books.',
  resources: [
    {
      name: 'book',
      plural: 'books',
      description: 'A book in the shop.',
      fields: [
        field('id', 'int', true),
        field('title', 'str'),
        field('price', 'float'),
      ],
    },
  ],
}

const AMA = { id: 1, email: 'ama@example.com', role: 'user' }

function session(status: string, extra: object = {}) {
  return {
    id: 's1',
    requirement: 'A bookshop where I can add books.',
    status,
    job_id: null,
    understanding: {
      verdict: 'vague',
      message: 'I have a couple of questions.',
      blueprint: BLUEPRINT,
      not_included: [{ category: 'payments', text: 'Taking card payments' }],
      questions: [
        {
          id: 'q1',
          text: 'Should each book have a price?',
          kind: 'yes_no',
          options: ['Yes', 'No'],
          allow_other: false,
          default: 'Yes',
          why: 'Decides whether we store prices.',
        },
      ],
      alternative: null,
      ...extra,
    },
  }
}

function reply(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>

// Every fake backend answers /auth/me for a logged-in token, and GET /memories and GET /projects
// (the start screen's memory card and the sidebar) with what the test gives, empty by default.
// callsOf() leaves those two background lists out, so flow checks stay readable.
function stubBackend(handler: Handler, lists: { projects?: unknown[] } = {}) {
  const spy = vi.fn(async (url: string, init?: RequestInit) => {
    const isGet = (init?.method ?? 'GET') === 'GET'
    if (url.endsWith('/auth/me')) return reply(AMA)
    if (url.endsWith('/memories') && isGet) return reply([])
    if (url.endsWith('/projects') && isGet) return reply(lists.projects ?? [])
    return handler(url, init)
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

function callsOf(spy: ReturnType<typeof stubBackend>): string[] {
  return spy.mock.calls
    .map(([url, init]) => `${init?.method ?? 'GET'} ${new URL(url).pathname}`)
    .filter((call) => call !== 'GET /memories' && call !== 'GET /projects')
}

async function renderLoggedIn() {
  sessionStorage.setItem('builder-token', 'good-token')
  render(<App />)
  await screen.findByRole('heading', { name: 'What should your API do?' })
}

function typeRequestAndSend() {
  fireEvent.change(screen.getByLabelText('Describe the API you need'), {
    target: { value: 'A bookshop where I can add books.' },
  })
  fireEvent.click(screen.getByRole('button', { name: /Plan my API/ }))
}

function readyJob() {
  return {
    id: 'j1',
    status: 'succeeded',
    stage: 'done',
    error: null,
    title: 'Bookshop API',
    files: ['a.py', 'b.py'],
    latency_s: 3,
  }
}

beforeEach(() => {
  sessionStorage.clear()
  // Start every test with a clean address (no #project=...)
  window.history.replaceState(null, '', '/')
})

afterEach(() => {
  vi.unstubAllGlobals()
  // Between tests, no request may reach a real server (a late request from one test once hit the
  // real backend on port 8001, got 401 and logged the next test out)
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.reject(new TypeError('No network in tests'))),
  )
})

describe('App against the prototype backend', () => {
  it('goes request → question → editable plan → build → ready', async () => {
    const spy = stubBackend((url) => {
      if (url.endsWith('/sessions')) return reply(session('needs_answers'))
      if (url.endsWith('/answers'))
        return reply(session('ready', { questions: [], verdict: 'clear' }))
      if (url.endsWith('/blueprint')) return reply(session('ready'))
      if (url.endsWith('/build')) return reply({ job_id: 'j1' })
      return reply(readyJob())
    })
    await renderLoggedIn()

    typeRequestAndSend()
    await screen.findByText('Should each book have a price?')
    fireEvent.click(screen.getByRole('button', { name: 'No' }))
    fireEvent.click(screen.getByRole('button', { name: 'Show my plan' }))

    await screen.findByText('Taking card payments')
    fireEvent.change(screen.getByLabelText('Detail 3 name'), {
      target: { value: 'cost' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Approve plan' }))

    await screen.findByText('Your API is ready')
    expect(screen.getByText(/2 files/)).toBeInTheDocument()
    // Step 3: the person is told where their two keys are
    expect(screen.getByText('Your API has two keys')).toBeInTheDocument()
    expect(callsOf(spy)).toEqual([
      'GET /auth/me',
      'POST /sessions',
      'POST /sessions/s1/answers',
      'PUT /sessions/s1/blueprint',
      'POST /sessions/s1/build',
      'GET /jobs/j1',
    ])
    // Every call after login carries the token
    for (const [, init] of spy.mock.calls) {
      expect(new Headers(init?.headers).get('Authorization')).toBe(
        'Bearer good-token',
      )
    }
  })

  it('sends the edited field names, and shows a failed build with a way back', async () => {
    const bodies: string[] = []
    stubBackend((url, init) => {
      if (url.endsWith('/blueprint')) bodies.push(String(init?.body))
      if (url.endsWith('/sessions'))
        return reply(session('ready', { questions: [] }))
      if (url.endsWith('/build')) return reply({ job_id: 'j1' })
      return reply({
        ...readyJob(),
        status: 'failed',
        stage: 'failed',
        error: 'LLM timed out',
        files: [],
      })
    })
    await renderLoggedIn()

    typeRequestAndSend()
    await screen.findByRole('button', { name: 'Approve plan' })
    fireEvent.change(screen.getByLabelText('Detail 3 name'), {
      target: { value: 'cost' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Approve plan' }))

    await screen.findByText('Show details for a developer')
    expect(screen.getByText('LLM timed out')).toBeInTheDocument()
    const sent: { resources: { fields: { name: string }[] }[] } = JSON.parse(
      bodies[0],
    )
    expect(sent.resources[0].fields.map((f) => f.name)).toEqual([
      'id',
      'title',
      'cost',
    ])
    fireEvent.click(screen.getByRole('button', { name: 'Back to the plan' }))
    expect(
      screen.getByRole('button', { name: 'Approve plan' }),
    ).toBeInTheDocument()
  })

  it('downloads the zip with the token (a plain link could not send it)', async () => {
    const spy = stubBackend((url) => {
      if (url.endsWith('/sessions'))
        return reply(session('ready', { questions: [] }))
      if (url.endsWith('/build')) return reply({ job_id: 'j1' })
      if (url.endsWith('/download'))
        return new Response('zip-bytes', { status: 200 })
      return reply(readyJob())
    })
    // jsdom has no real file saving, so stand in for the two browser functions used
    const createUrl = vi.fn(() => 'blob:fake')
    vi.stubGlobal(
      'URL',
      Object.assign(URL, {
        createObjectURL: createUrl,
        revokeObjectURL: vi.fn(),
      }),
    )
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {})
    await renderLoggedIn()

    typeRequestAndSend()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve plan' }))
    fireEvent.click(
      await screen.findByRole('button', { name: /Download project/ }),
    )

    await vi.waitFor(() => expect(click).toHaveBeenCalledTimes(1))
    const downloadCall = spy.mock.calls.find(([url]) =>
      url.endsWith('/download'),
    )
    expect(new Headers(downloadCall?.[1]?.headers).get('Authorization')).toBe(
      'Bearer good-token',
    )
    click.mockRestore()
  })

  it('says plainly when the backend is not running', async () => {
    stubBackend(() => Promise.reject(new TypeError('Failed to fetch')))
    await renderLoggedIn()

    typeRequestAndSend()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Is local\/prototype-backend\/run.ps1 running/,
    )
    expect(screen.getByLabelText('Describe the API you need')).toHaveValue(
      'A bookshop where I can add books.',
    )
  })

  it('shows the backend error text (for example the daily limit)', async () => {
    stubBackend(() =>
      reply({ detail: "You have used today's 20 requests." }, 429),
    )
    await renderLoggedIn()

    typeRequestAndSend()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "You have used today's 20 requests.",
    )
  })

  it('shows the refusal and lets the person start over', async () => {
    stubBackend(() =>
      reply(
        session('refused', {
          blueprint: null,
          message: 'That could harm people.',
        }),
      ),
    )
    await renderLoggedIn()

    typeRequestAndSend()

    expect(await screen.findByText('We cannot build that')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Change my request' }))
    expect(
      screen.getByRole('heading', { name: 'What should your API do?' }),
    ).toBeInTheDocument()
  })

  it('does not send a request that is too short', async () => {
    const spy = stubBackend(() => reply({}))
    await renderLoggedIn()

    fireEvent.change(screen.getByLabelText('Describe the API you need'), {
      target: { value: 'shop' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Plan my API/ }))

    expect(screen.getByText('Tell us a little more')).toBeInTheDocument()
    expect(callsOf(spy)).toEqual(['GET /auth/me'])
  })
})

describe('Logging in (step 2)', () => {
  it('shows the login card, not the builder, when nobody is logged in', () => {
    const spy = stubBackend(() => reply({}))
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'Log in to build your API' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('What should your API do?'),
    ).not.toBeInTheDocument()
    expect(spy).not.toHaveBeenCalled()
  })

  it('logs in, keeps the token, and opens the builder', async () => {
    stubBackend((url) =>
      url.endsWith('/auth/login')
        ? reply({ token: 'new-token', user: AMA })
        : reply({}),
    )
    render(<App />)

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'ama@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'long-password-1' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

    await screen.findByText('ama@example.com')
    expect(sessionStorage.getItem('builder-token')).toBe('new-token')
  })

  it('shows the backend message for a wrong password and stays on the card', async () => {
    stubBackend(() => reply({ detail: 'Email or password is wrong.' }, 401))
    render(<App />)

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'ama@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrong' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Email or password is wrong.',
    )
    expect(sessionStorage.getItem('builder-token')).toBeNull()
  })

  it('sign up needs at least 8 characters, then signs up and logs in', async () => {
    const spy = stubBackend((url) => {
      if (url.endsWith('/auth/register')) return reply(AMA, 201)
      return reply({ token: 'new-token', user: AMA })
    })
    render(<App />)

    fireEvent.click(
      screen.getByRole('button', { name: 'Create an account instead' }),
    )
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'ama@example.com' },
    })
    fireEvent.change(screen.getByLabelText(/Password/), {
      target: { value: 'short' },
    })
    expect(
      screen.getByRole('button', { name: 'Create account' }),
    ).toBeDisabled()

    fireEvent.change(screen.getByLabelText(/Password/), {
      target: { value: 'long-password-1' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    await screen.findByText('ama@example.com')
    expect(callsOf(spy)).toEqual(['POST /auth/register', 'POST /auth/login'])
  })

  it('goes back to the login card when the login ends in the middle of the flow', async () => {
    stubBackend(() => reply({ detail: 'Your login has ended.' }, 401))
    await renderLoggedIn()

    typeRequestAndSend()

    expect(
      await screen.findByRole('heading', { name: 'Log in to build your API' }),
    ).toBeInTheDocument()
    expect(sessionStorage.getItem('builder-token')).toBeNull()
  })

  it('a token from before a refresh that no longer works shows the login card', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => reply({ detail: 'ended' }, 401)),
    )
    sessionStorage.setItem('builder-token', 'old-token')
    render(<App />)

    expect(
      await screen.findByRole('heading', { name: 'Log in to build your API' }),
    ).toBeInTheDocument()
  })

  it('log out forgets the token and shows the login card', async () => {
    const spy = stubBackend(() => new Response(null, { status: 204 }))
    await renderLoggedIn()

    fireEvent.click(screen.getByRole('button', { name: 'Log out' }))

    expect(
      await screen.findByRole('heading', { name: 'Log in to build your API' }),
    ).toBeInTheDocument()
    expect(sessionStorage.getItem('builder-token')).toBeNull()
    expect(callsOf(spy)).toContain('POST /auth/logout')
  })
})

describe('Memory and similar designs (steps 4 and 5)', () => {
  it('shows what it remembers, and forgets one fact or everything', async () => {
    let facts = [
      { id: 2, fact: 'Uses Ghana cedis (GHS) for prices', created_at: 'x' },
      { id: 1, fact: 'Runs a hair salon', created_at: 'x' },
    ]
    const deleted: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/auth/me')) return reply(AMA)
        if (init?.method === 'DELETE') {
          const path = new URL(url).pathname
          deleted.push(path)
          facts =
            path === '/memories'
              ? []
              : facts.filter((f) => !path.endsWith(`/${f.id}`))
          return new Response(null, { status: 204 })
        }
        if (url.endsWith('/projects')) return reply([])
        return reply(facts)
      }),
    )
    await renderLoggedIn()

    expect(await screen.findByText('Runs a hair salon')).toBeInTheDocument()
    fireEvent.click(
      screen.getByRole('button', { name: 'Forget: Runs a hair salon' }),
    )
    await vi.waitFor(() =>
      expect(screen.queryByText('Runs a hair salon')).not.toBeInTheDocument(),
    )
    expect(
      screen.getByText('Uses Ghana cedis (GHS) for prices'),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Forget everything' }))
    expect(await screen.findByText(/Nothing yet/)).toBeInTheDocument()
    expect(deleted).toEqual(['/memories/1', '/memories'])
  })

  it('says plainly when memory cannot be loaded, and the builder still works', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        url.endsWith('/auth/me')
          ? reply(AMA)
          : reply({ detail: 'Database is busy.' }, 500),
      ),
    )
    await renderLoggedIn()

    expect(
      await screen.findByText('Memory is not available'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Plan my API/ }),
    ).toBeInTheDocument()
  })

  it('tells the person what helped make the plan', async () => {
    stubBackend(() =>
      reply(
        session('ready', {
          questions: [],
          memories_used: ['Runs a hair salon', 'Uses GHS'],
          examples_used: ['Salon Bookings API'],
        }),
      ),
    )
    await renderLoggedIn()

    typeRequestAndSend()

    expect(
      await screen.findByText(
        'I used 2 notes about you and similar designs: Salon Bookings API.',
      ),
    ).toBeInTheDocument()
  })
})

describe('Sidebar, build timeline, refresh and the account bar', () => {
  const PROJECTS = [
    {
      id: 's1',
      name: 'Bookshop API',
      status: 'ready',
      created_at: new Date().toISOString(),
    },
    {
      id: 's2',
      name: 'Clinic appointments',
      status: 'working',
      created_at: new Date().toISOString(),
    },
    {
      id: 's3',
      name: 'Farm produce orders',
      status: 'stopped',
      created_at: '2026-10-01T10:00:00+00:00',
    },
  ]

  function builtJob(
    tests: { name: string; passed: boolean; message: string }[],
  ) {
    return {
      ...readyJob(),
      steps: [
        {
          kind: 'Thinking',
          text: 'I will build books with 3 details, then test them.',
          state: 'done',
        },
        {
          kind: 'Doing',
          text: "Running the project's own tests.",
          state: 'done',
        },
        {
          kind: 'Result',
          text: '1 of 3 tests failed.',
          state: 'failed',
          output: 'FAILED delete: 200 instead of 204',
        },
      ],
      tests,
    }
  }

  it('lists your projects with a status and when, like the design', async () => {
    stubBackend(() => reply({}), { projects: PROJECTS })
    await renderLoggedIn()

    const sidebar = screen.getByRole('complementary', { name: 'Projects' })
    expect(await within(sidebar).findByText('Bookshop API')).toBeInTheDocument()
    expect(within(sidebar).getByText('Ready')).toBeInTheDocument()
    expect(within(sidebar).getByText('Working')).toBeInTheDocument()
    expect(within(sidebar).getByText('Stopped')).toBeInTheDocument()
    expect(within(sidebar).getAllByText('Just now')).toHaveLength(2)
  })

  it('opens a finished project from the sidebar with its real test results', async () => {
    const spy = stubBackend(
      (url) => {
        if (url.endsWith('/sessions/s1'))
          return reply({
            ...session('ready', { questions: [] }),
            id: 's1',
            job_id: 'j1',
          })
        return reply(
          builtJob([
            { name: 'health', passed: true, message: '' },
            { name: 'add', passed: true, message: '' },
            { name: 'delete', passed: false, message: '200 instead of 204' },
          ]),
        )
      },
      { projects: PROJECTS },
    )
    await renderLoggedIn()

    // Inside the sidebar: the start screen also has an example chip called "Bookshop API"
    const sidebar = screen.getByRole('complementary', { name: 'Projects' })
    fireEvent.click(
      await within(sidebar).findByRole('button', { name: /Bookshop API/ }),
    )

    // A finished build shows the ready card with the real test count (the timeline is for while it builds)
    expect(
      await screen.findByText('2 of 3 tests passed', { exact: false }),
    ).toBeInTheDocument()
    expect(screen.queryByText(/passing ·/)).not.toBeInTheDocument()
    // The open project is in the address, so a refresh can find it again
    expect(window.location.hash).toBe('#project=s1')
    expect(callsOf(spy)).toEqual([
      'GET /auth/me',
      'GET /sessions/s1',
      'GET /jobs/j1',
    ])
  })

  it('after a download, a refresh reopens the same project ready to download again', async () => {
    stubBackend((url) => {
      if (url.endsWith('/sessions/s1'))
        return reply({
          ...session('ready', { questions: [] }),
          id: 's1',
          job_id: 'j1',
        })
      if (url.endsWith('/download'))
        return new Response('zip-bytes', { status: 200 })
      return reply(builtJob([{ name: 'health', passed: true, message: '' }]))
    })
    vi.stubGlobal(
      'URL',
      Object.assign(URL, {
        createObjectURL: vi.fn(() => 'blob:x'),
        revokeObjectURL: vi.fn(),
      }),
    )
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {})
    window.history.replaceState(null, '', '/#project=s1')
    sessionStorage.setItem('builder-token', 'good-token')

    // First visit: download
    const first = render(<App />)
    fireEvent.click(
      await screen.findByRole('button', { name: /Download project/ }),
    )
    await vi.waitFor(() => expect(click).toHaveBeenCalledTimes(1))
    expect(window.location.hash).toBe('#project=s1') // the download did not change the page

    // "Refresh": a brand-new App with the same address
    first.unmount()
    render(<App />)
    fireEvent.click(
      await screen.findByRole('button', { name: /Download project/ }),
    )
    await vi.waitFor(() => expect(click).toHaveBeenCalledTimes(2))
    click.mockRestore()
  })

  it('a project that cannot be opened goes back to the start with a plain message', async () => {
    stubBackend(() => reply({ detail: 'This conversation was lost.' }, 404))
    window.history.replaceState(null, '', '/#project=gone')
    sessionStorage.setItem('builder-token', 'good-token')
    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This conversation was lost.',
    )
    expect(
      screen.getByRole('heading', { name: 'What should your API do?' }),
    ).toBeInTheDocument()
    expect(window.location.hash).toBe('')
  })

  it('shows the account bar at the top, and New project clears the address', async () => {
    stubBackend(() =>
      reply({ ...session('ready', { questions: [] }), id: 's9' }),
    )
    await renderLoggedIn()
    const bar = screen.getByLabelText('Your account')
    expect(within(bar).getByText('ama@example.com')).toBeInTheDocument()
    expect(
      within(bar).getByRole('button', { name: 'Log out' }),
    ).toBeInTheDocument()

    typeRequestAndSend()
    await screen.findByText('Your request')
    expect(window.location.hash).toBe('#project=s9')
    fireEvent.click(screen.getByRole('button', { name: /New project/ }))
    expect(window.location.hash).toBe('')
  })
})

describe('whenText', () => {
  const now = new Date('2026-11-03T12:00:00Z')
  it.each([
    ['2026-11-03T11:59:30Z', 'Just now'],
    ['2026-11-03T11:45:00Z', '15 minutes ago'],
    ['2026-11-03T11:00:00Z', '1 hour ago'],
    ['2026-11-03T07:00:00Z', '5 hours ago'],
    ['2026-11-02T10:00:00Z', 'Yesterday'],
    ['2026-10-31T10:00:00Z', '3 days ago'],
    ['not a date', ''],
  ])('%s → %s', (iso, expected) => {
    expect(whenText(iso, now)).toBe(expected)
  })
})

describe('Sidebar robustness', () => {
  it('a project with an unknown status shows as waiting instead of breaking the page', async () => {
    stubBackend(() => reply({}), {
      projects: [
        {
          id: 'x',
          name: 'Odd project',
          status: 'exploded',
          created_at: new Date().toISOString(),
        },
      ],
    })
    await renderLoggedIn()
    const sidebar = screen.getByRole('complementary', { name: 'Projects' })
    expect(await within(sidebar).findByText('Odd project')).toBeInTheDocument()
    expect(within(sidebar).getByText('Waiting')).toBeInTheDocument()
  })
})

describe('Timeline while building, and the login page', () => {
  it('shows one line per stage: done ones, then the one running now', async () => {
    stubBackend((url) => {
      if (url.endsWith('/sessions/s1'))
        return reply({
          ...session('ready', { questions: [] }),
          id: 's1',
          job_id: 'j1',
        })
      // Still running, now at the testing stage; poll keeps asking, so always answer the same
      return reply({
        ...readyJob(),
        status: 'running',
        stage: 'testing',
        tests: [],
      })
    })
    window.history.replaceState(null, '', '/#project=s1')
    sessionStorage.setItem('builder-token', 'good-token')
    render(<App />)

    expect(await screen.findByText('Running the tests')).toBeInTheDocument()
    const steps = screen
      .getAllByRole('listitem')
      .map((item) => item.textContent)
    expect(steps).toEqual([
      'DoingReading your design',
      'DoingWriting the API description',
      'DoingBuilding the project files',
      'DoingRunning the tests',
    ])
    expect(screen.getAllByRole('listitem')[3]).toHaveClass('step--current')
    expect(
      screen.getByText('0 passing · 0 failing · 11 tests'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Packaging the download')).not.toBeInTheDocument()
  })

  it('the login page has no sidebar, menu or project list', () => {
    stubBackend(() => reply({}))
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'Log in to build your API' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Mesora')).toBeInTheDocument()
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /New project/ }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /project menu/ }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText('Projects')).not.toBeInTheDocument()
  })
})

describe('Plan wording', () => {
  it('says "an appointment" and "a book"', () => {
    const design = (name: string) => ({
      title: 'T',
      description: 'D',
      resources: [{ name, plural: 'xs', description: '', fields: [] }],
    })
    const appointment = toPlan(design('appointment'), [])
    const book = toPlan(design('book'), [])
    expect(appointment.endpoints.map((e) => e.description)).toContain(
      'Change an appointment',
    )
    expect(appointment.endpoints.map((e) => e.description)).toContain(
      'Remove an appointment',
    )
    expect(book.endpoints.map((e) => e.description)).toContain('Change a book')
  })
})

describe('Plans with several linked record types (e.g. a school)', () => {
  const link = (name: string, to: string, required = true) => ({
    name,
    type: 'link',
    required,
    default: null,
    description: '',
    auto: false,
    links_to: to,
  })
  const SCHOOL = {
    title: 'School Management API',
    description: 'Students, teachers and classrooms.',
    resources: [
      {
        name: 'teacher',
        plural: 'teachers',
        description: 'A teacher.',
        fields: [field('full_name', 'str'), field('subject', 'str')],
      },
      {
        name: 'classroom',
        plural: 'classrooms',
        description: 'A class.',
        fields: [field('name', 'str'), link('teacher_id', 'teacher', false)],
      },
      {
        name: 'student',
        plural: 'students',
        description: 'A pupil.',
        fields: [field('full_name', 'str'), link('classroom_id', 'classroom')],
      },
    ],
  }

  async function openSchoolPlan(onBlueprint?: (body: string) => void) {
    stubBackend((url, init) => {
      if (url.endsWith('/blueprint')) onBlueprint?.(String(init?.body))
      if (url.endsWith('/sessions'))
        return reply(session('ready', { questions: [], blueprint: SCHOOL }))
      if (url.endsWith('/build')) return reply({ job_id: 'j1' })
      return reply({ ...readyJob(), status: 'running', stage: 'testing' })
    })
    await renderLoggedIn()
    typeRequestAndSend()
    await screen.findByText('How they connect')
  }

  it('shows how the record types connect, in plain words', async () => {
    await openSchoolPlan()
    expect(
      screen.getByText('Each classroom belongs to one teacher (optional)'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Each student belongs to one classroom'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /What it stores: 3 record types/ }),
    ).toBeInTheDocument()
  })

  it('counts the checks: 6 + 5 per record type + 3 per link', async () => {
    await openSchoolPlan()
    expect(
      screen.getByText(`${6 + 5 * 3 + 3 * 2} tests will check it`),
    ).toBeInTheDocument()
  })

  it('folds the 15 addresses away behind one line', async () => {
    await openSchoolPlan()
    expect(screen.getByText('Show all 15 addresses')).toBeInTheDocument()
    const details = screen.getByText('Show all 15 addresses').closest('details')
    expect(details).not.toHaveAttribute('open')
  })

  it('a detail can become a link to another record type, and the link reaches the backend', async () => {
    let saved = ''
    await openSchoolPlan((body) => (saved = body))
    // Teachers are the first table; turn their "subject" into a link to classrooms
    const select = screen.getByLabelText('Type of subject')
    expect(
      within(select).getByRole('option', { name: 'Link to classroom' }),
    ).toBeInTheDocument()
    expect(
      within(select).queryByRole('option', { name: 'Link to teacher' }),
    ).not.toBeInTheDocument() // not to itself
    fireEvent.change(select, { target: { value: 'link:classroom' } })
    // The teachers' second detail (the first table) was renamed to <record>_id
    expect(screen.getAllByLabelText('Detail 2 name')[0]).toHaveValue(
      'classroom_id',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Approve plan' }))
    await vi.waitFor(() => expect(saved).not.toBe(''))
    const teachers = JSON.parse(saved).resources[0]
    expect(teachers.fields[1]).toMatchObject({
      name: 'classroom_id',
      type: 'link',
      links_to: 'classroom',
    })
  })

  it('a single-record plan still lists its addresses in full and offers no links', async () => {
    stubBackend(() => reply(session('ready', { questions: [] })))
    await renderLoggedIn()
    typeRequestAndSend()
    await screen.findByRole('button', { name: 'Approve plan' })
    expect(screen.queryByText('How they connect')).not.toBeInTheDocument()
    expect(screen.queryByText(/Show all/)).not.toBeInTheDocument()
    expect(screen.getAllByText('/books').length).toBeGreaterThan(0)
    expect(
      within(screen.getByLabelText('Type of title')).queryByRole('option', {
        name: /Link to/,
      }),
    ).not.toBeInTheDocument()
  })
})

describe('Watching a build stops when the page closes', () => {
  it('no more progress requests after the builder is closed', async () => {
    const spy = stubBackend((url) => {
      if (url.endsWith('/sessions'))
        return reply(session('ready', { questions: [] }))
      if (url.endsWith('/build')) return reply({ job_id: 'j1' })
      return reply({ ...readyJob(), status: 'running', stage: 'testing' })
    })
    await renderLoggedIn()
    typeRequestAndSend()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve plan' }))
    await screen.findByText('Running the tests')
    const jobCalls = () =>
      spy.mock.calls.filter(([url]) => url.endsWith('/jobs/j1')).length

    cleanup() // closes the page, as logging out or leaving would
    const before = jobCalls()
    await new Promise((resolve) => setTimeout(resolve, 1500)) // longer than one poll interval

    expect(jobCalls()).toBe(before)
  })
})

describe('A late answer for an old login', () => {
  it('does not log out the person who is logged in now', async () => {
    let answerOld: (response: Response) => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        const token = new Headers(init?.headers).get('Authorization')
        if (url.endsWith('/auth/me')) return Promise.resolve(reply(AMA))
        if (url.endsWith('/sessions') && token === 'Bearer old-token')
          // The old login's request is slow: it answers later, after a new login
          return new Promise<Response>((resolve) => (answerOld = resolve))
        return Promise.resolve(reply([]))
      }),
    )
    sessionStorage.setItem('builder-token', 'old-token')
    render(<App />)
    await screen.findByRole('heading', { name: 'What should your API do?' })
    typeRequestAndSend()

    sessionStorage.setItem('builder-token', 'new-token') // someone logged in again meanwhile
    answerOld(reply({ detail: 'Your login has ended.' }, 401))
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(sessionStorage.getItem('builder-token')).toBe('new-token')
    expect(
      screen.queryByRole('heading', { name: 'Log in to build your API' }),
    ).not.toBeInTheDocument()
  })
})
