import { Download } from 'lucide-react'
import type { BuildState } from '../build/buildState'
import { isFinal } from '../build/buildState'
import { toPlainSteps } from '../build/plainSteps'
import { BuildTimeline } from '../components/BuildTimeline'
import { Button } from '../components/Button'
import { Notice } from '../components/Notice'
import { useDownload } from '../hooks/useDownload'
import { useTick } from '../hooks/useTick'

type Props = {
  projectId: string
  title: string // the project's name
  build: BuildState
  error: string | null // a plain sentence when the live connection failed
  onReopen: () => void // open the project's live stream again (the server replays its history)
}

// Shows one project: its timeline, plus a plain sentence for whatever state it is in.
// The take-home zip (F-7). It exists only while the project is ready, so the hook (and its state) starts fresh each time.
function DownloadButton({ projectId }: { projectId: string }) {
  const { loading, error, download } = useDownload(projectId)
  return (
    <>
      <Button variant="primary" loading={loading} onClick={download}>
        {!loading && <Download size={16} aria-hidden />}
        {loading ? 'Preparing your download…' : 'Download your project (.zip)'}
      </Button>
      {error && (
        <span className="notice__text" role="alert">
          {error}
        </span>
      )}
    </>
  )
}

export function BuildScreen({
  projectId,
  title,
  build,
  error,
  onReopen,
}: Props) {
  const lastStep = build.steps[build.steps.length - 1]
  const hasStarted = build.steps.length > 0
  // Only tick while the build is going: a finished build's words never change.
  const tick = useTick(!isFinal(build.status))

  return (
    <div className="start">
      <BuildTimeline
        title={title}
        status={build.status}
        steps={toPlainSteps(build.steps, build.status, tick)}
        details={build.steps}
        tests={build.tests}
        attempt={build.attempt ?? undefined}
        maxAttempts={build.maxAttempts ?? undefined}
      />

      {/* Empty state: a new project that nothing has worked on yet. */}
      {!hasStarted && !isFinal(build.status) && !error && (
        <Notice tone="info" title="Waiting to start">
          Your request is saved. Nothing has been built yet: the questions, the
          plan and the build arrive in the next steps of the project.
        </Notice>
      )}

      {build.status === 'ready' && (
        <Notice
          tone="success"
          title="Your API passed its tests"
          action={<DownloadButton projectId={projectId} />}
        >
          Download the project to keep it. The live link arrives in a later
          step.
        </Notice>
      )}

      {(build.status === 'failed' || build.status === 'stopped') && (
        <Notice
          tone="error"
          title={
            build.status === 'failed'
              ? 'The build did not finish'
              : 'The build was stopped'
          }
        >
          {lastStep ? lastStep.text : 'No reason was given.'}
        </Notice>
      )}

      {error && (
        <Notice
          tone="error"
          title="Live progress stopped"
          action={
            <Button variant="secondary" onClick={onReopen}>
              Open this project again
            </Button>
          }
        >
          {error}
        </Notice>
      )}
    </div>
  )
}
