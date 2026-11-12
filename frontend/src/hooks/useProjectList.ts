// Loads the sidebar's list of projects.

import { useEffect, useState } from 'react'
import { errorMessage, listProjects } from '../api/client'
import { toSidebarProject } from '../build/sidebar'
import type { ProjectSummary } from '../components/Sidebar'

// `refreshKey` is any text that changes when the list should be fetched again
// (for example "p_3:ready" after project p_3 finishes). The same text means "no new fetch".
export function useProjectList(refreshKey: string) {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false // set to true if the page goes away (or the key changes) before the answer

    listProjects().then(
      (rows) => {
        if (cancelled) return
        const now = new Date()
        setProjects(rows.map((row) => toSidebarProject(row, now)))
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
  }, [refreshKey])

  return { projects, error }
}
