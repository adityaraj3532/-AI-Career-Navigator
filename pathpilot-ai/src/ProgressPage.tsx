
import { useEffect, useState } from 'react'
import {
  ArrowUpRight,
  BriefcaseBusiness,
  CheckCircle2,
  Circle,
  Code2,
  ExternalLink,
  FileText,
  Plus,
  Target,
  Trash2,
} from 'lucide-react'

type Project = {
  id: number
  name: string
  repo: string
  demo: string
}

const readinessItems = [
  { id: 'resume', title: 'Resume is ready', detail: 'Include relevant skills and projects.' },
  { id: 'portfolio', title: 'Portfolio is available', detail: 'Show your best work in one place.' },
  { id: 'interview', title: 'Practised technical interviews', detail: 'Solve problems and explain your approach.' },
  { id: 'explanation', title: 'Can explain my projects', detail: 'Describe your decisions, challenges, and solutions.' },
  { id: 'applications', title: 'Started applying to relevant roles', detail: 'Track suitable internships and entry-level jobs.' },
]

const starterProjects: Project[] = []

export default function ProgressPage() {
  const [completed, setCompleted] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('pathpilot-readiness') || '[]')
    } catch {
      return []
    }
  })

  const [projects, setProjects] = useState<Project[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('pathpilot-projects') || '[]')
    } catch {
      return starterProjects
    }
  })

  const [name, setName] = useState('')
  const [repo, setRepo] = useState('')
  const [demo, setDemo] = useState('')
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    localStorage.setItem('pathpilot-readiness', JSON.stringify(completed))
  }, [completed])

  useEffect(() => {
    localStorage.setItem('pathpilot-projects', JSON.stringify(projects))
  }, [projects])

  const readiness = Math.round((completed.length / readinessItems.length) * 100)

  function toggleItem(id: string) {
    setCompleted((previous) =>
      previous.includes(id)
        ? previous.filter((item) => item !== id)
        : [...previous, id],
    )
  }

  function addProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim()) return

    setProjects((previous) => [
      ...previous,
      {
        id: Date.now(),
        name: name.trim(),
        repo: repo.trim(),
        demo: demo.trim(),
      },
    ])

    setName('')
    setRepo('')
    setDemo('')
    setShowForm(false)
  }

  function removeProject(id: number) {
    setProjects((previous) => previous.filter((project) => project.id !== id))
  }

  return (
    <main className="progress-page">
      <header className="progress-header">
        <div>
          <p className="progress-eyebrow">YOUR CAREER JOURNEY</p>
          <h1>Progress & Job Readiness</h1>
          <p className="progress-muted">
            Track what you learn. Show what you can do.
          </p>
        </div>
        <div className="progress-header-icon"><Target size={23} /></div>
      </header>

      <section className="progress-summary">
        <div className="progress-summary-top">
          <div>
            <p className="progress-eyebrow">READINESS CHECKLIST</p>
            <h2>{completed.length} of {readinessItems.length} steps completed</h2>
            <p className="progress-muted">
              This measures your preparation, not your chances of getting hired.
            </p>
          </div>
          <strong className="progress-score">{readiness}%</strong>
        </div>
        <div className="progress-track">
          <div style={{ width: `${readiness}%` }} />
        </div>
      </section>

      <section className="progress-section">
        <div className="progress-section-heading">
          <div className="progress-section-icon"><Code2 size={19} /></div>
          <div>
            <h2>Proof of your skills</h2>
            <p>Add projects an employer can actually inspect.</p>
          </div>
        </div>

        {projects.length === 0 ? (
          <div className="progress-empty">
            <div className="progress-empty-icon"><FileText size={24} /></div>
            <h3>No projects added yet</h3>
            <p>Add a project with its GitHub repository or live demo.</p>
          </div>
        ) : (
          <div className="progress-project-list">
            {projects.map((project) => (
              <article className="progress-project" key={project.id}>
                <div className="progress-project-icon"><Code2 size={18} /></div>
                <div className="progress-project-info">
                  <h3>{project.name}</h3>
                  <div className="progress-project-links">
                    {project.repo && (
                      <a href={project.repo} target="_blank" rel="noreferrer">
                        Repository <ExternalLink size={13} />
                      </a>
                    )}
                    {project.demo && (
                      <a href={project.demo} target="_blank" rel="noreferrer">
                        Live demo <ExternalLink size={13} />
                      </a>
                    )}
                    {!project.repo && !project.demo && (
                      <span className="progress-muted">No links added</span>
                    )}
                  </div>
                </div>
                <button
                  className="progress-icon-button"
                  type="button"
                  aria-label={`Delete ${project.name}`}
                  onClick={() => removeProject(project.id)}
                >
                  <Trash2 size={16} />
                </button>
              </article>
            ))}
          </div>
        )}

        {showForm ? (
          <form className="progress-project-form" onSubmit={addProject}>
            <label>
              Project name *
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Student Task Tracker"
                required
              />
            </label>
            <label>
              GitHub repository URL
              <input
                type="url"
                value={repo}
                onChange={(event) => setRepo(event.target.value)}
                placeholder="https://github.com/username/project"
              />
            </label>
            <label>
              Live demo URL
              <input
                type="url"
                value={demo}
                onChange={(event) => setDemo(event.target.value)}
                placeholder="https://your-project.example"
              />
            </label>
            <div className="progress-form-actions">
              <button className="progress-secondary-button" type="button" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button className="progress-primary-button" type="submit">
                Save project
              </button>
            </div>
          </form>
        ) : (
          <button className="progress-add-button" type="button" onClick={() => setShowForm(true)}>
            <Plus size={17} /> Add a project
          </button>
        )}
      </section>

      <section className="progress-section">
        <div className="progress-section-heading">
          <div className="progress-section-icon"><BriefcaseBusiness size={19} /></div>
          <div>
            <h2>Job readiness checklist</h2>
            <p>Tick an item when you have genuinely done it.</p>
          </div>
        </div>

        <div className="progress-checklist">
          {readinessItems.map((item) => {
            const isDone = completed.includes(item.id)

            return (
              <button
                className={`progress-check-item ${isDone ? 'is-complete' : ''}`}
                key={item.id}
                type="button"
                onClick={() => toggleItem(item.id)}
              >
                {isDone
                  ? <CheckCircle2 className="progress-check-icon" size={21} />
                  : <Circle className="progress-check-icon" size={21} />}
                <span>
                  <strong>{item.title}</strong>
                  <small>{item.detail}</small>
                </span>
                <span className="progress-check-status">
                  {isDone ? 'Done' : 'Mark done'}
                </span>
              </button>
            )
          })}
        </div>
      </section>

      <section className="progress-next-step">
        <div className="progress-next-icon"><Target size={20} /></div>
        <div>
          <h2>Your next step</h2>
          <p>
            {completed.length < readinessItems.length
              ? `Focus next on: ${readinessItems.find((item) => !completed.includes(item.id))?.title}. Build evidence as you go.`
              : 'Your checklist is complete. Keep improving your projects and applying to roles that fit your skills.'}
          </p>
        </div>
        <ArrowUpRight size={19} />
      </section>
    </main>
  )
}
