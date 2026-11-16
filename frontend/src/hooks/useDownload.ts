// Downloads a finished project's zip (F-7): idle, then loading, then saved or an error sentence.

import { useEffect, useRef, useState } from 'react'
import { downloadProject, errorMessage } from '../api/client'
import { saveFile } from '../build/saveFile'

// fileName: what the saved file is called, e.g. "clinic-appointment-api.zip" (zipName in build/naming.ts).
export function useDownload(projectId: string, fileName: string) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const busyRef = useRef(false) // blocks a second click before React has re-drawn the disabled button
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false // the person left the screen: do not update a screen that is gone
    }
  }, [])

  async function download() {
    if (busyRef.current) return
    busyRef.current = true
    setLoading(true)
    setError(null)
    try {
      saveFile(await downloadProject(projectId), fileName)
    } catch (failure) {
      if (mountedRef.current) setError(errorMessage(failure))
    } finally {
      busyRef.current = false
      if (mountedRef.current) setLoading(false)
    }
  }

  return { loading, error, download }
}
