
import { useState } from 'react'
import { UserRound, Save, Target, BookOpen, Code2 } from 'lucide-react'

export default function ProfilePage() {
  const [name, setName] = useState(
    () => localStorage.getItem('pathpilot-profile-name') ?? '',
  )
  const [education, setEducation] = useState(
    () => localStorage.getItem('pathpilot-profile-education') ?? 'B.Tech',
  )
  const [year, setYear] = useState(
    () => localStorage.getItem('pathpilot-profile-year') ?? '1st Year',
  )
  const [career, setCareer] = useState(
    () => localStorage.getItem('pathpilot-profile-career') ?? 'Software Developer',
  )
  const [skills, setSkills] = useState(
    () => localStorage.getItem('pathpilot-profile-skills') ?? '',
  )
  const [interests, setInterests] = useState(
    () => localStorage.getItem('pathpilot-profile-interests') ?? '',
  )
  const [hours, setHours] = useState(
    () => localStorage.getItem('pathpilot-profile-hours') ?? '4–8 hours',
  )
  const [saved, setSaved] = useState(false)

  function saveProfile() {
    localStorage.setItem('pathpilot-profile-name', name)
    localStorage.setItem('pathpilot-profile-education', education)
    localStorage.setItem('pathpilot-profile-year', year)
    localStorage.setItem('pathpilot-profile-career', career)
    localStorage.setItem('pathpilot-profile-skills', skills)
    localStorage.setItem('pathpilot-profile-interests', interests)
    localStorage.setItem('pathpilot-profile-hours', hours)
    localStorage.setItem('pathpilot-selected-career', career === 'Data Analyst' ? 'data' : career === 'UI/UX Designer' ? 'design' : career === 'AI / ML Engineer' ? 'ai' : 'software')
    setSaved(true)
  }

  return (
    <main className="roadmap-page">
      <header className="roadmap-header">
        <div>
          <p className="roadmap-eyebrow">YOUR PROFILE</p>
          <h1>Get to know you</h1>
          <p className="roadmap-muted">
            Your profile helps PathPilot personalize your learning journey.
          </p>
        </div>
        <div className="roadmap-header-icon">
          <UserRound size={23} />
        </div>
      </header>

      <section className="roadmap-settings" style={{ display: 'block' }}>
        <h2><UserRound size={18} /> Personal information</h2>
        <label>
          <span>Your name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter your name" />
        </label>
        <label>
          <span>Education</span>
          <select value={education} onChange={(e) => setEducation(e.target.value)}>
            <option>B.Tech</option>
            <option>B.E.</option>
            <option>B.Sc.</option>
            <option>BCA</option>
            <option>Other</option>
          </select>
        </label>
        <label>
          <span>Current year</span>
          <select value={year} onChange={(e) => setYear(e.target.value)}>
            <option>1st Year</option>
            <option>2nd Year</option>
            <option>3rd Year</option>
            <option>4th Year</option>
            <option>Graduate</option>
          </select>
        </label>
      </section>

      <section className="roadmap-settings" style={{ display: 'block' }}>
        <h2><Target size={18} /> Career goals</h2>
        <label>
          <span>Target career</span>
          <select value={career} onChange={(e) => setCareer(e.target.value)}>
            <option>Software Developer</option>
            <option>Frontend Developer</option>
            <option>Data Analyst</option>
            <option>UI/UX Designer</option>
            <option>AI / ML Engineer</option>
            <option>Product Manager</option>
          </select>
        </label>
        <label>
          <span>Study time each week</span>
          <select value={hours} onChange={(e) => setHours(e.target.value)}>
            <option>1–3 hours</option>
            <option>4–8 hours</option>
            <option>9–15 hours</option>
            <option>15+ hours</option>
          </select>
        </label>
      </section>

      <section className="roadmap-settings" style={{ display: 'block' }}>
        <h2><Code2 size={18} /> Skills and interests</h2>
        <label>
          <span>Current skills</span>
          <textarea value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="e.g. Python, HTML, React" rows={3} />
        </label>
        <label>
          <span>Interests</span>
          <textarea value={interests} onChange={(e) => setInterests(e.target.value)} placeholder="e.g. building apps, data, AI" rows={3} />
        </label>
      </section>

      <button className="roadmap-primary-button" onClick={saveProfile}>
        <Save size={16} /> Save profile
      </button>

      {saved && (
        <p className="roadmap-muted" role="status">
          Profile saved successfully.
        </p>
      )}

      <p className="roadmap-muted">
        <BookOpen size={15} /> Your profile is currently saved in this browser.
      </p>
    </main>
  )
}
