// Plain data and helpers for the plan's stored details (used by FieldsEditor and PlanCard).
// Kept out of the component files so Vite's fast refresh keeps working while developing.

// The data types a generated API can store. The values are the Python type names
// the backend will use; people only ever see the plain-English label.
// "link" = this detail points at one record of another type (e.g. a student's classroom).
export type FieldType = 'str' | 'int' | 'float' | 'bool' | 'datetime' | 'link'

export const TYPE_LABELS: Record<FieldType, string> = {
  str: 'Text',
  int: 'Whole number',
  float: 'Number with decimals (e.g. money)',
  bool: 'Yes / No',
  datetime: 'Date and time',
  link: 'Link to another record',
}

// The value types, in dropdown order. Links are offered separately, one per other record type.
export const TYPES: FieldType[] = ['str', 'int', 'float', 'bool', 'datetime']

export type PlanField = {
  name: string
  type: FieldType
  required: boolean
  // True for details the system fills in itself (like id): shown, but not editable
  auto?: boolean
  // Only for type "link": the singular name of the record type it points at, e.g. "classroom"
  linksTo?: string
}

// A record type a link can point at: its singular name, and how people see it
export type LinkTarget = { name: string; label: string }

// Limits on details per table, so a plan stays small enough to generate reliably
export const MIN_FIELDS = 2
export const MAX_FIELDS = 10

// True when any detail has no name; the plan cannot be approved until it is fixed
export function hasBlankName(fields: PlanField[]): boolean {
  return fields.some((field) => field.name.trim() === '')
}

// "classroom_id" → "classroom"; "student" stays "student" (used in plain sentences)
export function words(name: string): string {
  return name.replace(/_id$/, '').replace(/_/g, ' ')
}
