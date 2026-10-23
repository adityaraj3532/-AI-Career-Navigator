
import OpportunitiesPage from './OpportunitiesPage'
import AssessmentsPage from './AssessmentsPage'
import AssessmentPage from './AssessmentPage'
import ProjectsPage from './ProjectsPage'
import LearnPage from './LearnPage'
import ProfilePage from './ProfilePage'
import ProgressPage from './ProgressPage'
import CareerRoadmapPage from './CareerRoadmapPage'
import CareerComparisonPage from './CareerComparisonPage'
import { useEffect, useState } from 'react'
import {
  Compass, Home, Map, BriefcaseBusiness, FolderKanban,
  ClipboardCheck, UserRound, ArrowRight, Clock, Sparkles,
  CheckCircle2, Menu, X, Brain,Target
} from 'lucide-react'

import './App.css'

type NavigationItem = {
  name: string
  icon: typeof Home
}

const tasks = [
  { title: 'Learn REST API fundamentals', time: '25 min', done: true },
  { title: 'Build your first API endpoint', time: '45 min', done: false },
  { title: 'Test your endpoint', time: '20 min', done: false },
]



const navigation: NavigationItem[]= [
  
  { name: 'Profile', icon: UserRound },
  { name: 'Home', icon: Home },
  { name: 'Career Assessment', icon: Brain },
  { name: 'Career Comparison', icon: BriefcaseBusiness },
  { name: 'My Roadmap', icon: Map },
  { name: 'Progress & Job Readiness', icon: Target },
  { name: 'Learn', icon: Compass },
  { name: 'Projects', icon: FolderKanban },
  { name: 'Assessments', icon: ClipboardCheck },
  { name: 'Opportunities', icon: BriefcaseBusiness },
]

