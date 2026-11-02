import { Chip } from './Chip'

type Props = {
  index: number
  total: number
  question: string
  why: string
  options: string[]
  selected: string | null
  onSelect: (option: string) => void
  customAnswer: string
  onCustomChange: (value: string) => void
}

export function QuestionCard({
  index,
  total,
  question,
  why,
  options,
  selected,
  onSelect,
  customAnswer,
  onCustomChange,
}: Props) {
  const inputId = `custom-answer-${index}`
  return (
    <div className="card card--bordered">
      <span className="t-caption accent-text">
        Question {index} of {total}
      </span>
      <h2 className="t-title" style={{ margin: 0 }}>
        {question}
      </h2>
      <p className="muted" style={{ margin: 0 }}>
        {why}
      </p>
      <div className="question__chips">
        {options.map((option) => (
          <Chip
            key={option}
            label={option}
            selected={selected === option}
            onClick={() => onSelect(option)}
          />
        ))}
      </div>
      <label htmlFor={inputId} className="t-caption muted">
        Or answer in your own words
      </label>
      <input
        id={inputId}
        className="question__input"
        value={customAnswer}
        onChange={(event) => onCustomChange(event.target.value)}
      />
    </div>
  )
}
