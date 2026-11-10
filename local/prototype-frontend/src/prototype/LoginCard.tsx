// LOCAL ONLY. Log in or create an account, in the same card style as the request card.
import { useState, type FormEvent } from 'react'
import { Button } from '../components/Button'
import { Notice } from '../components/Notice'

// The backend's limits (models.py Credentials), checked here too so people get instant feedback
const MIN_PASSWORD = 8
const MAX_PASSWORD = 128

type Props = {
  busy: boolean
  error: string | null
  onLogIn: (email: string, password: string) => void
  onSignUp: (email: string, password: string) => void
}

export function LoginCard({ busy, error, onLogIn, onSignUp }: Props) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const isSignUp = mode === 'signup'
  const passwordOk =
    password.length >= MIN_PASSWORD && password.length <= MAX_PASSWORD
  const canSend =
    email.trim() !== '' && (isSignUp ? passwordOk : password !== '')

  function submit(event: FormEvent) {
    // A form submit would reload the page; we send it ourselves instead
    event.preventDefault()
    if (!canSend || busy) return
    if (isSignUp) {
      onSignUp(email.trim(), password)
    } else {
      onLogIn(email.trim(), password)
    }
  }

  return (
    // A real <form>, so pressing Enter in either box sends it
    <form className="card card--bordered" onSubmit={submit}>
      <h2 className="t-title" style={{ margin: 0 }}>
        {isSignUp ? 'Create an account' : 'Log in'}
      </h2>
      <label htmlFor="email" className="t-caption muted">
        Email
      </label>
      <input
        id="email"
        className="question__input"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <label htmlFor="password" className="t-caption muted">
        Password{isSignUp && ` (at least ${MIN_PASSWORD} characters)`}
      </label>
      <input
        id="password"
        className="question__input"
        type="password"
        autoComplete={isSignUp ? 'new-password' : 'current-password'}
        maxLength={MAX_PASSWORD}
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      {error && (
        <Notice tone="error" title="That did not work">
          {error}
        </Notice>
      )}
      <div className="card__row">
        <Button
          variant="ghost"
          disabled={busy}
          onClick={() => setMode(isSignUp ? 'login' : 'signup')}
        >
          {isSignUp ? 'I already have an account' : 'Create an account instead'}
        </Button>
        <Button
          variant="primary"
          type="submit"
          disabled={!canSend}
          loading={busy}
        >
          {isSignUp ? 'Create account' : 'Log in'}
        </Button>
      </div>
    </form>
  )
}
