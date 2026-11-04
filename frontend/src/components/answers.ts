// Turns the answers held by QuestionFlow into what the backend expects.
// Kept out of the component file so Vite's fast refresh keeps working while developing.
import type { Answer, Question } from './QuestionCard'

// The shape POST /projects/{id}/answers expects (docs/api-contract.md)
export type AnswerItem = { question_id: string; answer: string }

// Turns one answer into the plain text the backend expects.
// A list of picks becomes "Price, Author". A blank answer becomes '' (skipped).
function toText(answer: Answer): string {
  if (Array.isArray(answer)) {
    return answer.join(', ')
  }
  return answer.trim()
}

// Keeps only the questions the person actually answered.
// Unanswered ones are left out so the planner uses its best guess for them.
export function collectAnswers(
  questions: Question[],
  answers: Record<string, Answer>,
): AnswerItem[] {
  const result: AnswerItem[] = []
  for (const question of questions) {
    const text = toText(answers[question.id] ?? '')
    if (text !== '') {
      result.push({ question_id: question.id, answer: text })
    }
  }
  return result
}
