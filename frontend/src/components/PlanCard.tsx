import { Clock } from 'lucide-react'
import { Button } from './Button'
import { FieldsEditor } from './FieldsEditor'
import { hasBlankName, type PlanField } from './fields'
import { MethodBadge, type Method } from './MethodBadge'

export type PlanTable = { name: string; fields: PlanField[] }

export type Plan = {
  name: string
  summary: string
  endpoints: { method: Method; path: string; description: string }[]
  // Structured fields (proposed in D-010) so people can edit them before approving
  tables: PlanTable[]
  testCount: number
  // Things the person asked for that the builder cannot do yet (proposed in D-010)
  notIncluded?: string[]
}

type Props = {
  plan: Plan
  onPlanChange: (plan: Plan) => void
  onApprove: () => void
  onChange: () => void
}

// Nothing is built until the person approves this card (human-in-the-loop).
// People fix the stored details here instead of rewriting their whole request.
export function PlanCard({ plan, onPlanChange, onApprove, onChange }: Props) {
  const blank = plan.tables.some((table) => hasBlankName(table.fields))
  const notIncluded = plan.notIncluded ?? []

  function updateTable(position: number, fields: PlanField[]) {
    const tables = plan.tables.map((table, index) =>
      index === position ? { ...table, fields } : table,
    )
    onPlanChange({ ...plan, tables })
  }

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
          What it stores (change anything that is not right)
        </h3>
        <div className="plan__rows">
          {plan.tables.map((table, position) => (
            <div className="plan__row" key={table.name}>
              <FieldsEditor
                tableName={table.name}
                fields={table.fields}
                onChange={(fields) => updateTable(position, fields)}
              />
            </div>
          ))}
        </div>
      </div>

      {notIncluded.length > 0 && (
        <div>
          <h3 className="t-section" style={{ margin: 0 }}>
            Not included yet
          </h3>
          <ul className="plan__not-included">
            {notIncluded.map((item) => (
              <li key={item}>
                <Clock size={14} aria-hidden />
                {item}
              </li>
            ))}
          </ul>
          <span className="t-caption muted">
            We have noted these so we know what to support next.
          </span>
        </div>
      )}

      <div className="plan__footer">
        <span className="t-caption muted">
          {blank
            ? 'Give every detail a name before approving'
            : `${plan.testCount} tests will check it`}
        </span>
        <div className="plan__actions">
          <Button onClick={onChange}>Change something</Button>
          <Button variant="primary" disabled={blank} onClick={onApprove}>
            Approve plan
          </Button>
        </div>
      </div>
    </div>
  )
}
