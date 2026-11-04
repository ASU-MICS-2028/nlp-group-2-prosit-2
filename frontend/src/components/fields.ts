// Plain data and helpers for the plan's stored details (used by FieldsEditor and PlanCard).
// Kept out of the component files so Vite's fast refresh keeps working while developing.

// The data types a generated API can store. The values are the Python type names
// the backend will use; people only ever see the plain-English label.
export type FieldType = 'str' | 'int' | 'float' | 'bool' | 'datetime'

export const TYPE_LABELS: Record<FieldType, string> = {
  str: 'Text',
  int: 'Whole number',
  float: 'Number with decimals (e.g. money)',
  bool: 'Yes / No',
  datetime: 'Date and time',
}

// The order the types appear in the dropdown
export const TYPES: FieldType[] = ['str', 'int', 'float', 'bool', 'datetime']

export type PlanField = {
  name: string
  type: FieldType
  required: boolean
  // True for details the system fills in itself (like id): shown, but not editable
  auto?: boolean
}

// Limits on details per table, so a plan stays small enough to generate reliably
export const MIN_FIELDS = 2
export const MAX_FIELDS = 10

// True when any detail has no name; the plan cannot be approved until it is fixed
export function hasBlankName(fields: PlanField[]): boolean {
  return fields.some((field) => field.name.trim() === '')
}
