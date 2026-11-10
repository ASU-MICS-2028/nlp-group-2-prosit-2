import { Chip } from './Chip'

// The kinds of question the planner can ask (proposed in D-010).
// single_choice: pick one chip, or type your own answer
// multi_choice:  pick any number of chips
// yes_no:        pick Yes or No
// short_text:    type a short answer
export type QuestionKind =
  'single_choice' | 'multi_choice' | 'yes_no' | 'short_text'

export type Question = {
  id: string
  text: string
  why: string
  kind: QuestionKind
  options: string[]
}

// One answer: text for most kinds, a list of picked options for multi_choice
export type Answer = string | string[]

type Props = {
  index: number
  total: number
  question: Question
  answer: Answer
  onAnswer: (answer: Answer) => void
}

const YES_NO = ['Yes', 'No']

// Turns an answer into a list, so multi_choice code never has to check the type twice
function asList(answer: Answer): string[] {
  return Array.isArray(answer) ? answer : []
}

function asText(answer: Answer): string {
  return typeof answer === 'string' ? answer : ''
}

export function QuestionCard({
  index,
  total,
  question,
  answer,
  onAnswer,
}: Props) {
  const inputId = `answer-${question.id}`
  const text = asText(answer)
  const picked = asList(answer)
  // For yes/no, use the planner's wording if it sent some, otherwise plain Yes and No
  const yesNoOptions = question.options.length > 0 ? question.options : YES_NO
  // The own-words box shows the answer only when it is not one of the chips
  const ownWords = question.options.includes(text) ? '' : text

  function toggle(option: string) {
    if (picked.includes(option)) {
      onAnswer(picked.filter((item) => item !== option))
    } else {
      onAnswer([...picked, option])
    }
  }

  return (
    <div className="card card--bordered">
      <span className="t-caption accent-text">
        Question {index} of {total}
      </span>
      <h2 className="t-title" style={{ margin: 0 }}>
        {question.text}
      </h2>
      <p className="muted" style={{ margin: 0 }}>
        {question.why}
      </p>

      {question.kind === 'single_choice' && (
        <>
          <div className="question__chips">
            {question.options.map((option) => (
              <Chip
                key={option}
                label={option}
                selected={text === option}
                onClick={() => onAnswer(option)}
              />
            ))}
          </div>
          <label htmlFor={inputId} className="t-caption muted">
            Or answer in your own words
          </label>
          <input
            id={inputId}
            className="question__input"
            value={ownWords}
            onChange={(event) => onAnswer(event.target.value)}
          />
        </>
      )}

      {question.kind === 'yes_no' && (
        <div className="question__chips">
          {yesNoOptions.map((option) => (
            <Chip
              key={option}
              label={option}
              selected={text === option}
              onClick={() => onAnswer(option)}
            />
          ))}
        </div>
      )}

      {question.kind === 'multi_choice' && (
        <>
          <span className="t-caption muted">Pick as many as you need</span>
          <div className="question__chips">
            {question.options.map((option) => (
              <Chip
                key={option}
                label={option}
                selected={picked.includes(option)}
                onClick={() => toggle(option)}
              />
            ))}
          </div>
        </>
      )}

      {question.kind === 'short_text' && (
        <>
          <label htmlFor={inputId} className="t-caption muted">
            Your answer
          </label>
          <input
            id={inputId}
            className="question__input"
            value={text}
            onChange={(event) => onAnswer(event.target.value)}
          />
        </>
      )}
    </div>
  )
}
