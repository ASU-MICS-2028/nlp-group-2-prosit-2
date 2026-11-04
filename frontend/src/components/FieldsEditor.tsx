import { Plus, Trash2 } from 'lucide-react'
import { Button } from './Button'
import {
  MAX_FIELDS,
  MIN_FIELDS,
  TYPES,
  TYPE_LABELS,
  type FieldType,
  type PlanField,
} from './fields'

type Props = {
  tableName: string
  fields: PlanField[]
  onChange: (fields: PlanField[]) => void
}

// Edits the details (columns) of one stored table, in plain words.
export function FieldsEditor({ tableName, fields, onChange }: Props) {
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
                  value={field.type}
                  onChange={(event) =>
                    // The options only hold FieldType values, so this cast is safe
                    updateField(position, {
                      type: event.target.value as FieldType,
                    })
                  }
                >
                  {TYPES.map((type) => (
                    <option key={type} value={type}>
                      {TYPE_LABELS[type]}
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
