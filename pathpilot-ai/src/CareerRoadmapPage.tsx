import { useEffect, useState } from 'react'
import { Check, ChevronDown, Clock3, ExternalLink, PartyPopper, RotateCcw } from 'lucide-react'
import { roadmaps, taskHours, type RoadmapCareerId } from './roadmapData'

const CAREER_KEY = 'pathpilot-selected-career'
const HOURS_KEY = 'pathpilot-weekly-hours'
const progressKey = (career: string) => `pathpilot-roadmap-progress-${career}`

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function initialCareer(): RoadmapCareerId {
  try {
    const saved = localStorage.getItem(CAREER_KEY)
    if (saved && saved in roadmaps) return saved as RoadmapCareerId
  } catch { /* ignore */ }
  return 'software'
}

export default function CareerRoadmapPage() {
  const [career, setCareer] = useState<RoadmapCareerId>(initialCareer)
  const [hours, setHours] = useState(() => readJson(HOURS_KEY, '8'))
  const [completed, setCompleted] = useState<number[]>(() => readJson(progressKey(initialCareer()), []))
  const [openId, setOpenId] = useState<number | null>(null)

  const roadmap = roadmaps[career]
  const steps = roadmap.tasks
  const currentStep = steps.find((step) => !completed.includes(step.id))
  // The open step defaults to the current one, so the user always sees what to do next.
  const expandedId = openId ?? currentStep?.id ?? null

  useEffect(() => {
    try { localStorage.setItem(progressKey(career), JSON.stringify(completed)) } catch { /* ignore */ }
  }, [career, completed])
  useEffect(() => {
    try { localStorage.setItem(HOURS_KEY, JSON.stringify(hours)) } catch { /* ignore */ }
  }, [hours])

  const progress = Math.round((completed.length / steps.length) * 100)
  const hoursLeft = steps
    .filter((step) => !completed.includes(step.id))
    .reduce((sum, step) => sum + taskHours(step.duration), 0)
  const weeksLeft = Math.ceil(hoursLeft / Number(hours))

  function changeCareer(value: RoadmapCareerId) {
    setCareer(value)
    try { localStorage.setItem(CAREER_KEY, value) } catch { /* ignore */ }
    setCompleted(readJson<number[]>(progressKey(value), []))
    setOpenId(null)
  }

  function markDone(id: number) {
    setCompleted((previous) => [...previous, id])
    setOpenId(null) // jump to the next step automatically
  }

  function undo(id: number) {
    setCompleted((previous) => previous.filter((stepId) => stepId !== id))
    setOpenId(id)
  }

  function startOver() {
    if (window.confirm(`Start the ${roadmap.title} roadmap over?`)) {
      setCompleted([])
      setOpenId(null)
    }
  }

  return (
    <main className="rm-page">
      <header className="rm-header">
        <p className="rm-eyebrow">MY ROADMAP</p>
        <h1>
          Become a{' '}
          <select
            className="rm-career-select"
            value={career}
            onChange={(event) => changeCareer(event.target.value as RoadmapCareerId)}
            aria-label="Target career"
          >
            {(Object.keys(roadmaps) as RoadmapCareerId[]).map((id) => (
              <option key={id} value={id}>{roadmaps[id].title}</option>
            ))}
          </select>
        </h1>
        <p className="rm-muted">{steps.length} steps. Do them in order and tick each one off when you finish.</p>
      </header>

      <section className="rm-progress">
        <div className="rm-progress-row">
          <strong>Step {Math.min(completed.length + 1, steps.length)} of {steps.length}</strong>
          <span>{progress}% done</span>
        </div>
        <div className="rm-bar"><div style={{ width: `${progress}%` }} /></div>
        <div className="rm-progress-row rm-small">
          {currentStep ? (
            <span>
              About {weeksLeft} week{weeksLeft === 1 ? '' : 's'} left if you study{' '}
              <select value={hours} onChange={(event) => setHours(event.target.value)} aria-label="Hours per week">
                <option value="3">3 hrs</option>
                <option value="8">8 hrs</option>
                <option value="15">15 hrs</option>
                <option value="20">20 hrs</option>
              </select>{' '}
              a week
            </span>
          ) : <span>All steps finished</span>}
          {completed.length > 0 && (
            <button type="button" className="rm-link" onClick={startOver}><RotateCcw size={13} /> Start over</button>
          )}
        </div>
      </section>

      {!currentStep && (
        <section className="rm-finished">
          <PartyPopper size={28} />
          <h2>You finished the {roadmap.title} roadmap!</h2>
          <p>Add your projects to your portfolio and start applying in Opportunities.</p>
        </section>
      )}

      <ol className="rm-steps">
        {steps.map((step, index) => {
          const done = completed.includes(step.id)
          const isCurrent = step.id === currentStep?.id
          const isOpen = step.id === expandedId

          return (
            <li key={step.id} className={`rm-step ${done ? 'is-done' : ''} ${isCurrent ? 'is-current' : ''}`}>
              <span className="rm-dot">{done ? <Check size={15} /> : index + 1}</span>

              <div className="rm-card">
                <button
                  type="button"
                  className="rm-card-head"
                  onClick={() => setOpenId(isOpen ? -1 : step.id)}
                  aria-expanded={isOpen}
                >
                  <span>
                    {isCurrent && <em className="rm-badge">Do this next</em>}
                    <strong>{step.title}</strong>
                    <small><Clock3 size={13} /> {step.duration}</small>
                  </span>
                  <ChevronDown size={18} className={isOpen ? 'rm-rotate' : ''} />
                </button>

                {isOpen && (
                  <div className="rm-card-body">
                    <p>{step.description}</p>

                    <h3>What to do</h3>
                    <ol>
                      {step.instructions.map((item) => <li key={item}>{item}</li>)}
                    </ol>

                    <h3>You're done when</h3>
                    <ul className="rm-checks">
                      {step.criteria.map((item) => <li key={item}>{item}</li>)}
                    </ul>

                    {step.project && <p className="rm-project"><strong>Build:</strong> {step.project}</p>}

                    <div className="rm-actions">
                      <a href={step.resourceUrl} target="_blank" rel="noreferrer" className="rm-secondary">
                        Open lesson: {step.resource} <ExternalLink size={14} />
                      </a>
                      {done ? (
                        <button type="button" className="rm-link" onClick={() => undo(step.id)}>Mark as not done</button>
                      ) : (
                        <button type="button" className="rm-primary" onClick={() => markDone(step.id)}>
                          <Check size={16} /> I finished this step
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </main>
  )
}
