import { Plus, Trash2 } from 'lucide-react'
import { Button } from './Button'
import {
  MAX_FIELDS,
  MIN_FIELDS,
  TYPES,
  TYPE_LABELS,
  type FieldType,
  type LinkTarget,
  type PlanField,
} from './fields'

type Props = {
  tableName: string
  fields: PlanField[]
  onChange: (fields: PlanField[]) => void
  // Other record types a detail can link to (none for a single-record plan)
  linkTargets?: LinkTarget[]
}

const LINK_PREFIX = 'link:'

// The dropdown's value: the type, or "link:<record>" for a link
function selectValue(field: PlanField): string {
  return field.type === 'link'
    ? `${LINK_PREFIX}${field.linksTo ?? ''}`
    : field.type
}

// What changes when a new type is picked in the dropdown
function typeChange(field: PlanField, value: string): Partial<PlanField> {
  if (value.startsWith(LINK_PREFIX)) {
    const target = value.slice(LINK_PREFIX.length)
    // A link is always named <record>_id, e.g. classroom_id
    const name = field.name.endsWith('_id') ? field.name : `${target}_id`
    return { type: 'link', linksTo: target, name }
  }
  // The options only hold FieldType values here, so this cast is safe
  return { type: value as FieldType, linksTo: undefined }
}

// Edits the details (columns) of one stored table, in plain words.
export function FieldsEditor({
  tableName,
  fields,
  onChange,
  linkTargets = [],
}: Props) {
  const canAdd = fields.length < MAX_FIELDS
  const canRemove = fields.length > MIN_FIELDS

  function updateField(position: number, change: Partial<PlanField>) {
    const next = fields.map((field, index) =>
      index === position ? { ...field, ...change } : field,
    )
    onChange(next)
  }

  function addField() {
    onChange([...fields, { name: '', type: 'str', required: false }])
  }

  function removeField(position: number) {
    onChange(fields.filter((_, index) => index !== position))
  }

  return (
    <div className="fields">
      <div className="card__row">
        <span className="t-code">{tableName}</span>
        <span className="t-caption muted">
          {fields.length} of {MAX_FIELDS} details
        </span>
      </div>

      {fields.map((field, position) => {
        const number = position + 1
        const shownName = field.name || `detail ${number}`
        return (
          // Position is the key: details have no id of their own and can be renamed
          <div className="fields__row" key={position}>
            {field.auto ? (
              <>
                <span className="t-code fields__name">{field.name}</span>
                <span className="t-caption muted">Filled in automatically</span>
              </>
            ) : (
              <>
                <input
                  className="question__input fields__name"
                  aria-label={`Detail ${number} name`}
                  placeholder="Name of this detail"
                  value={field.name}
                  onChange={(event) =>
                    updateField(position, { name: event.target.value })
                  }
                />
                <select
                  className="fields__select"
                  aria-label={`Type of ${shownName}`}
                  value={selectValue(field)}
                  onChange={(event) =>
                    updateField(position, typeChange(field, event.target.value))
                  }
                >
                  {TYPES.map((type) => (
                    <option key={type} value={type}>
                      {TYPE_LABELS[type]}
                    </option>
                  ))}
                  {linkTargets.map((target) => (
                    <option
                      key={target.name}
                      value={`${LINK_PREFIX}${target.name}`}
                    >
                      Link to {target.label}
                    </option>
                  ))}
                </select>
                <label className="fields__required t-caption">
                  <input
                    type="checkbox"
                    checked={field.required}
                    onChange={(event) =>
                      updateField(position, { required: event.target.checked })
                    }
                  />
                  Must be filled in
                </label>
                <Button
                  variant="ghost"
                  aria-label={`Remove ${shownName}`}
                  disabled={!canRemove}
                  onClick={() => removeField(position)}
                >
                  <Trash2 size={16} aria-hidden />
                </Button>
              </>
            )}
          </div>
        )
      })}

      <div>
        <Button variant="ghost" disabled={!canAdd} onClick={addField}>
          <Plus size={16} aria-hidden />
          Add a detail
        </Button>
      </div>
    </div>
  )
}
