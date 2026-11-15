// What a timeline step is about: a fixed list of words, the same ones the backend sends (D-019,
// docs/api-contract.md and PHASES in backend/builder.py). If you change this list, change those too.
export const PHASES = [
  'planning', // the AI's opening sentence about what it will build
  'writing', // reading, writing or listing files
  'testing', // running the tests, and their result
  'fixing', // the AI explaining a problem and what it will change
  'finishing', // the AI's closing reply, and the build's final result
] as const

export type Phase = (typeof PHASES)[number]
