import { ArrowRight, Clock } from 'lucide-react'
import { Button } from './Button'
import { FieldsEditor } from './FieldsEditor'
import { hasBlankName, words, type LinkTarget, type PlanField } from './fields'
import { MethodBadge, type Method } from './MethodBadge'

export type PlanTable = {
  name: string // plural, e.g. students (the address and table name)
  fields: PlanField[]
  // Optional (multi-record plans): the singular name links point at, and a one-line description
  resourceName?: string
  description?: string
}

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

// With more record types than this, the full address list is folded away (it gets long)
const SHOW_ALL_ENDPOINTS_UP_TO = 1

// "Each student belongs to one classroom", from every link in the plan
function connections(tables: PlanTable[]): string[] {
  const sentences: string[] = []
  for (const table of tables) {
    for (const field of table.fields) {
      if (field.type === 'link' && field.linksTo) {
        const one = words(table.resourceName ?? table.name)
        const optional = field.required ? '' : ' (optional)'
        sentences.push(
          `Each ${one} belongs to one ${words(field.linksTo)}${optional}`,
        )
      }
    }
  }
  return sentences
}

function Endpoints({ plan }: { plan: Plan }) {
  const rows = (
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
  )
  if (plan.tables.length <= SHOW_ALL_ENDPOINTS_UP_TO) return rows
  return (
    <>
      <p className="muted" style={{ margin: 'var(--space-2) 0 0' }}>
        Each of the {plan.tables.length} record types can be listed, added,
        opened, changed and deleted.
      </p>
      <details className="step__details">
        <summary className="t-caption muted">
          Show all {plan.endpoints.length} addresses
        </summary>
        {rows}
      </details>
    </>
  )
}

// Nothing is built until the person approves this card (human-in-the-loop).
// People fix the stored details here instead of rewriting their whole request.
export function PlanCard({ plan, onPlanChange, onApprove, onChange }: Props) {
  const blank = plan.tables.some((table) => hasBlankName(table.fields))
  const notIncluded = plan.notIncluded ?? []
  const links = connections(plan.tables)
  const many = plan.tables.length > 1

  function updateTable(position: number, fields: PlanField[]) {
    const tables = plan.tables.map((table, index) =>
      index === position ? { ...table, fields } : table,
    )
    onPlanChange({ ...plan, tables })
  }

  // The record types a detail in `table` may link to: every other one
  function targetsFor(table: PlanTable): LinkTarget[] {
    return plan.tables
      .filter((other) => other !== table && other.resourceName)
      .map((other) => ({
        name: other.resourceName ?? other.name,
        label: words(other.resourceName ?? other.name),
      }))
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

      {links.length > 0 && (
        <div>
          <h3 className="t-section" style={{ margin: 0 }}>
            How they connect
          </h3>
          <ul className="plan__links">
            {links.map((sentence) => (
              <li key={sentence}>
                <ArrowRight size={14} aria-hidden />
                {sentence}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h3 className="t-section" style={{ margin: 0 }}>
          {many
            ? `What it stores: ${plan.tables.length} record types (change anything that is not right)`
            : 'What it stores (change anything that is not right)'}
        </h3>
        <div className="plan__rows">
          {plan.tables.map((table, position) => (
            <div className="plan__row plan__table" key={table.name}>
              {many && table.description && (
                <span className="muted">{table.description}</span>
              )}
              <FieldsEditor
                tableName={table.name}
                fields={table.fields}
                linkTargets={many ? targetsFor(table) : []}
                onChange={(fields) => updateTable(position, fields)}
              />
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="t-section" style={{ margin: 0 }}>
          Endpoints (addresses your app will call)
        </h3>
        <Endpoints plan={plan} />
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
