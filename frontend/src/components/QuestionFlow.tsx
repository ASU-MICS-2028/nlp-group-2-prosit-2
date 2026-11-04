import { useState } from 'react'
import { Button } from './Button'
import { QuestionCard, type Answer, type Question } from './QuestionCard'
import { collectAnswers, type AnswerItem } from './answers'

type Props = {
  questions: Question[]
  onSubmit: (answers: AnswerItem[]) => void
  // True while the answers are being sent; stops a second click sending them twice
  busy?: boolean
}

function emptyAnswer(question: Question): Answer {
  return question.kind === 'multi_choice' ? [] : ''
}

// One question at a time, with Back, Next and "Skip, use your best guess".
export function QuestionFlow({ questions, onSubmit, busy = false }: Props) {
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, Answer>>({})

  // Nothing to ask: the parent should go straight to the plan
  if (questions.length === 0) {
    return null
  }

  const question = questions[index]
  const isLast = index === questions.length - 1
  const answer = answers[question.id] ?? emptyAnswer(question)

  function setAnswer(next: Answer) {
    setAnswers({ ...answers, [question.id]: next })
  }

  function submit() {
    if (busy) {
      return
    }
    onSubmit(collectAnswers(questions, answers))
  }

  return (
    // aria-live so a screen reader reads the new question after Next or Back
    <div className="question-flow" aria-live="polite">
      <QuestionCard
        index={index + 1}
        total={questions.length}
        question={question}
        answer={answer}
        onAnswer={setAnswer}
      />
      <div className="card__row">
        <Button variant="ghost" disabled={busy} onClick={submit}>
          Skip, use your best guess
        </Button>
        <div className="question-flow__nav">
          {index > 0 && (
            <Button disabled={busy} onClick={() => setIndex(index - 1)}>
              Back
            </Button>
          )}
          {isLast ? (
            <Button variant="primary" loading={busy} onClick={submit}>
              {busy ? 'Making your plan' : 'Show my plan'}
            </Button>
          ) : (
            <Button variant="primary" onClick={() => setIndex(index + 1)}>
              Next
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
