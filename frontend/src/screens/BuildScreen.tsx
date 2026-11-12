import type { BuildState } from '../build/buildState'
import { isFinal } from '../build/buildState'
import { BuildTimeline } from '../components/BuildTimeline'
import { Button } from '../components/Button'
import { Notice } from '../components/Notice'

type Props = {
  title: string // the project's name
  build: BuildState
  error: string | null // a plain sentence when the live connection failed
  onReopen: () => void // open the project's live stream again (the server replays its history)
}

// Shows one project: its timeline, plus a plain sentence for whatever state it is in.
export function BuildScreen({ title, build, error, onReopen }: Props) {
  const lastStep = build.steps[build.steps.length - 1]
  const hasStarted = build.steps.length > 0

  return (
    <div className="start">
      <BuildTimeline
        title={title}
        status={build.status}
        steps={build.steps}
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
        <Notice tone="success" title="Your API passed its tests">
          The live link and the download arrive in a later step.
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
