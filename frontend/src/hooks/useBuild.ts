// Starts a project and follows its live progress. This is the only place the screen
// talks to the backend about ONE project (API calls live in hooks, not in components).

import { useEffect, useRef, useState } from 'react'
import { errorMessage, startProject, streamEvents } from '../api/client'
import {
  applyEvent,
  emptyBuild,
  isFinal,
  type BuildState,
} from '../build/buildState'

export type BuildScreenState = {
  starting: boolean // true while we wait for the server to create the project
  projectId: string | null // null means "no project open": show the Start screen
  build: BuildState
  error: string | null // a plain sentence for the user, or null
}

const NOTHING_OPEN: BuildScreenState = {
  starting: false,
  projectId: null,
  build: emptyBuild,
  error: null,
}

const ENDED_EARLY =
  'The live connection ended before the build finished. Open the project again to see where it got to.'

export function useBuild() {
  const [state, setState] = useState<BuildScreenState>(NOTHING_OPEN)

  // A "ref" is a box that keeps its value between renders without causing a new render.
  const streamRef = useRef<AbortController | null>(null) // lets us hang up on the live stream
  const startingRef = useRef(false) // blocks a second click while the first is still working
  const mountedRef = useRef(false) // false after the page is gone, so we never start a stream nobody sees

  function stopWatching() {
    streamRef.current?.abort()
    streamRef.current = null
  }

  // Runs when the page appears; the function it returns runs when the page goes away.
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      stopWatching()
    }
  }, [])

  // Open the live stream of one project. The server first replays everything that already
  // happened, so opening an old project shows its whole timeline.
  function watch(projectId: string) {
    stopWatching()
    const controller = new AbortController()
    streamRef.current = controller
    setState({ starting: false, projectId, build: emptyBuild, error: null })

    streamEvents(
      projectId,
      (event) => {
        if (controller.signal.aborted) return // we moved on to another project
        setState((current) => ({
          ...current,
          build: applyEvent(current.build, event),
        }))
      },
      controller.signal,
    ).then(
      () => {
        if (controller.signal.aborted) return
        // The server hung up. That is normal after a final status; otherwise something went wrong.
        setState((current) =>
          isFinal(current.build.status)
            ? current
            : { ...current, error: ENDED_EARLY },
        )
      },
      (error: unknown) => {
        if (controller.signal.aborted) return
        setState((current) => ({ ...current, error: errorMessage(error) }))
      },
    )
  }

  async function start(requestText: string) {
    if (startingRef.current) return // a double click must not create two projects
    startingRef.current = true
    stopWatching()
    setState({ ...NOTHING_OPEN, starting: true })
    try {
      const project = await startProject(requestText)
      if (mountedRef.current) watch(project.id)
    } catch (error) {
      if (mountedRef.current) {
        setState({ ...NOTHING_OPEN, error: errorMessage(error) })
      }
    } finally {
      startingRef.current = false
    }
  }

  // Back to the Start screen.
  function reset() {
    stopWatching()
    setState(NOTHING_OPEN)
  }

  return { state, start, open: watch, reset }
}
