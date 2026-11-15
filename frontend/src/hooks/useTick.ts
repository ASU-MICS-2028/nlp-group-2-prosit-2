import { useEffect, useState } from 'react'

// A number that goes up by one every `everyMs` milliseconds, only while `running` is true.
// The build screen uses it to change the wording of the line that is happening now.
export function useTick(running: boolean, everyMs = 4000): number {
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!running) return
    const timer = setInterval(() => setTick((current) => current + 1), everyMs)
    // Cleanup: stop the clock when the build ends or the screen goes away, so nothing keeps running.
    return () => clearInterval(timer)
  }, [running, everyMs])

  return tick
}
