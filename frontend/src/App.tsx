import { AppShell } from './components/AppShell'
import { Notice } from './components/Notice'
import { Sidebar } from './components/Sidebar'
import { useBuild } from './hooks/useBuild'
import { useProjectList } from './hooks/useProjectList'
import { NAMING, waitingForName } from './build/naming'
import { listRefreshKey } from './build/sidebar'
import { BuildScreen } from './screens/BuildScreen'
import { StartScreen } from './screens/StartScreen'

// The page: the project list on the left; on the right either the Start screen
// (no project open) or the project's live timeline.
function App() {
  const { state, start, open, reset } = useBuild()

  // Fetch the list again when a project opens, its status changes, or the agent first names the API.
  const refreshKey = listRefreshKey(state.projectId, state.build)
  const {
    projects: listed,
    error: listError,
    loadedKey,
  } = useProjectList(refreshKey)

  // Until the backend has the API's real name, show "Naming your API…" (not the cut-off request) in the
  // sidebar, and wait with the Build screen. A live-stream error shows at once, so the person can reopen.
  const naming =
    state.projectId !== null &&
    state.error === null &&
    waitingForName(state.build, loadedKey === refreshKey)
  const projects = naming
    ? listed.map((project) =>
        project.id === state.projectId ? { ...project, name: NAMING } : project,
      )
    : listed

  const openProject = projects.find((project) => project.id === state.projectId)

  return (
    <AppShell
      sidebar={
        <Sidebar
          projects={projects}
          activeId={state.projectId}
          onNewProject={reset}
          onSelect={open}
        />
      }
    >
      {listError && (
        <Notice tone="warning" title="We could not load your projects">
          {listError}
        </Notice>
      )}
      {state.projectId === null ? (
        <StartScreen
          loading={state.starting}
          error={state.error}
          onSubmit={start}
        />
      ) : naming ? (
        <div className="start">
          <Notice tone="info" title={NAMING}>
            The agent is reading your request. Your project opens in a moment.
          </Notice>
        </div>
      ) : (
        <BuildScreen
          projectId={state.projectId}
          title={openProject?.name ?? 'Your API'}
          build={state.build}
          error={state.error}
          onReopen={() => open(state.projectId ?? '')}
        />
      )}
    </AppShell>
  )
}

export default App
