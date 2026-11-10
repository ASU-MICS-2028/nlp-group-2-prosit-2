// The one place that reads settings from the environment.
// Vite only exposes variables that start with VITE_. They are public: never put secrets here.
export const API_URL: string =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
