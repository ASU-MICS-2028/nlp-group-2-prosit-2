export type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

// Colours match the ones on FastAPI's /docs page.
export function MethodBadge({ method }: { method: Method }) {
  return (
    <span className={`method-badge method--${method.toLowerCase()}`}>
      {method}
    </span>
  )
}
