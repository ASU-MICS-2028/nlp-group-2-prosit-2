import { useState } from 'react'
import { AppShell } from './components/AppShell'
import { Chip } from './components/Chip'
import { Notice } from './components/Notice'
import { RequestCard } from './components/RequestCard'
import { Sidebar } from './components/Sidebar'

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

// The Start screen. Planning is not connected to the backend yet (tasks W-5 to W-7),
// so sending shows a clear notice instead of pretending to work.
function App() {
  const [request, setRequest] = useState('')
  const [sent, setSent] = useState(false)

  return (
    <AppShell
      sidebar={
        <Sidebar
          projects={[]}
          activeId={null}
          onNewProject={() => {
            setRequest('')
            setSent(false)
          }}
          onSelect={() => {}}
        />
      }
    >
      <div className="start">
        <h1 className="t-display start__title">What should your API do?</h1>
        <RequestCard
          value={request}
          onChange={(value) => {
            setRequest(value)
            setSent(false)
          }}
          onSubmit={() => setSent(true)}
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
        {sent && (
          <Notice tone="info" title="Planning is not connected yet">
            The planning step arrives when the backend is ready. Your request
            was not sent anywhere.
          </Notice>
        )}
      </div>
    </AppShell>
  )
}

export default App
