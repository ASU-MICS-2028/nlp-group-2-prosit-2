// The details of a finished project for the Ready screen (F-14): files, size, tests, and the live API.
// Loads when the project is ready, can be loaded again, and can wake a sleeping live API.

import { useEffect, useRef, useState } from 'react'
import {
  errorMessage,
  getProject,
  wakeProject,
  type ProjectResponse,
} from '../api/client'

export function useReadyProject(projectId: string, ready: boolean) {
  const [project, setProject] = useState<ProjectResponse | null>(null)
  const [error, setError] = useState<string | null>(null) // why the details could not load
  const [reloadKey, setReloadKey] = useState(0) // changing it loads the details again
  const [waking, setWaking] = useState(false)
  const [wakeError, setWakeError] = useState<string | null>(null)
  const wakingRef = useRef(false) // blocks a second click before React has re-drawn the disabled button
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false // the person left the screen: do not update a screen that is gone
    }
  }, [])

  useEffect(() => {
    if (!ready) return // nothing to show before the build is ready
    let cancelled = false // set to true if the page goes away (or the key changes) before the answer

    getProject(projectId).then(
      (details) => {
        if (cancelled) return
        setProject(details)
        setError(null)
      },
      (failure: unknown) => {
        if (cancelled) return
        setError(errorMessage(failure))
      },
    )

    return () => {
      cancelled = true
    }
  }, [projectId, ready, reloadKey])

  // Loading means: we want the details, and have neither them nor an error yet.
  const loading = ready && project === null && error === null

  function reload() {
    setError(null) // back to "loading" while the new answer is on its way
    setReloadKey((key) => key + 1)
  }

  async function wake() {
    if (wakingRef.current) return
    wakingRef.current = true
    setWaking(true)
    setWakeError(null)
    try {
      await wakeProject(projectId)
      // Read the new live_status from the server instead of guessing it.
      const details = await getProject(projectId)
      if (mountedRef.current) setProject(details)
    } catch (failure) {
      if (mountedRef.current) setWakeError(errorMessage(failure))
    } finally {
      wakingRef.current = false
      if (mountedRef.current) setWaking(false)
    }
  }

  return { project, loading, error, reload, waking, wakeError, wake }
}
