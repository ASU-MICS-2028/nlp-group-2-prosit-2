import { Button } from './Button'
import { MethodBadge, type Method } from './MethodBadge'

export type Plan = {
  name: string
  summary: string
  endpoints: { method: Method; path: string; description: string }[]
  tables: { name: string; fields: string }[]
  testCount: number
}

type Props = {
  plan: Plan
  onApprove: () => void
  onChange: () => void
}

// Nothing is built until the person approves this card (human-in-the-loop).
export function PlanCard({ plan, onApprove, onChange }: Props) {
  return (
    <div className="warm-card card">
      <span className="t-caption accent-text">
        Nothing is built until you approve
      </span>
      <h2 className="t-title" style={{ margin: 0 }}>
        {plan.name}
      </h2>
      <p className="muted" style={{ margin: 0 }}>
        {plan.summary}
      </p>

      <div>
        <h3 className="t-section" style={{ margin: 0 }}>
          Endpoints (addresses your app will call)
        </h3>
        <div className="plan__rows">
          {plan.endpoints.map((endpoint) => (
            <div className="plan__row" key={endpoint.method + endpoint.path}>
              <MethodBadge method={endpoint.method} />
              <span className="plan__row-text">
                <span className="t-code">{endpoint.path}</span>
                <br />
                <span className="muted">{endpoint.description}</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="t-section" style={{ margin: 0 }}>
          What it stores
        </h3>
        <div className="plan__rows">
          {plan.tables.map((table) => (
            <div className="plan__row" key={table.name}>
              <span className="t-code">{table.name}</span>
              <span className="t-code muted">{table.fields}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="plan__footer">
        <span className="t-caption muted">
          {plan.testCount} tests will check it
        </span>
        <div className="plan__actions">
          <Button onClick={onChange}>Change something</Button>
          <Button variant="primary" onClick={onApprove}>
            Approve plan
          </Button>
        </div>
      </div>
    </div>
  )
}
