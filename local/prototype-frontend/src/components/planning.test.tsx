import { fireEvent, render, screen, within } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { BuildTimeline } from './BuildTimeline'
import { CannotBuildNotice } from './CannotBuildNotice'
import { FieldsEditor } from './FieldsEditor'
import { PlanCard, type Plan } from './PlanCard'
import { QuestionCard, type Question } from './QuestionCard'
import { QuestionFlow } from './QuestionFlow'
import { collectAnswers, type AnswerItem } from './answers'
import { MAX_FIELDS, hasBlankName, type PlanField } from './fields'

// Tests for the features brought over from the earlier prototype (task F-12).

const SINGLE: Question = {
  id: 'q1',
  text: 'Should each book have a price?',
  why: 'Decides whether we store prices.',
  kind: 'single_choice',
  options: ['Yes, with a price', 'No, just titles'],
}
const MULTI: Question = {
  id: 'q2',
  text: 'What else should each book have?',
  why: 'Each one becomes a detail.',
  kind: 'multi_choice',
  options: ['Author', 'Year published'],
}
const YES_NO: Question = {
  id: 'q3',
  text: 'Can people delete books?',
  why: 'Some shops keep every record.',
  kind: 'yes_no',
  options: [],
}
const SHORT: Question = {
  id: 'q4',
  text: 'What is your shop called?',
  why: 'We use it as the name.',
  kind: 'short_text',
  options: [],
}

function field(name: string, extra: Partial<PlanField> = {}): PlanField {
  return { name, type: 'str', required: false, ...extra }
}

