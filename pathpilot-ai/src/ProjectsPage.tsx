
import { useState } from 'react'
import {
  CheckCircle2,
  
  Code2,
  ExternalLink,
  FolderKanban,
  Search,
  Target,
} from 'lucide-react'

type Project = {
  title: string
  career: string[]
  difficulty: string
  duration: string
  skills: string[]
  description: string
  steps: string[]
  resourceUrl: string
}

const projects: Project[] = [
  {
    title: 'Personal Portfolio Website',
    career: ['Software Developer', 'Frontend Developer'],
    difficulty: 'Beginner',
    duration: '3–5 days',
    skills: ['HTML', 'CSS', 'JavaScript'],
    description:
      'Build a portfolio that showcases your skills, projects, and achievements.',
    steps: [
      'Create an introduction and About section.',
      'Add your skills and project cards.',
      'Make the layout responsive.',
      'Deploy the website and add its live link.',
    ],
    resourceUrl: 'https://developer.mozilla.org/en-US/docs/Learn_web_development',
  },
  {
    title: 'Student Performance Dashboard',
    career: ['Data Analyst'],
    difficulty: 'Intermediate',
    duration: '4–7 days',
    skills: ['Python', 'pandas', 'Data Visualization'],
    description:
      'Analyze student marks and attendance to discover performance patterns.',
    steps: [
      'Find or create a sample student dataset.',
      'Clean missing or inconsistent data.',
      'Calculate averages and identify trends.',
      'Create charts and write your findings.',
    ],
    resourceUrl: 'https://pandas.pydata.org/docs/getting_started/',
  },
  {
    title: 'Mobile App UI Prototype',
    career: ['UI/UX Designer'],
    difficulty: 'Beginner',
    duration: '3–5 days',
    skills: ['Figma', 'Wireframing', 'Prototyping'],
    description:
      'Design a clean mobile app experience for a real user problem.',
    steps: [
      'Choose a problem and define your target user.',
      'Sketch the main screens.',
      'Create polished screens in Figma.',
      'Connect screens into a clickable prototype.',
    ],
    resourceUrl: 'https://help.figma.com/',
  },
  {
    title: 'Movie Recommendation System',
    career: ['AI / ML Engineer'],
    difficulty: 'Intermediate',
    duration: '5–8 days',
    skills: ['Python', 'pandas', 'Recommendation Systems'],
    description:
      'Recommend movies based on genres or similarities between items.',
    steps: [
      'Choose a movie dataset.',
      'Clean and explore the dataset.',
      'Build a simple similarity-based recommender.',
      'Test recommendations and document limitations.',
    ],
    resourceUrl: 'https://scikit-learn.org/stable/',
  },
  {
    title: 'Campus Event Planner',
    career: ['Software Developer', 'Frontend Developer'],
    difficulty: 'Intermediate',
    duration: '5–7 days',
    skills: ['React', 'TypeScript', 'Local Storage'],
    description:
      'Build an app to browse campus events, save favorites, and track registrations.',
    steps: [
      'Display a list of campus events.',
      'Add search and category filters.',
      'Allow users to save favorite events.',
      'Test the app and publish a demo.',
    ],
    resourceUrl: 'https://react.dev/learn',
  },
  {
    title: 'AI Career Recommendation Prototype',
    career: ['Product Manager', 'Software Developer', 'AI / ML Engineer'],
    difficulty: 'Intermediate',
    duration: '5–7 days',
    skills: ['User Research', 'React', 'Recommendation Logic'],
    description:
      'Create a prototype that matches a learner profile to possible career paths.',
    steps: [
      'Define the learner information you need.',
      'Create a small set of career profiles.',
      'Implement transparent matching rules.',
      'Test with two different learner profiles.',
    ],
    resourceUrl: 'https://react.dev/learn',
  },
]

