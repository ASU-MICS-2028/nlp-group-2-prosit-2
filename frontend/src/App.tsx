import { AppShell } from './components/AppShell'
import { Notice } from './components/Notice'
import { Sidebar } from './components/Sidebar'
import { useBuild } from './hooks/useBuild'
import { useProjectList } from './hooks/useProjectList'
import { BuildScreen } from './screens/BuildScreen'
import { StartScreen } from './screens/StartScreen'

// The page: the project list on the left; on the right either the Start screen
// (no project open) or the project's live timeline.
function App() {
  const { state, start, open, reset } = useBuild()

  // Fetch the list again when a project opens or its status changes, so the sidebar stays current.
  const { projects, error: listError } = useProjectList(
    `${state.projectId ?? 'none'}:${state.build.status}`,
  )

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
      ) : (
        <BuildScreen
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
