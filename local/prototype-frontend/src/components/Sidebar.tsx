import { FolderOpen, Plus } from 'lucide-react'
import { IconTile } from './IconTile'
import { StatusPill, type Status } from './StatusPill'

export type ProjectSummary = {
  id: string
  name: string
  status: Status
  when: string
}

type Props = {
  projects: ProjectSummary[]
  activeId: string | null
  onNewProject: () => void
  onSelect: (id: string) => void
}

export function Sidebar({ projects, activeId, onNewProject, onSelect }: Props) {
  return (
    <>
      <div className="sidebar__brand">
        <span className="logo-tile" aria-hidden>
          {'{ }'}
        </span>
        <span className="t-title" style={{ fontSize: 16 }}>
          Mesora
        </span>
      </div>

      <button
        type="button"
        className="btn glow-edge"
        style={{ width: '100%' }}
        onClick={onNewProject}
      >
        <Plus size={16} aria-hidden />
        New project
      </button>

      <div>
        <h2 className="t-section" style={{ margin: '0 0 8px' }}>
          Projects
        </h2>
        {projects.length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>
            No projects yet. Describe your first API to start one.
          </p>
        ) : (
          <div className="sidebar__list">
            {projects.map((project) => (
              <button
                key={project.id}
                type="button"
                className={`project-row ${project.id === activeId ? 'project-row--active' : ''}`}
                aria-current={project.id === activeId ? 'true' : undefined}
                onClick={() => onSelect(project.id)}
              >
                <IconTile icon={FolderOpen} />
                <span className="project-row__text">
                  <span className="t-label">{project.name}</span>
                  <span className="t-caption muted">{project.when}</span>
                </span>
                <StatusPill status={project.status} />
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
