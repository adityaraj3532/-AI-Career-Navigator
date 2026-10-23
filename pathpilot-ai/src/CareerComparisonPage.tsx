
import { useState } from 'react'
import {
  ArrowRight,
  Check,
  Clock,
  Code2,
  Database,
  Palette,
  Brain,
  Target,
  Wallet,
  BriefcaseBusiness,
  ChevronDown,
} from 'lucide-react'

type Career = {
  id: string
  title: string
  description: string
  icon: typeof Code2
  skills: string[]
  months: string
  budget: string
  projects: string
  workStyle: string
  demand: string
  match: string[]
}

const careers: Career[] = [
  {
    id: 'software',
    title: 'Software Developer',
    description: 'Build applications, websites, and software products.',
    icon: Code2,
    skills: ['Programming', 'Data structures', 'Git & GitHub', 'APIs'],
    months: '6–12 months',
    budget: '₹0–₹5,000',
    projects: '2–3 working projects',
    workStyle: 'Building & problem-solving',
    demand: 'Varies by skills, location, and experience',
    match: ['logic', 'building', 'technology'],
  },
  {
    id: 'data',
    title: 'Data Analyst',
    description: 'Turn data into useful insights for better decisions.',
    icon: Database,
    skills: ['Excel', 'SQL', 'Statistics', 'Power BI'],
    months: '4–8 months',
    budget: '₹0–₹4,000',
    projects: '2 analysis case studies',
    workStyle: 'Research & analytical thinking',
    demand: 'Varies by industry and experience',
    match: ['analysis', 'numbers', 'research'],
  },
  {
    id: 'design',
    title: 'UI/UX Designer',
    description: 'Design digital products that are clear and easy to use.',
    icon: Palette,
    skills: ['Figma', 'Wireframing', 'User research', 'Prototyping'],
    months: '3–6 months',
    budget: '₹0–₹3,000',
    projects: '2–3 portfolio case studies',
    workStyle: 'Creativity & user empathy',
    demand: 'Varies by portfolio, industry, and experience',
    match: ['design', 'creativity', 'people'],
  },
  {
    id: 'ai',
    title: 'AI / ML Engineer',
    description: 'Build applications that use machine learning and AI.',
    icon: Brain,
    skills: ['Python', 'Statistics', 'Machine learning', 'Data handling'],
    months: '8–18 months',
    budget: '₹0–₹8,000',
    projects: '2–3 evaluated ML projects',
    workStyle: 'Experimentation & technical problem-solving',
    demand: 'Varies by role, fundamentals, and experience',
    match: ['ai', 'math', 'technology', 'research'],
  },
  {
    id: 'product',
    title: 'Product Manager',
    description: 'Help teams identify user needs and build the right products.',
    icon: Target,
    skills: ['Communication', 'User research', 'Prioritization', 'Analytics'],
    months: '4–9 months to build foundations',
    budget: '₹0–₹4,000',
    projects: '2 product case studies',
    workStyle: 'Planning & cross-team collaboration',
    demand: 'Varies by company and prior experience',
    match: ['people', 'planning', 'business'],
  },
]

const interests = [
  { id: 'technology', label: 'Technology & coding' },
  { id: 'analysis', label: 'Data & analysis' },
  { id: 'design', label: 'Design & creativity' },
  { id: 'people', label: 'People & teamwork' },
  { id: 'ai', label: 'AI & experimentation' },
  { id: 'building', label: 'Building useful things' },
]