export default function App() {
  const [active, setActive] = useState('Home')
  const [completed, setCompleted] = useState<number[]>([0])
  const [menuOpen, setMenuOpen] = useState(false)

  
  useEffect(() => {
    const handleCareerSelected = (event: Event) => {
      const careerId = (event as CustomEvent<string>).detail

      if (careerId) {
        localStorage.setItem('pathpilot-selected-career', careerId)
      }

      setActive('My Roadmap')
    }

    window.addEventListener(
      'pathpilot-career-selected',
      handleCareerSelected
    )

    return () => {
      window.removeEventListener(
        'pathpilot-career-selected',
        handleCareerSelected
      )
    }
  }, [])



  const progress = Math.round((completed.length / tasks.length) * 100)

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-icon"><Compass size={23} /></div>
          <span>pathpilot<span className="brand-dot">.</span></span>
          <button className="mobile-close" onClick={() => setMenuOpen(false)}><X /></button>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {navigation.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={`nav-item ${active === name ? 'nav-active' : ''}`}
              onClick={() => { setActive(name); setMenuOpen(false) }}
            >
              <Icon size={19} />
              <span>{name}</span>
              {name === 'My Roadmap' && <span className="nav-count">3</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="help-card">
            <Sparkles size={20} />
            <strong>Small steps. Big future.</strong>
            <p>Your career journey, made simpler.</p>
          </div>
          <button className={`nav-item ${active === 'Profile' ? 'nav-active' : ''}`} onClick={() => setActive('Profile')}>
            <UserRound size={19} /><span>My Profile</span>
          </button>
          <div className="user-row">
            <div className="avatar">S</div>
            <div><strong>Student</strong><small>Career explorer</small></div>
          </div>
        </div>
      </aside>

      {menuOpen && <button className="mobile-overlay" onClick={() => setMenuOpen(false)} aria-label="Close menu" />}

      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu /></button>
          <div className="breadcrumb">Workspace <span>/</span> {active}</div>
          <div className="topbar-right">
            <span className="status-dot" /> <span className="status-text">Your journey starts here</span>
            <div className="avatar">S</div>
          </div>
        </header>

       
            {active === 'Progress & Job Readiness' ?(
              <ProgressPage />            
            ) :active === 'My Roadmap' ? (
              <CareerRoadmapPage />
            ) : active === 'Career Comparison' ? (
              <CareerComparisonPage />
            ) : active === 'Career Assessment' ? (
              <AssessmentPage />
            ) : active === 'Profile' ? (
              <ProfilePage />
            ) : active === 'Learn' ? (
              <LearnPage />
            ) : active === 'Projects' ? (
              <ProjectsPage />
            ) : active === 'Assessments' ? (
              <AssessmentsPage />
            ) : active === 'Opportunities' ? (
              <OpportunitiesPage />
            ) : active === 'Home' ? (
          <div className="page-content">
            <section className="welcome">
              <div>
                <div className="eyebrow"><Sparkles size={15} /> YOUR PERSONAL CAREER SPACE</div>
                <h1>Your future,<br /><span>one step at a time.</span></h1>
                <p>Build skills, create projects, and prepare for the opportunities you want.</p>
                <button className="primary-button" onClick={() => setActive('My Roadmap')}>
                  Explore my roadmap <ArrowRight size={17} />
                </button>
              </div>
              <div className="welcome-art">
                <div className="art-orbit orbit-one" />
                <div className="art-orbit orbit-two" />
                <div className="art-core"><Compass size={65} strokeWidth={1.3} /></div>
                <div className="floating-chip chip-one"><Sparkles size={16} /> Find your direction</div>
                <div className="floating-chip chip-two"><CheckCircle2 size={16} /> Build real skills</div>
              </div>
            </section>

            <section className="section-heading">
              <div><h2>Your workspace</h2><p>Everything you need, without the overwhelm.</p></div>
            </section>

            <section className="quick-grid">
              <button className="quick-card" onClick={() => setActive('My Roadmap')}>
                <div className="quick-icon purple"><Map /></div>
                <strong>My Roadmap</strong><p>Know what to learn next.</p><ArrowRight className="quick-arrow" size={18} />
              </button>
              <button className="quick-card" onClick={() => setActive('Projects')}>
                <div className="quick-icon peach"><FolderKanban /></div>
                <strong>Projects</strong><p>Turn skills into real work.</p><ArrowRight className="quick-arrow" size={18} />
              </button>
              <button className="quick-card" onClick={() => setActive('Assessments')}>
                <div className="quick-icon mint"><ClipboardCheck /></div>
                <strong>Skill check</strong><p>See what you already know.</p><ArrowRight className="quick-arrow" size={18} />
              </button>
              <button className="quick-card" onClick={() => setActive('Opportunities')}>
                <div className="quick-icon blue"><BriefcaseBusiness /></div>
                <strong>Opportunities</strong><p>Explore your next opening.</p><ArrowRight className="quick-arrow" size={18} />
              </button>
            </section>

            <section className="bottom-grid">
              <div className="panel next-panel">
                <div className="panel-heading"><div><span className="panel-kicker">PICK UP WHERE YOU LEFT OFF</span><h2>Your next steps</h2></div><span className="task-count">{completed.length}/{tasks.length}</span></div>
                <div className="task-list">
                  {tasks.map((task, index) => (
                    <label key={task.title} className={`task-row ${completed.includes(index) ? 'task-done' : ''}`}>
                      <input type="checkbox" checked={completed.includes(index)} onChange={() => setCompleted(old => old.includes(index) ? old.filter(n => n !== index) : [...old, index])} />
                      <span className="custom-check"><CheckCircle2 size={18} /></span>
                      <span className="task-name">{task.title}</span>
                      <span className="task-time"><Clock size={13} />{task.time}</span>
                    </label>
                  ))}
                </div>
                <button className="text-button" onClick={() => setActive('My Roadmap')}>View full roadmap <ArrowRight size={16} /></button>
              </div>

              <div className="panel progress-panel">
                <span className="panel-kicker">YOUR MOMENTUM</span>
                <h2>Every step counts.</h2>
                <div className="progress-ring" style={{ '--progress': `${progress}%` } as React.CSSProperties}>
                  <div className="progress-inner"><strong>{progress}%</strong><span>completed</span></div>
                </div>
                <p>{completed.length === tasks.length ? 'Great work! You finished all your sample tasks.' : 'Keep going. Small, consistent steps add up.'}</p>
                <button className="secondary-button" onClick={() => setActive('My Roadmap')}>Continue learning <ArrowRight size={16} /></button>
              </div>
            </section>
            <footer>Made for your next chapter <span>✳</span> PathPilot AI</footer>
          </div>
        ) : (
          <div className="simple-page">
            <div className="eyebrow"><Sparkles size={15} /> YOUR CAREER JOURNEY</div>
            <h1>{active}</h1>
            <p className="simple-description">
              {active === 'My Roadmap' && 'Your learning plan, broken into simple, achievable steps.'}
              {active === 'Learn' && 'Find learning resources that match your career goal.'}
              {active === 'Projects' && 'Build practical projects that demonstrate your skills.'}
              {active === 'Assessments' && 'Check your skills and discover what to practice next.'}
              {active === 'Opportunities' && 'Explore internships and entry-level roles that fit your goals.'}
              {active === 'Profile' && 'Your skills, interests, goals, and available time.'}
            </p>
            <div className="panel placeholder-panel">
              <div className="quick-icon purple"><Compass size={25} /></div>
              <h2>{active === 'Profile' ? 'Your journey, your goals.' : `Let's build your ${active.toLowerCase()}.`}</h2>
              <p>This section is ready for us to build next. We'll keep it focused on one task at a time.</p>
              <button className="primary-button" onClick={() => setActive('Home')}>Back to home <ArrowRight size={17} /></button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
