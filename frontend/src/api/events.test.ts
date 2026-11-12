import { describe, expect, it } from 'vitest'
import { parseEvent, splitMessages } from './events'

describe('parseEvent', () => {
  it('reads the exact message the real server sends for a new project', () => {
    expect(parseEvent('{"status":"waiting"}')).toEqual({ status: 'waiting' })
  })

  it('reads a full event from the contract, including the step', () => {
    const text = JSON.stringify({
      status: 'retrying',
      attempt: 2,
      max_attempts: 3,
      tests: ['pass', 'pass', 'fail'],
      step: {
        kind: 'Result',
        text: 'Tests failed',
        output: 'FAILED test_x',
        state: 'failed',
      },
    })

    expect(parseEvent(text)).toEqual({
      status: 'retrying',
      attempt: 2,
      maxAttempts: 3,
      tests: ['pass', 'pass', 'fail'],
      step: {
        kind: 'Result',
        text: 'Tests failed',
        output: 'FAILED test_x',
        state: 'failed',
      },
    })
  })

  it('gives null for text that is not JSON', () => {
    expect(parseEvent('hello')).toBeNull()
    expect(parseEvent('')).toBeNull()
  })

  it('gives null when there is no status word', () => {
    expect(
      parseEvent('{"step":{"kind":"Doing","text":"x","state":"done"}}'),
    ).toBeNull()
    expect(parseEvent('{"status":5}')).toBeNull()
    expect(parseEvent('[1,2]')).toBeNull()
    expect(parseEvent('null')).toBeNull()
  })

  it('drops a damaged step but keeps the status', () => {
    expect(parseEvent('{"status":"working","step":{"kind":"Doing"}}')).toEqual({
      status: 'working',
    })
  })

  it('ignores numbers and lists of the wrong type', () => {
    const event = parseEvent(
      '{"status":"working","attempt":"two","max_attempts":null,"tests":[1,2]}',
    )

    expect(event).toEqual({ status: 'working' })
  })
})

describe('splitMessages', () => {
  it('cuts the real server text into one message', () => {
    const { messages, rest } = splitMessages('data: {"status":"waiting"}\n\n')

    expect(messages).toEqual(['{"status":"waiting"}'])
    expect(rest).toBe('')
  })

  it('keeps an unfinished message until the rest arrives', () => {
    const first = splitMessages('data: {"status":"wor')
    expect(first.messages).toEqual([])

    const second = splitMessages(first.rest + 'king"}\n\n')
    expect(second.messages).toEqual(['{"status":"working"}'])
  })

  it('handles two messages arriving together', () => {
    const { messages } = splitMessages(
      'data: {"status":"waiting"}\n\ndata: {"status":"working"}\n\n',
    )

    expect(messages).toHaveLength(2)
  })

  it('skips ping comments', () => {
    const { messages } = splitMessages(': ping\n\ndata: {"status":"ready"}\n\n')

    expect(messages).toEqual(['{"status":"ready"}'])
  })

  it('accepts \\r\\n line endings', () => {
    const { messages } = splitMessages('data: {"status":"ready"}\r\n\r\n')

    expect(messages).toEqual(['{"status":"ready"}'])
  })

  it('gives nothing for empty text', () => {
    expect(splitMessages('')).toEqual({ messages: [], rest: '' })
  })
})