export default function ProjectsPage() {
  const [search, setSearch] = useState('')
  const [career, setCareer] = useState(
    () =>
      localStorage.getItem('pathpilot-profile-career') ||
      'Software Developer',
  )
  const [completed, setCompleted] = useState<string[]>(() => {
    try {
      return JSON.parse(
        localStorage.getItem('pathpilot-projects-completed') || '[]',
      ) as string[]
    } catch {
      return []
    }
  })
  const [selectedProject, setSelectedProject] = useState<string | null>(null)

  const filteredProjects = projects.filter((project) => {
    const matchesCareer = project.career.includes(career)
    const matchesSearch = [
      project.title,
      project.description,
      ...project.skills,
    ]
      .join(' ')
      .toLowerCase()
      .includes(search.toLowerCase())

    return matchesCareer && matchesSearch
  })

  function toggleComplete(title: string) {
    const updated = completed.includes(title)
      ? completed.filter((item) => item !== title)
      : [...completed, title]

    setCompleted(updated)
    localStorage.setItem(
      'pathpilot-projects-completed',
      JSON.stringify(updated),
    )
  }

  return (
    <main className="roadmap-page">
      <header className="roadmap-header">
        <div>
          <p className="roadmap-eyebrow">BUILD REAL-WORLD EXPERIENCE</p>
          <h1>Projects that prove your skills</h1>
          <p className="roadmap-muted">
            Turn what you learn into practical work you can show employers.
          </p>
        </div>
        <div className="roadmap-header-icon">
          <FolderKanban size={23} />
        </div>
      </header>

      <section className="roadmap-settings">
        <label>
          <span>Target career</span>
          <select
            value={career}
            onChange={(event) => setCareer(event.target.value)}
          >
            <option>Software Developer</option>
            <option>Frontend Developer</option>
            <option>Data Analyst</option>
            <option>UI/UX Designer</option>
            <option>AI / ML Engineer</option>
            <option>Product Manager</option>
          </select>
        </label>

        <label>
          <span>Find a project</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Search size={17} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search projects or skills..."
            />
          </div>
        </label>
      </section>

      <section className="roadmap-progress-card">
        <div className="roadmap-progress-top">
          <div>
            <p className="roadmap-eyebrow">YOUR PROJECT PORTFOLIO</p>
            <h2>
              {completed.length} of {projects.length} projects completed
            </h2>
          </div>
          <Target size={22} />
        </div>
        <p className="roadmap-muted">
          Finish a project, document what you built, and add its demo or
          repository link to your portfolio.
        </p>
      </section>

      <section className="roadmap-phases">
        <div className="roadmap-section-title">
          <div>
            <h2>Recommended projects</h2>
            <p>Choose a project that matches your career goal.</p>
          </div>
          <Code2 size={21} />
        </div>

        {filteredProjects.length === 0 ? (
          <p className="roadmap-muted">
            No projects found. Try another search or target career.
          </p>
        ) : (
          filteredProjects.map((project) => {
            const isDone = completed.includes(project.title)
            const isExpanded = selectedProject === project.title

            return (
              <article className="roadmap-phase" key={project.title}>
                <div className="roadmap-phase-heading">
                  <span className="roadmap-phase-number">
                    {isDone ? (
                      <CheckCircle2 size={19} />
                    ) : (
                      <FolderKanban size={19} />
                    )}
                  </span>

                  <span className="roadmap-phase-copy">
                    <strong>{project.title}</strong>
                    <small>
                      {project.difficulty} · {project.duration}
                    </small>
                    <small>{project.description}</small>
                    <small>Skills: {project.skills.join(', ')}</small>
                  </span>
                </div>

                {isExpanded && (
                  <div style={{ padding: '0 16px 16px' }}>
                    <strong>What to build</strong>
                    <ol>
                      {project.steps.map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ol>
                    <a
                      className="roadmap-resource-link"
                      href={project.resourceUrl}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open learning resource <ExternalLink size={15} />
                    </a>
                  </div>
                )}

                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 12,
                    padding: '0 16px 16px',
                  }}
                >
                  <button
                    type="button"
                    className="roadmap-text-button"
                    onClick={() =>
                      setSelectedProject(isExpanded ? null : project.title)
                    }
                  >
                    {isExpanded ? 'Hide instructions' : 'View instructions'}
                  </button>

                  <button
                    type="button"
                    className="roadmap-text-button"
                    onClick={() => toggleComplete(project.title)}
                  >
                    {isDone ? 'Mark incomplete' : 'Mark complete'}
                  </button>
                </div>
              </article>
            )
          })
        )}
      </section>
    </main>
  )
}
