// What the Ready screen shows under "Your API passed its tests" (F-14): the facts, the live link,
// "Wake it up" when the live API is asleep, and the zip. It only draws what it is given: the loading
// and the waking happen in useReadyProject, so every state here can be shown from plain props.

import { ExternalLink, Power } from 'lucide-react'
import { liveDocsUrl, type ProjectResponse } from '../api/client'
import { factsLine } from '../build/readyFacts'
import { Button } from '../components/Button'

type Props = {
  project: ProjectResponse | null // null until the details have loaded
  loading: boolean
  error: string | null // why the details could not load
  onReload: () => void
  waking: boolean
  wakeError: string | null
  onWake: () => void
}

export function ReadyDetails({
  project,
  loading,
  error,
  onReload,
  waking,
  wakeError,
  onWake,
}: Props) {
  // Loading state: we asked, and the answer has not come yet.
  if (project === null && loading) {
    return <p role="status">Getting the details of your API…</p>
  }

  // Error state: the details could not be loaded. Say why, and offer to try again.
  if (project === null) {
    return (
      <div className="ready-details">
        <span className="notice__text" role="alert">
          {error ?? 'The details of your API are not available.'}
        </span>
        <Button onClick={onReload} loading={loading}>
          Try again
        </Button>
      </div>
    )
  }

  const facts = factsLine(project)
  const live = project.api_url != null && project.live_status != null

  return (
    <div className="ready-details">
      {facts && <span className="notice__text">{facts}</span>}

      {/* Empty state: this project has no live link (it could not start). The zip below still works. */}
      {!live && (
        <span className="notice__text">
          There is no live link for this project. You can still download it.
        </span>
      )}

      {live && project.live_status === 'running' && (
        <div className="ready-details__row">
          {/* A real link: it opens the generated API's own Swagger page in a new tab, where "Try it out" works. */}
          <a
            className="btn btn--secondary"
            href={liveDocsUrl(project.api_url ?? '')}
            target="_blank"
            rel="noopener noreferrer"
          >
            <ExternalLink size={16} aria-hidden />
            Open your live API
          </a>
          <span className="notice__text">
            It is running now. It goes to sleep after 10 idle minutes.
          </span>
        </div>
      )}

      {live && project.live_status !== 'running' && (
        <div className="ready-details__row">
          <Button loading={waking} onClick={onWake}>
            {!waking && <Power size={16} aria-hidden />}
            {waking ? 'Waking it up…' : 'Wake it up'}
          </Button>
          <span className="notice__text">
            Your API is asleep to save memory. Wake it up to use the live link.
          </span>
        </div>
      )}

      {wakeError && (
        <span className="notice__text" role="alert">
          {wakeError}
        </span>
      )}
    </div>
  )
}
