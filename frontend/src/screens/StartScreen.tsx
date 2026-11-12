import { useState } from 'react'
import { Chip } from '../components/Chip'
import { Notice } from '../components/Notice'
import { RequestCard } from '../components/RequestCard'

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

type Props = {
  loading: boolean // true while the server creates the project
  error: string | null // a plain sentence when starting failed
  onSubmit: (request: string) => void
}

// The first screen: one question, one box. The text lives here, so it is still there
// after an error and the person can send it again without retyping.
export function StartScreen({ loading, error, onSubmit }: Props) {
  const [request, setRequest] = useState('')

  return (
    <div className="start">
      <h1 className="t-display start__title">What should your API do?</h1>
      <RequestCard
        value={request}
        onChange={setRequest}
        onSubmit={() => onSubmit(request.trim())}
        loading={loading}
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
      {loading && (
        <Notice tone="info" title="Starting your project">
          If the server was asleep, this can take up to half a minute.
        </Notice>
      )}
      {error && (
        <Notice tone="error" title="We could not start your project">
          {error}
        </Notice>
      )}
    </div>
  )
}
