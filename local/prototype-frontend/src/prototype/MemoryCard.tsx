// LOCAL ONLY. Step 4: "What I remember about you", with a way to delete each fact or all of them.
import { X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from '../components/Button'
import { Notice } from '../components/Notice'
import {
  forgetAllMemories,
  forgetMemory,
  listMemories,
  type Memory,
} from './api'

export function MemoryCard() {
  const [memories, setMemories] = useState<Memory[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setMemories(await listMemories())
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load.')
    }
  }

  useEffect(() => {
    // State is set only when the request comes back, never straight away inside the effect
    listMemories()
      .then(setMemories)
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : 'Could not load.'),
      )
  }, [])

  async function act(action: () => Promise<void>) {
    setError(null)
    try {
      await action()
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'That did not work.')
    }
  }

  if (memories === null && !error) return null // still loading: show nothing rather than flicker

  return (
    <div className="card card--bordered">
      <div className="card__row">
        <h2 className="t-section" style={{ margin: 0 }}>
          What I remember about you
        </h2>
        {memories && memories.length > 0 && (
          <Button variant="ghost" onClick={() => act(forgetAllMemories)}>
            Forget everything
          </Button>
        )}
      </div>
      {error && (
        <Notice tone="error" title="Memory is not available">
          {error}
        </Notice>
      )}
      {memories && memories.length === 0 && (
        <span className="muted">
          Nothing yet. I learn from plans you approve, and you can delete
          anything here.
        </span>
      )}
      {memories && memories.length > 0 && (
        <ul className="plan__not-included">
          {memories.map((item) => (
            <li key={item.id}>
              <span style={{ flex: 1 }}>{item.fact}</span>
              <Button
                variant="ghost"
                aria-label={`Forget: ${item.fact}`}
                onClick={() => act(() => forgetMemory(item.id))}
              >
                <X size={14} aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
