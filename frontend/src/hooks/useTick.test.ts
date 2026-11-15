import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useTick } from './useTick'

// Fake timers fake only the CLOCK (so a test need not wait seconds). No data is faked.
describe('useTick', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('goes up by one every interval while running', () => {
    const { result } = renderHook(() => useTick(true, 1000))
    expect(result.current).toBe(0)

    act(() => vi.advanceTimersByTime(3000))

    expect(result.current).toBe(3)
  })

  it('stays at 0 when not running', () => {
    const { result } = renderHook(() => useTick(false, 1000))

    act(() => vi.advanceTimersByTime(5000))

    expect(result.current).toBe(0)
  })

  it('stops counting once running turns false', () => {
    const { result, rerender } = renderHook(
      ({ running }) => useTick(running, 1000),
      { initialProps: { running: true } },
    )
    act(() => vi.advanceTimersByTime(2000))

    rerender({ running: false })
    act(() => vi.advanceTimersByTime(5000))

    expect(result.current).toBe(2)
  })

  it('leaves no timer behind when the screen goes away', () => {
    const { unmount } = renderHook(() => useTick(true, 1000))

    unmount()

    expect(vi.getTimerCount()).toBe(0)
  })
})
