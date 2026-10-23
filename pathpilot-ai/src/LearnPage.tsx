
import { useState } from 'react'
import {
  BookOpen,
  CheckCircle2,
  Clock3,
  ExternalLink,
  GraduationCap,
  Search,
  Target,
} from 'lucide-react'

type LearningResource = {
  title: string
  category: string
  duration: string
  description: string
  url: string
  career: string[]
}

const resources: LearningResource[] = [
  {
    title: 'Your First Website',
    category: 'Web Development',
    duration: '2 hours',
    description: 'Learn HTML structure and build your first webpage.',
    url: 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Getting_started/Your_first_website',
    career: ['Software Developer', 'Frontend Developer'],
  },
  {
    title: 'React Learn',
    category: 'Frontend',
    duration: '3 hours',
    description: 'Learn components, props, events, and state.',
    url: 'https://react.dev/learn',
    career: ['Software Developer', 'Frontend Developer'],
  },
  {
    title: 'SQLBolt',
    category: 'Data Analysis',
    duration: '5 hours',
    description: 'Practice SQL queries through interactive lessons.',
    url: 'https://sqlbolt.com/',
    career: ['Data Analyst'],
  },
  {
    title: 'Python with pandas',
    category: 'Data Analysis',
    duration: '4 hours',
    description: 'Explore datasets and learn basic data manipulation.',
    url: 'https://pandas.pydata.org/docs/getting_started/',
    career: ['Data Analyst', 'AI / ML Engineer'],
  },
  {
    title: 'Figma Design Basics',
    category: 'UI/UX Design',
    duration: '3 hours',
    description: 'Explore interface design and prototyping.',
    url: 'https://help.figma.com/',
    career: ['UI/UX Designer'],
  },
  {
    title: 'Machine Learning',
    category: 'Artificial Intelligence',
    duration: '5 hours',
    description: 'Start learning machine learning concepts and workflows.',
    url: 'https://developers.google.com/machine-learning/crash-course',
    career: ['AI / ML Engineer'],
  },
  {
    title: 'Product Management',
    category: 'Product',
    duration: '2 hours',
    description: 'Explore product discovery, strategy, and prioritization.',
    url: 'https://www.atlassian.com/agile/product-management',
    career: ['Product Manager'],
  },
]

export default function LearnPage() {
  const [search, setSearch] = useState('')
  const [career, setCareer] = useState(
    () => localStorage.getItem('pathpilot-profile-career')
      || 'Software Developer',
  )
  const [completed, setCompleted] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('pathpilot-learn-completed') || '[]')
    } catch {
      return []
    }
  })

  const filteredResources = resources.filter((resource) => {
    const matchesCareer = resource.career.includes(career)
    const matchesSearch =
      `${resource.title} ${resource.category} ${resource.description}`
        .toLowerCase()
        .includes(search.toLowerCase())

    return matchesCareer && matchesSearch
  })

  function toggleComplete(title: string) {
    const updated = completed.includes(title)
      ? completed.filter((item) => item !== title)
      : [...completed, title]

    setCompleted(updated)
    localStorage.setItem('pathpilot-learn-completed', JSON.stringify(updated))
  }

  return (
    <main className="roadmap-page">
      <header className="roadmap-header">
        <div>
          <p className="roadmap-eyebrow">YOUR LEARNING SPACE</p>
          <h1>Learn and grow</h1>
          <p className="roadmap-muted">
            Build skills for your target career, one lesson at a time.
          </p>
        </div>
        <div className="roadmap-header-icon">
          <GraduationCap size={23} />
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
          <span>Find a learning resource</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Search size={17} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search lessons..."
            />
          </div>
        </label>
      </section>

      <section className="roadmap-progress-card">
        <div className="roadmap-progress-top">
          <div>
            <p className="roadmap-eyebrow">YOUR LEARNING PROGRESS</p>
            <h2>{completed.length} lessons completed</h2>
          </div>
          <BookOpen size={22} />
        </div>
        <p className="roadmap-muted">
          Mark a lesson complete after you finish studying it.
        </p>
      </section>

      <section className="roadmap-phases">
        <div className="roadmap-section-title">
          <div>
            <h2>Recommended resources</h2>
            <p>Choose a lesson and learn at your own pace.</p>
          </div>
          <Target size={21} />
        </div>

        {filteredResources.length === 0 ? (
          <p className="roadmap-muted">
            No resources found. Try another search or target career.
          </p>
        ) : (
          filteredResources.map((resource) => {
            const isDone = completed.includes(resource.title)

            return (
              <article className="roadmap-phase" key={resource.title}>
                <div className="roadmap-phase-heading">
                  <span className="roadmap-phase-number">
                    {isDone ? <CheckCircle2 size={19} /> : <BookOpen size={19} />}
                  </span>
                  <span className="roadmap-phase-copy">
                    <strong>{resource.title}</strong>
                    <small>{resource.category}</small>
                    <small>{resource.description}</small>
                    <small>
                      <Clock3 size={13} /> {resource.duration}
                    </small>
                  </span>
                </div>

                <div style={{ display: 'flex', gap: 12, padding: '0 16px 16px' }}>
                  <a
                    className="roadmap-resource-link"
                    href={resource.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open lesson <ExternalLink size={15} />
                  </a>
                  <button
                    type="button"
                    className="roadmap-text-button"
                    onClick={() => toggleComplete(resource.title)}
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
