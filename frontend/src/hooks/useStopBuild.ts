// Stops a running build (F-18): idle, then stopping, then the live stream shows "stopped" (or an error sentence).

import { useEffect, useRef, useState } from 'react'
import { errorMessage, stopProject } from '../api/client'

export function useStopBuild(projectId: string) {
  // stopping stays true after the server said yes: the build ends a moment later, when the "stopped"
  // event arrives on the live stream, and then the Stop control is no longer shown at all.
  const [stopping, setStopping] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const busyRef = useRef(false) // blocks a second click before React has re-drawn the disabled button
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false // the person left the screen: do not update a screen that is gone
    }
  }, [])

  async function stop() {
    if (busyRef.current) return
    busyRef.current = true
    setStopping(true)
    setError(null)
    try {
      await stopProject(projectId)
    } catch (failure) {
      busyRef.current = false // the stop did not happen, so the person may try again
      if (mountedRef.current) {
        setStopping(false)
        setError(errorMessage(failure))
      }
    }
  }

  return { stopping, error, stop }
}
