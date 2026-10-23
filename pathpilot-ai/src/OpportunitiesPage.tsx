
import { useMemo, useState } from 'react'
import {
  Search,
  BriefcaseBusiness,
  Code2,
  Users,
  Bookmark,
  ExternalLink,
  Clock,
} from 'lucide-react'

type ApplicationStatus =
  | 'Interested'
  | 'Applied'
  | 'Interview'
  | 'Rejected'
  | 'Selected'

type Opportunity = {
  id: number
  title: string
  organization: string
  type: string
  skills: string[]
  eligibility: string
  deadline: string
  description: string
  url: string
}

// Temporary learner profile.
// Later, replace this with skills from the user's Profile page or backend.
const learnerSkills = [
  'JavaScript',
  'React',
  'Git',
  'HTML',
  'CSS',
]

const opportunities: Opportunity[] = [
  {
    id: 1,
    title: 'Software Development Intern',
    organization: 'Example Tech Company',
    type: 'Internship',
    skills: ['JavaScript', 'React', 'Git'],
    eligibility: 'Students learning software development',
    deadline: 'Check official website',
    description: 'Gain practical experience by building software features.',
    url: 'https://www.google.com/search?q=software+development+internships+India',
  },
  {
    id: 2,
    title: 'Open Source Contributor',
    organization: 'Open Source Programs',
    type: 'Open Source',
    skills: ['Git', 'JavaScript', 'Python'],
    eligibility: 'Beginners and student contributors',
    deadline: 'Varies by program',
    description: 'Contribute code, documentation, and fixes to open-source projects.',
    url: 'https://summerofcode.withgoogle.com/',
  },
  {
    id: 3,
    title: 'Student Hackathon',
    organization: 'Hackathon Opportunities',
    type: 'Hackathon',
    skills: ['React', 'Problem Solving', 'Teamwork'],
    eligibility: 'Students interested in building projects',
    deadline: 'Check event website',
    description: 'Build a project with a team and demonstrate your technical skills.',
    url: 'https://devpost.com/hackathons',
  },
  {
    id: 4,
    title: 'Frontend Development Intern',
    organization: 'Example Web Studio',
    type: 'Internship',
    skills: ['HTML', 'CSS', 'React'],
    eligibility: 'Students with basic web development knowledge',
    deadline: 'Check official website',
    description: 'Practice building accessible, responsive web interfaces.',
    url: 'https://www.google.com/search?q=frontend+internships+India',
  },
]

const categories = ['All', 'Internship', 'Hackathon', 'Open Source']

function getOpportunityMatch(requiredSkills: string[]) {
  const normalizedLearnerSkills = learnerSkills.map((skill) =>
    skill.trim().toLowerCase()
  )

  const matchedSkills = requiredSkills.filter((skill) =>
    normalizedLearnerSkills.includes(skill.trim().toLowerCase())
  )

  const missingSkills = requiredSkills.filter(
    (skill) =>
      !normalizedLearnerSkills.includes(skill.trim().toLowerCase())
  )

  const matchPercentage =
    requiredSkills.length === 0
      ? 0
      : Math.round((matchedSkills.length / requiredSkills.length) * 100)

  return {
    matchedSkills,
    missingSkills,
    matchPercentage,
  }
}