describe('QuestionCard', () => {
  it('single choice: a chip click gives that option as the answer', () => {
    const onAnswer = vi.fn()
    render(
      <QuestionCard
        index={1}
        total={1}
        question={SINGLE}
        answer=""
        onAnswer={onAnswer}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'No, just titles' }))

    expect(onAnswer).toHaveBeenCalledWith('No, just titles')
  })

  it('single choice: own words become the answer, and the box stays empty when a chip is picked', () => {
    const onAnswer = vi.fn()
    const { rerender } = render(
      <QuestionCard
        index={1}
        total={1}
        question={SINGLE}
        answer=""
        onAnswer={onAnswer}
      />,
    )
    const box = screen.getByLabelText('Or answer in your own words')

    fireEvent.change(box, { target: { value: 'Only some books' } })
    expect(onAnswer).toHaveBeenCalledWith('Only some books')

    rerender(
      <QuestionCard
        index={1}
        total={1}
        question={SINGLE}
        answer="Yes, with a price"
        onAnswer={onAnswer}
      />,
    )
    expect(box).toHaveValue('')
    expect(
      screen.getByRole('button', { name: 'Yes, with a price' }),
    ).toHaveAttribute('aria-pressed', 'true')
  })

  it('multi choice: clicking adds an option, clicking again removes it', () => {
    const onAnswer = vi.fn()
    const { rerender } = render(
      <QuestionCard
        index={1}
        total={1}
        question={MULTI}
        answer={[]}
        onAnswer={onAnswer}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Author' }))
    expect(onAnswer).toHaveBeenLastCalledWith(['Author'])

    rerender(
      <QuestionCard
        index={1}
        total={1}
        question={MULTI}
        answer={['Author']}
        onAnswer={onAnswer}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Author' }))
    expect(onAnswer).toHaveBeenLastCalledWith([])
  })

  it('yes/no: shows Yes and No when the planner sends no wording', () => {
    render(
      <QuestionCard
        index={1}
        total={1}
        question={YES_NO}
        answer=""
        onAnswer={() => {}}
      />,
    )

    expect(screen.getByRole('button', { name: 'Yes' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'No' })).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('short text: shows only a labelled text box', () => {
    render(
      <QuestionCard
        index={1}
        total={1}
        question={SHORT}
        answer=""
        onAnswer={() => {}}
      />,
    )

    expect(screen.getByLabelText('Your answer')).toBeInTheDocument()
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})

describe('collectAnswers', () => {
  it('keeps answered questions in the contract shape and joins multi choice', () => {
    const result = collectAnswers([SINGLE, MULTI, YES_NO, SHORT], {
      q1: 'Yes, with a price',
      q2: ['Author', 'Year published'],
      q3: '',
      q4: '   ',
    })

    expect(result).toEqual([
      { question_id: 'q1', answer: 'Yes, with a price' },
      { question_id: 'q2', answer: 'Author, Year published' },
    ])
  })

  it('returns an empty list when nothing was answered', () => {
    expect(collectAnswers([SINGLE, MULTI], {})).toEqual([])
  })
})

describe('QuestionFlow', () => {
  it('goes Next and Back, then sends the answers from the last question', () => {
    const onSubmit = vi.fn()
    render(<QuestionFlow questions={[SINGLE, YES_NO]} onSubmit={onSubmit} />)

    expect(screen.getByText('Question 1 of 2')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Back' }),
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Yes, with a price' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    expect(screen.getByText('Question 2 of 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    // The first answer is still picked after going back
    expect(
      screen.getByRole('button', { name: 'Yes, with a price' }),
    ).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.click(screen.getByRole('button', { name: 'No' }))
    fireEvent.click(screen.getByRole('button', { name: 'Show my plan' }))

    expect(onSubmit).toHaveBeenCalledWith([
      { question_id: 'q1', answer: 'Yes, with a price' },
      { question_id: 'q3', answer: 'No' },
    ])
  })

  it('Skip sends what is answered so far, and nothing when nothing is answered', () => {
    const onSubmit = vi.fn()
    render(<QuestionFlow questions={[SINGLE, YES_NO]} onSubmit={onSubmit} />)

    fireEvent.click(
      screen.getByRole('button', { name: 'Skip, use your best guess' }),
    )

    expect(onSubmit).toHaveBeenCalledWith([])
  })

  it('shows nothing when there are no questions', () => {
    const { container } = render(
      <QuestionFlow questions={[]} onSubmit={() => {}} />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it('while busy, every button is off and nothing is sent', () => {
    const onSubmit = vi.fn()
    render(<QuestionFlow questions={[SINGLE]} onSubmit={onSubmit} busy />)

    const send = screen.getByRole('button', { name: 'Making your plan' })
    expect(send).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Skip, use your best guess' }),
    ).toBeDisabled()
    fireEvent.click(send)
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('a double-click sends the answers only once', () => {
    const sent: AnswerItem[][] = []
    // A parent that turns on "busy" as soon as it receives the answers, like the real screen will
    function Parent() {
      const [busy, setBusy] = useState(false)
      return (
        <QuestionFlow
          questions={[SHORT]}
          busy={busy}
          onSubmit={(answers) => {
            sent.push(answers)
            setBusy(true)
          }}
        />
      )
    }
    render(<Parent />)
    const send = screen.getByRole('button', { name: 'Show my plan' })

    fireEvent.click(send)
    fireEvent.click(send)

    expect(sent).toHaveLength(1)
  })
})

describe('FieldsEditor', () => {
  it('renames a detail, changes its type and marks it required', () => {
    const onChange = vi.fn()
    render(
      <FieldsEditor
        tableName="books"
        fields={[field('title'), field('price')]}
        onChange={onChange}
      />,
    )

    fireEvent.change(screen.getByLabelText('Detail 1 name'), {
      target: { value: 'book_title' },
    })
    expect(onChange).toHaveBeenLastCalledWith([
      field('book_title'),
      field('price'),
    ])

    fireEvent.change(screen.getByLabelText('Type of price'), {
      target: { value: 'float' },
    })
    expect(onChange).toHaveBeenLastCalledWith([
      field('title'),
      field('price', { type: 'float' }),
    ])

    fireEvent.click(screen.getAllByLabelText('Must be filled in')[0])
    expect(onChange).toHaveBeenLastCalledWith([
      field('title', { required: true }),
      field('price'),
    ])
  })

  it('shows types in plain words, not Python names', () => {
    render(
      <FieldsEditor
        tableName="books"
        fields={[field('title'), field('price')]}
        onChange={() => {}}
      />,
    )

    const select = screen.getByLabelText('Type of title')
    expect(
      within(select).getByRole('option', { name: 'Whole number' }),
    ).toBeInTheDocument()
    expect(
      within(select).queryByRole('option', { name: 'int' }),
    ).not.toBeInTheDocument()
  })

  it('adds a blank detail and removes one', () => {
    const onChange = vi.fn()
    render(
      <FieldsEditor
        tableName="books"
        fields={[field('a'), field('b'), field('c')]}
        onChange={onChange}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Add a detail/ }))
    expect(onChange).toHaveBeenLastCalledWith([
      field('a'),
      field('b'),
      field('c'),
      field(''),
    ])

    fireEvent.click(screen.getByRole('button', { name: 'Remove b' }))
    expect(onChange).toHaveBeenLastCalledWith([field('a'), field('c')])
  })

  it('cannot go below 2 details or above 10', () => {
    const { rerender } = render(
      <FieldsEditor
        tableName="books"
        fields={[field('a'), field('b')]}
        onChange={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: 'Remove a' })).toBeDisabled()

    const ten = Array.from({ length: MAX_FIELDS }, (_, i) => field(`f${i}`))
    rerender(
      <FieldsEditor tableName="books" fields={ten} onChange={() => {}} />,
    )
    expect(screen.getByRole('button', { name: /Add a detail/ })).toBeDisabled()
    expect(screen.getByText('10 of 10 details')).toBeInTheDocument()
  })

  it('an automatic detail (like id) cannot be edited or removed', () => {
    render(
      <FieldsEditor
        tableName="books"
        fields={[
          field('id', { auto: true, type: 'int' }),
          field('title'),
          field('price'),
        ]}
        onChange={() => {}}
      />,
    )

    expect(screen.getByText('Filled in automatically')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Remove id' }),
    ).not.toBeInTheDocument()
    expect(screen.getAllByRole('textbox')).toHaveLength(2)
  })

  it('hasBlankName treats spaces as blank', () => {
    expect(hasBlankName([field('title'), field('   ')])).toBe(true)
    expect(hasBlankName([field('title')])).toBe(false)
  })
})

const PLAN: Plan = {
  name: 'Bookshop API',
  summary: 'Add and list books.',
  endpoints: [{ method: 'GET', path: '/books', description: 'See all books' }],
  tables: [{ name: 'books', fields: [field('title'), field('price')] }],
  testCount: 5,
}

describe('PlanCard', () => {
  it('approves when every detail has a name', () => {
    const onApprove = vi.fn()
    render(
      <PlanCard
        plan={PLAN}
        onPlanChange={() => {}}
        onApprove={onApprove}
        onChange={() => {}}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Approve plan' }))

    expect(onApprove).toHaveBeenCalledTimes(1)
    expect(screen.getByText('5 tests will check it')).toBeInTheDocument()
  })

  it('blocks approval and says why when a detail has no name', () => {
    const blankPlan: Plan = {
      ...PLAN,
      tables: [{ name: 'books', fields: [field('title'), field('')] }],
    }
    render(
      <PlanCard
        plan={blankPlan}
        onPlanChange={() => {}}
        onApprove={() => {}}
        onChange={() => {}}
      />,
    )

    expect(screen.getByRole('button', { name: 'Approve plan' })).toBeDisabled()
    expect(
      screen.getByText('Give every detail a name before approving'),
    ).toBeInTheDocument()
  })

  it('passes an edited detail up as a whole new plan', () => {
    const onPlanChange = vi.fn()
    render(
      <PlanCard
        plan={PLAN}
        onPlanChange={onPlanChange}
        onApprove={() => {}}
        onChange={() => {}}
      />,
    )

    fireEvent.change(screen.getByLabelText('Detail 2 name'), {
      target: { value: 'cost' },
    })

    expect(onPlanChange).toHaveBeenCalledWith({
      ...PLAN,
      tables: [{ name: 'books', fields: [field('title'), field('cost')] }],
    })
  })

  it('lists what is not included yet, and hides the section when the list is empty', () => {
    const { rerender } = render(
      <PlanCard
        plan={{ ...PLAN, notIncluded: ['Taking card payments'] }}
        onPlanChange={() => {}}
        onApprove={() => {}}
        onChange={() => {}}
      />,
    )
    expect(screen.getByText('Not included yet')).toBeInTheDocument()
    expect(screen.getByText('Taking card payments')).toBeInTheDocument()

    rerender(
      <PlanCard
        plan={{ ...PLAN, notIncluded: [] }}
        onPlanChange={() => {}}
        onApprove={() => {}}
        onChange={() => {}}
      />,
    )
    expect(screen.queryByText('Not included yet')).not.toBeInTheDocument()
  })
})

describe('CannotBuildNotice', () => {
  it('a refused request interrupts screen readers and offers to start over', () => {
    const onStartOver = vi.fn()
    render(
      <CannotBuildNotice
        reason="refused"
        message="This could harm people."
        onStartOver={onStartOver}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('We cannot build that')
    fireEvent.click(screen.getByRole('button', { name: 'Change my request' }))
    expect(onStartOver).toHaveBeenCalledTimes(1)
  })

  it('an unsupported request is calm and shows the suggested alternative', () => {
    render(
      <CannotBuildNotice
        reason="unsupported"
        message="Live video needs more than an API."
        alternative="We could build appointment booking instead."
        onStartOver={() => {}}
      />,
    )

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(
      'We could build appointment booking instead.',
    )
  })
})

describe('BuildTimeline', () => {
  it('keeps raw test output folded away behind "Show details for a developer"', () => {
    render(
      <BuildTimeline
        title="Building Bookshop API"
        attempt={1}
        maxAttempts={3}
        status="failed"
        tests={['fail']}
        steps={[
          {
            kind: 'Result',
            text: 'A test failed.',
            output: 'FAILED test_delete_missing_book',
            state: 'failed',
          },
        ]}
      />,
    )

    const details = screen
      .getByText('Show details for a developer')
      .closest('details')
    expect(details).not.toHaveAttribute('open')
  })
})