export default function CareerComparisonPage() {
  const [selected, setSelected] = useState<string[]>(['software', 'data'])
  const [interest, setInterest] = useState('technology')
  const [hours, setHours] = useState('8')
  const [budget, setBudget] = useState('low')
  const [showDetails, setShowDetails] = useState(false)
  const [chosenCareer, setChosenCareer] = useState<string | null>(null)

  const compared = careers.filter((career) => selected.includes(career.id))

  const affordable = (career: Career) => {
    if (budget === 'low') return career.id !== 'ai'
    if (budget === 'medium') return true
    return true
  }

  const ranked = [...careers].sort((a, b) => {
    const score = (career: Career) =>
      (career.match.includes(interest) ? 3 : 0) +
      (affordable(career) ? 1 : 0)
    return score(b) - score(a)
  })

  const recommendation = ranked[0]

  function toggleCareer(id: string) {
    setSelected((previous) => {
      if (previous.includes(id)) return previous.filter((item) => item !== id)
      if (previous.length >= 3) return previous
      return [...previous, id]
    })
  }

  return (
    <main className="comparison-page">
      <header className="comparison-header">
        <div>
          <p className="comparison-eyebrow">CAREER DISCOVERY</p>
          <h1>Compare your career paths</h1>
          <p className="comparison-subtitle">
            Explore your options before deciding what to learn next.
          </p>
        </div>
        <div className="comparison-header-icon"><BriefcaseBusiness size={23} /></div>
      </header>

      <section className="comparison-picker">
        <div className="comparison-section-heading">
          <div>
            <h2>Which careers interest you?</h2>
            <p>Choose up to 3 paths to compare side by side.</p>
          </div>
          <span className="comparison-count">{selected.length}/3 selected</span>
        </div>

        <div className="comparison-career-picker">
          {careers.map((career) => {
            const Icon = career.icon
            const isSelected = selected.includes(career.id)
            const disabled = selected.length >= 3 && !isSelected
            return (
              <button
                key={career.id}
                className={`comparison-career-option ${isSelected ? 'is-selected' : ''}`}
                onClick={() => toggleCareer(career.id)}
                disabled={disabled}
              >
                <span className="comparison-career-icon"><Icon size={20} /></span>
                <span className="comparison-career-copy">
                  <strong>{career.title}</strong>
                  <small>{career.description}</small>
                </span>
                <span className="comparison-check">
                  {isSelected && <Check size={15} />}
                </span>
              </button>
            )
          })}
        </div>
      </section>

      <section className="comparison-preferences">
        <div className="comparison-section-heading">
          <div>
            <h2>Make it personal</h2>
            <p>Tell us a little about your situation.</p>
          </div>
        </div>

        <div className="comparison-preference-grid">
          <label className="comparison-field">
            <span><Target size={15} /> Main interest</span>
            <select value={interest} onChange={(e) => setInterest(e.target.value)}>
              {interests.map((item) => (
                <option value={item.id} key={item.id}>{item.label}</option>
              ))}
            </select>
          </label>

          <label className="comparison-field">
            <span><Clock size={15} /> Learning time per week</span>
            <select value={hours} onChange={(e) => setHours(e.target.value)}>
              <option value="3">1–3 hours</option>
              <option value="8">4–8 hours</option>
              <option value="15">9–15 hours</option>
              <option value="20">15+ hours</option>
            </select>
          </label>

          <label className="comparison-field">
            <span><Wallet size={15} /> Learning budget</span>
            <select value={budget} onChange={(e) => setBudget(e.target.value)}>
              <option value="low">Free / under ₹1,000</option>
              <option value="medium">₹1,000–₹5,000</option>
              <option value="high">₹5,000+</option>
            </select>
          </label>
        </div>

        <button
          className="comparison-details-toggle"
          onClick={() => setShowDetails((value) => !value)}
        >
          {showDetails ? 'Hide comparison details' : 'What should I compare?'}
          <ChevronDown size={16} className={showDetails ? 'rotated' : ''} />
        </button>
        {showDetails && (
          <p className="comparison-explanation">
            We compare the skills to learn, time to build foundations, likely
            learning expenses, project expectations, work style, and your stated
            interests. Time and cost are illustrative estimates, not guarantees.
          </p>
        )}
      </section>

      <section className="comparison-results">
        <div className="comparison-section-heading">
          <div>
            <h2>Your comparison</h2>
            <p>Use these estimates to plan, not as a promise of employment.</p>
          </div>
        </div>

        {compared.length === 0 ? (
          <div className="comparison-empty">
            Select at least one career above to see its details.
          </div>
        ) : (
          <div className="comparison-table-wrap">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>What to compare</th>
                  {compared.map((career) => <th key={career.id}>{career.title}</th>)}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Preparation estimate</td>
                  {compared.map((career) => <td key={career.id}>{career.months}</td>)}
                </tr>
                <tr>
                  <td>Learning budget</td>
                  {compared.map((career) => <td key={career.id}>{career.budget}</td>)}
                </tr>
                <tr>
                  <td>Portfolio evidence</td>
                  {compared.map((career) => <td key={career.id}>{career.projects}</td>)}
                </tr>
                <tr>
                  <td>Work style</td>
                  {compared.map((career) => <td key={career.id}>{career.workStyle}</td>)}
                </tr>
                <tr>
                  <td>Skills to build</td>
                  {compared.map((career) => (
                    <td key={career.id}>
                      <div className="comparison-skill-list">
                        {career.skills.map((skill) => <span key={skill}>{skill}</span>)}
                      </div>
                    </td>
                  ))}
                </tr>
                <tr>
                  <td>Job opportunities</td>
                  {compared.map((career) => <td key={career.id}>{career.demand}</td>)}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="comparison-recommendation">
        <div className="comparison-recommendation-icon"><SparklesIcon /></div>
        <div className="comparison-recommendation-copy">
          <p className="comparison-eyebrow">A STARTING POINT FOR YOU</p>
          <h2>Explore {recommendation.title}</h2>
          <p>
            This path is suggested because it relates to your selected interest:
            {' '}{interests.find((item) => item.id === interest)?.label.toLowerCase()}.
            With {hours} hours available per week, start with one small project
            before committing to an expensive course.
          </p>
          <small>This is a simple interest-based suggestion, not an AI assessment or hiring prediction.</small>
        </div>
        <button
          className="comparison-continue"
          onClick={() => {
            setChosenCareer(recommendation.id)
            window.dispatchEvent(
              new CustomEvent('pathpilot-career-selected', {
                detail: recommendation.id,
              })
            )
          }}
        >
          Explore roadmap <ArrowRight size={16} />
        </button>
      </section>

      {chosenCareer && (
        <p className="comparison-confirmation">
          Your choice is {careers.find((career) => career.id === chosenCareer)?.title}.
          The roadmap page will be connected in the next step.
        </p>
      )}
    </main>
  )
}

function SparklesIcon() {
  return <Brain size={22} />
}