export default function OpportunitiesPage() {
  const [category, setCategory] = useState('All')
  const [search, setSearch] = useState('')

  const [saved, setSaved] = useState<number[]>(() => {
    try {
      const stored = localStorage.getItem(
        'pathpilot-saved-opportunities'
      )
      return stored ? (JSON.parse(stored) as number[]) : []
    } catch {
      return []
    }
  })

  const [applicationStatuses, setApplicationStatuses] = useState<
    Record<number, ApplicationStatus>
  >(() => {
    try {
      const stored = localStorage.getItem(
        'pathpilot-application-statuses'
      )
      return stored
        ? (JSON.parse(stored) as Record<number, ApplicationStatus>)
        : {}
    } catch {
      return {}
    }
  })
  
  const applicationCounts = {
    Interested: 0,
    Applied: 0,
    Interview: 0,
    Rejected: 0,
    Selected: 0,
    }

    Object.values(applicationStatuses).forEach((status) => {
    applicationCounts[status]++
    })

    const totalTracked = Object.keys(applicationStatuses).length


  const filteredOpportunities = useMemo(() => {
    return opportunities.filter((opportunity) => {
      const matchesCategory =
        category === 'All' || opportunity.type === category

      const searchableText = [
        opportunity.title,
        opportunity.organization,
        opportunity.type,
        ...opportunity.skills,
      ]
        .join(' ')
        .toLowerCase()

      return matchesCategory && searchableText.includes(search.toLowerCase())
    })
  }, [search, category])

  function toggleSaved(id: number) {
    setSaved((current) =>
      current.includes(id)
        ? current.filter((savedId) => savedId !== id)
        : [...current, id]
    )
  }

  return (
    <div className="page-content opportunities-page">
      <section className="opportunities-header">
        <div>
          <div className="eyebrow">
            <BriefcaseBusiness size={15} /> YOUR NEXT STEP
          </div>
          <h1>Find your <span>opportunity.</span></h1>
          <p>
            Discover internships, hackathons, and open-source programs
            to turn your skills into real experience.
          </p>
        </div>
      </section>

      <section className="opportunities-stats">
        <section className="panel application-dashboard">
            <div className="application-dashboard-header">
                <div>
                <h2>Application tracker</h2>
                <p>Keep track of your opportunity journey.</p>
                </div>

                <div className="application-total">
                <strong>{totalTracked}</strong>
                <span>Tracked</span>
                </div>
            </div>

            <div className="application-dashboard-grid">
                {(
                [
                    ['Interested', applicationCounts.Interested],
                    ['Applied', applicationCounts.Applied],
                    ['Interview', applicationCounts.Interview],
                    ['Selected', applicationCounts.Selected],
                    ['Rejected', applicationCounts.Rejected],
                ] as const
                ).map(([status, count]) => (
                <div className="application-dashboard-card" key={status}>
                    <span>{status}</span>
                    <strong>{count}</strong>
                </div>
                ))}
            </div>
            </section>



        <div className="panel opportunity-stat">
          <BriefcaseBusiness size={21} />
          <strong>{opportunities.length}</strong>
          <span>Sample opportunities</span>
        </div>
        <div className="panel opportunity-stat">
          <Bookmark size={21} />
          <strong>{saved.length}</strong>
          <span>Saved by you</span>
        </div>
        <div className="panel opportunity-stat">
          <Users size={21} />
          <strong>{categories.length - 1}</strong>
          <span>Opportunity types</span>
        </div>
      </section>

      <section className="panel opportunities-browser">
        <div className="opportunities-search">
          <Search size={19} />
          <input
            type="text"
            placeholder="Search roles, organizations, or skills..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <div className="opportunity-filters">
          {categories.map((item) => (
            <button
              key={item}
              className={`opportunity-filter ${
                category === item ? 'opportunity-filter-active' : ''
              }`}
              onClick={() => setCategory(item)}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="opportunities-list">
          {filteredOpportunities.length > 0 ? (
            filteredOpportunities.map((opportunity) => (
              <article className="opportunity-card" key={opportunity.id}>

                {(() => {
                    const {
                        matchedSkills,
                        missingSkills,
                        matchPercentage,
                    } = getOpportunityMatch(opportunity.skills)

                    return (
                        <div className="opportunity-match">
                        <div className="opportunity-match-heading">
                            <strong>{matchPercentage}% skill match</strong>
                            <span>
                            {matchedSkills.length}/{opportunity.skills.length} skills matched
                            </span>
                        </div>

                        <div
                            className="opportunity-match-track"
                            role="progressbar"
                            aria-label="Skill match"
                            aria-valuenow={matchPercentage}
                            aria-valuemin={0}
                            aria-valuemax={100}
                        >
                            <div
                            className="opportunity-match-fill"
                            style={{ width: `${matchPercentage}%` }}
                            />
                        </div>

                        {missingSkills.length > 0 ? (
                            <div className="missing-skills">
                            <strong>Skills to learn:</strong>
                            <div className="opportunity-skills">
                                {missingSkills.map((skill) => (
                                <span key={skill}>{skill}</span>
                                ))}
                            </div>
                            </div>
                        ) : (
                            <p className="all-skills-matched">
                            You have all the listed required skills!
                            </p>
                        )}
                        </div>
                    )
                })()}

                <div className="opportunity-card-top">
                  <div className="opportunity-icon">
                    {opportunity.type === 'Hackathon' ? (
                      <Code2 size={23} />
                    ) : (
                      <BriefcaseBusiness size={23} />
                    )}
                  </div>

                  <button
                    className={`save-opportunity ${
                      saved.includes(opportunity.id) ? 'is-saved' : ''
                    }`}
                    onClick={() => toggleSaved(opportunity.id)}
                    aria-label={
                      saved.includes(opportunity.id)
                        ? 'Remove saved opportunity'
                        : 'Save opportunity'
                    }
                  >
                    <Bookmark size={19} />
                  </button>
                </div>

                <span className="opportunity-type">{opportunity.type}</span>
                <h2>{opportunity.title}</h2>
                <p className="opportunity-organization">
                  {opportunity.organization}
                </p>
                <p className="opportunity-description">
                  {opportunity.description}
                </p>

                <div className="opportunity-skills">
                  {opportunity.skills.map((skill) => (
                    <span key={skill}>{skill}</span>
                  ))}
                </div>
                <div className="application-tracker">
                    <label htmlFor={`application-status-${opportunity.id}`}>
                        Application status
                    </label>

                    <select
                        id={`application-status-${opportunity.id}`}
                        value={applicationStatuses[opportunity.id] ?? 'Interested'}
                        onChange={(event) => {
                        setApplicationStatuses((current) => ({
                            ...current,
                            [opportunity.id]: event.target.value as ApplicationStatus,
                        }))
                        }}
                    >
                        <option value="Interested">Interested</option>
                        <option value="Applied">Applied</option>
                        <option value="Interview">Interview</option>
                        <option value="Rejected">Rejected</option>
                        <option value="Selected">Selected</option>
                    </select>
                    </div>

                <div className="opportunity-meta">
                  <span><Users size={15} /> {opportunity.eligibility}</span>
                  <span><Clock size={15} /> {opportunity.deadline}</span>
                </div>

                <a
                  className="primary-button opportunity-apply"
                  href={opportunity.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Explore opportunity <ExternalLink size={16} />
                </a>
              </article>
            ))
          ) : (
            <div className="opportunities-empty">
              <Search size={25} />
              <h2>No matching opportunities</h2>
              <p>Try another search or select a different category.</p>
              <button
                className="secondary-button"
                onClick={() => {
                  setSearch('')
                  setCategory('All')
                }}
              >
                Clear filters
              </button>
            </div>
          )}
        </div>
      </section>

      <p className="opportunities-note">
        Demo listings only. Verify current openings, eligibility, and deadlines
        on the official websites before applying.
      </p>
    </div>
  )
}
