import { StatusPill, type Status } from './StatusPill'

export type TestResult = 'pass' | 'fail' | 'pending'

export type BuildStep = {
  kind: 'Thinking' | 'Doing' | 'Result'
  text: string
  output?: string
  state: 'done' | 'current' | 'failed'
}

type Props = {
  title: string
  // Optional: a builder that does not retry (like the prototype) leaves these out
  attempt?: number
  maxAttempts?: number
  // Optional caption shown instead, e.g. "Started 2 minutes ago"
  caption?: string
  status: Status
  tests: TestResult[]
  steps: BuildStep[]
}

function countOf(tests: TestResult[], result: TestResult) {
  return tests.filter((test) => test === result).length
}

// Shows the agent's work in plain words: Thinking, Doing, Result.
export function BuildTimeline({
  title,
  attempt,
  maxAttempts,
  caption,
  status,
  tests,
  steps,
}: Props) {
  const subtitle =
    attempt !== undefined && maxAttempts !== undefined
      ? `Attempt ${attempt} of ${maxAttempts}`
      : caption
  return (
    <div className="card card--bordered">
      <div className="card__row">
        <div>
          <h2 className="t-title" style={{ margin: 0 }}>
            {title}
          </h2>
          {subtitle && <span className="t-caption muted">{subtitle}</span>}
        </div>
        {/* role="status" so screen readers hear changes politely */}
        <span role="status">
          <StatusPill status={status} />
        </span>
      </div>

      <div>
        <div className="tests-bar" aria-hidden>
          {tests.map((result, index) => (
            <span
              key={index}
              className={`tests-bar__segment tests-bar__segment--${result}`}
            />
          ))}
        </div>
        <span className="t-caption muted">
          {countOf(tests, 'pass')} passing · {countOf(tests, 'fail')} failing ·{' '}
          {tests.length} tests
        </span>
      </div>

      <ol className="steps">
        {steps.map((step, index) => (
          <li key={index} className={`step step--${step.state}`}>
            <span className="step__dot" aria-hidden />
            <span className="step__kind t-caption">{step.kind}</span>
            <div>{step.text}</div>
            {/* Raw output is for developers, so it stays folded away unless opened */}
            {step.output && (
              <details className="step__details">
                <summary className="t-caption muted">
                  Show details for a developer
                </summary>
                <pre className="well t-code">{step.output}</pre>
              </details>
            )}
          </li>
        ))}
      </ol>
    </div>
  )
}
