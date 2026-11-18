import { Download, Square } from 'lucide-react'
import { useState } from 'react'
import type { BuildState } from '../build/buildState'
import { isFinal } from '../build/buildState'
import { nothingBuilt, zipName } from '../build/naming'
import { toPlainSteps } from '../build/plainSteps'
import { BuildTimeline } from '../components/BuildTimeline'
import { Button } from '../components/Button'
import { Notice } from '../components/Notice'
import { useDownload } from '../hooks/useDownload'
import { useReadyProject } from '../hooks/useReadyProject'
import { useStopBuild } from '../hooks/useStopBuild'
import { ReadyDetails } from './ReadyDetails'
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
function DownloadButton({
  projectId,
  fileName,
}: {
  projectId: string
  fileName: string
}) {
  const { loading, error, download } = useDownload(projectId, fileName)
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

// Everything under "Your API passed its tests": the details, the live link, and the zip.
// It exists only while the project is ready, so its state starts fresh each time.
function ReadyActions({
  projectId,
  title,
}: {
  projectId: string
  title: string
}) {
  const ready = useReadyProject(projectId, true)
  return (
    <>
      <ReadyDetails
        project={ready.project}
        loading={ready.loading}
        error={ready.error}
        onReload={ready.reload}
        waking={ready.waking}
        wakeError={ready.wakeError}
        onWake={ready.wake}
      />
      <DownloadButton
        projectId={projectId}
        fileName={zipName(title, projectId)}
      />
    </>
  )
}

// Stop a running build (F-18). Two steps, so one stray click can't throw a build away:
// "Stop build", then "Stop this build?" with "Yes, stop it" / "Keep building".
// It exists only while the build is running, so its state starts fresh for every build.
function StopControl({ projectId }: { projectId: string }) {
  const [confirming, setConfirming] = useState(false)
  const { stopping, error, stop } = useStopBuild(projectId)

  if (!confirming) {
    return (
      <div className="stop-control">
        <Button variant="ghost" onClick={() => setConfirming(true)}>
          <Square size={14} aria-hidden className="stop-control__icon" />
          Stop build
        </Button>
      </div>
    )
  }
  return (
    <Notice
      tone="warning"
      title="Stop this build?"
      action={
        <div className="stop-control__choices">
          <Button variant="secondary" loading={stopping} onClick={stop}>
            {stopping ? 'Stopping…' : 'Yes, stop it'}
          </Button>
          {!stopping && (
            <Button variant="ghost" onClick={() => setConfirming(false)}>
              Keep building
            </Button>
          )}
          {error && (
            <span className="notice__text" role="alert">
              {error}
            </span>
          )}
        </div>
      }
    >
      Nothing will be kept: no download and no live link. You can send the
      request again later.
    </Notice>
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
  // A refused request (nothing was written or tested): show only its result, not "Finalizing your API…".
  const onlyResult = nothingBuilt(build)
  // Only tick while the build is going: a finished build's words never change.
  const tick = useTick(!isFinal(build.status))

  return (
    <div className="start">
      <BuildTimeline
        title={title}
        status={onlyResult ? 'notBuilt' : build.status}
        steps={onlyResult ? [] : toPlainSteps(build.steps, build.status, tick)}
        details={onlyResult ? [] : build.steps}
        tests={build.tests}
        attempt={onlyResult ? undefined : (build.attempt ?? undefined)}
        maxAttempts={build.maxAttempts ?? undefined}
      />

      {/* While the build runs, the person can stop it (F-18). Hidden if the live stream is lost:
          then we don't know whether it is still running. */}
      {!isFinal(build.status) && !error && (
        <StopControl projectId={projectId} />
      )}

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
          action={<ReadyActions projectId={projectId} title={title} />}
        >
          Your API is built and tested. Open it and try it, or download it to
          keep.
        </Notice>
      )}

      {(build.status === 'failed' || build.status === 'stopped') && (
        <Notice
          tone={onlyResult ? 'warning' : 'error'} // a refusal is not an error: amber, like its "Not built" badge
          title={
            onlyResult
              ? 'Nothing was built'
              : build.status === 'failed'
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
