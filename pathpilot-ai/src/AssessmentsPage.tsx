
import { useState } from 'react'
import {
  ArrowLeft, ArrowRight, Brain, CheckCircle2,
  Code2, Database, Palette, Sparkles, Target,
  RotateCcw
} from 'lucide-react'

type CareerId = 'software' | 'data' | 'design' | 'ai' | 'product'

type Option = {
  label: string
  detail: string
  scores: Partial<Record<CareerId, number>>
}

type Question = {
  title: string
  subtitle: string
  options: Option[]
}

const careers: {
  id: CareerId
  title: string
  description: string
  strengths: string
  skills: string[]
  icon: typeof Code2
}[] = [
  {
    id: 'software',
    title: 'Software Developer',
    description: 'Build websites, applications, and tools that solve real problems.',
    strengths: 'Logical thinking, building things, and solving technical problems.',
    skills: ['Programming', 'Problem solving', 'Git & GitHub'],
    icon: Code2,
  },
  {
    id: 'data',
    title: 'Data Analyst',
    description: 'Explore data, discover patterns, and help people make decisions.',
    strengths: 'Analytical thinking, curiosity, and finding patterns.',
    skills: ['SQL', 'Spreadsheets', 'Data visualization'],
    icon: Database,
  },
  {
    id: 'design',
    title: 'UI/UX Designer',
    description: 'Design useful, clear, and enjoyable digital experiences.',
    strengths: 'Creativity, empathy, and improving how things work.',
    skills: ['Design fundamentals', 'Figma', 'User research'],
    icon: Palette,
  },
  {
    id: 'ai',
    title: 'AI / Machine Learning',
    description: 'Build intelligent applications and experiment with data and models.',
    strengths: 'Curiosity, experimentation, mathematics, and problem solving.',
    skills: ['Python', 'Statistics', 'Machine learning'],
    icon: Brain,
  },
  {
    id: 'product',
    title: 'Product Management',
    description: 'Understand user problems and help teams build the right solutions.',
    strengths: 'Communication, planning, teamwork, and decision making.',
    skills: ['User research', 'Prioritization', 'Communication'],
    icon: Target,
  },
]

const questions: Question[] = [
  {
    title: 'What kind of activity sounds most interesting?',
    subtitle: 'Choose the activity you would enjoy trying.',
    options: [
      { label: 'Building an app or website', detail: 'Create something people can use', scores: { software: 3, ai: 1 } },
      { label: 'Finding patterns in information', detail: 'Explore numbers and discover insights', scores: { data: 3, ai: 2 } },
      { label: 'Designing a beautiful interface', detail: 'Make a product easier to use', scores: { design: 3, product: 1 } },
      { label: 'Solving a real user problem', detail: 'Understand needs and plan a solution', scores: { product: 3, design: 1 } },
    ],
  },
  {
    title: 'Which challenge would you choose?',
    subtitle: 'There is no right or wrong answer.',
    options: [
      { label: 'Debug a tricky coding problem', detail: 'Find why a program is not working', scores: { software: 3, ai: 1 } },
      { label: 'Explain what a dataset reveals', detail: 'Turn information into a useful conclusion', scores: { data: 3, ai: 1 } },
      { label: 'Improve a confusing app screen', detail: 'Make it simpler and clearer', scores: { design: 3, product: 1 } },
      { label: 'Decide which feature to build first', detail: 'Balance user needs and priorities', scores: { product: 3, software: 1 } },
    ],
  },
  {
    title: 'What would you like to learn first?',
    subtitle: 'Pick the topic you are most curious about.',
    options: [
      { label: 'Programming and app development', detail: 'Write code and build projects', scores: { software: 3 } },
      { label: 'SQL, statistics, and data', detail: 'Work with information and evidence', scores: { data: 3, ai: 1 } },
      { label: 'Visual design and user experience', detail: 'Create clear digital experiences', scores: { design: 3 } },
      { label: 'AI tools and intelligent systems', detail: 'Explore how AI applications work', scores: { ai: 3, software: 1 } },
    ],
  },
  {
    title: 'How do you prefer to solve problems?',
    subtitle: 'Think about what feels natural or enjoyable.',
    options: [
      { label: 'Break the problem into logical steps', detail: 'Work through it systematically', scores: { software: 2, ai: 1, data: 1 } },
      { label: 'Look for patterns and evidence', detail: 'Use information to reach a conclusion', scores: { data: 3, ai: 1 } },
      { label: 'Sketch ideas and try different layouts', detail: 'Explore visual possibilities', scores: { design: 3 } },
      { label: 'Discuss the problem and organize a plan', detail: 'Bring people and ideas together', scores: { product: 3 } },
    ],
  },
  {
    title: 'Which result would make you proud?',
    subtitle: 'Imagine finishing a personal project.',
    options: [
      { label: 'A working app people can use', detail: 'Something functional from start to finish', scores: { software: 3 } },
      { label: 'A report that reveals an insight', detail: 'A discovery backed by data', scores: { data: 3 } },
      { label: 'A design people find easy to use', detail: 'A thoughtful, polished experience', scores: { design: 3 } },
      { label: 'A smart tool that automates a task', detail: 'A useful application powered by AI', scores: { ai: 3, software: 1 } },
    ],
  },
  {
    title: 'Which work style appeals to you?',
    subtitle: 'Most careers include a mix of these activities.',
    options: [
      { label: 'Focused individual problem solving', detail: 'Spend time building and improving', scores: { software: 2, ai: 1, data: 1 } },
      { label: 'Research and careful investigation', detail: 'Explore evidence before deciding', scores: { data: 2, ai: 2 } },
      { label: 'Creative iteration and feedback', detail: 'Try ideas and improve them', scores: { design: 3 } },
      { label: 'Collaborating and coordinating', detail: 'Help a team move toward a goal', scores: { product: 3 } },
    ],
  },
  {
    title: 'Which subject or activity do you enjoy most?',
    subtitle: 'Choose based on your interest, not your grades.',
    options: [
      { label: 'Logic, mathematics, or programming', detail: 'Rules, systems, and problem solving', scores: { software: 2, ai: 2 } },
      { label: 'Numbers, research, and interpretation', detail: 'Understand what the evidence means', scores: { data: 3, ai: 1 } },
      { label: 'Art, visuals, and human behavior', detail: 'How people see and use things', scores: { design: 3 } },
      { label: 'Business, teamwork, and planning', detail: 'People, goals, and decisions', scores: { product: 3 } },
    ],
  },
  {
    title: 'What would you like your work to improve?',
    subtitle: 'Think about the impact you want to make.',
    options: [
      { label: 'Make technology work better', detail: 'Reliable, useful software', scores: { software: 3 } },
      { label: 'Help people make better decisions', detail: 'Clear insights from data', scores: { data: 3 } },
      { label: 'Make technology easier for people', detail: 'Simple and accessible experiences', scores: { design: 3 } },
      { label: 'Find new ways to solve hard problems', detail: 'Experiment with intelligent tools', scores: { ai: 3, product: 1 } },
    ],
  },
]

export default function AssessmentPage() {
  const [answers, setAnswers] = useState<number[]>([])
  const [finished, setFinished] = useState(false)
  const [selectedCareer, setSelectedCareer] = useState<CareerId | null>(null)

  const currentQuestion = questions[answers.length]
  const progress = Math.round((answers.length / questions.length) * 100)

  const scores = careers.map((career) => {
  const score = questions.reduce((total, question, index) => {
    const option = question.options[answers[index]]
    return total + (option?.scores[career.id] ?? 0)
  }, 0)

  const maxScore = questions.reduce((total, question) => {
    const highestQuestionScore = Math.max(
      ...question.options.map(
        (option) => option.scores[career.id] ?? 0
      )
    )

    return total + highestQuestionScore
  }, 0)

  const matchPercentage =
    maxScore === 0 ? 0 : Math.round((score / maxScore) * 100)

  return {
    ...career,
    score,
    matchPercentage,
  }
}).sort((a, b) => b.matchPercentage - a.matchPercentage)

function chooseAnswer(index: number) {
  const updatedAnswers = [...answers, index]
  setAnswers(updatedAnswers)

  if (updatedAnswers.length === questions.length) {
    setFinished(true)
  }
}
 
 
  function goBack() {
    if (finished) {
      setFinished(false)
      setSelectedCareer(null)
      return
    }
    setAnswers((previous) => previous.slice(0, -1))
  }

  function restart() {
    setAnswers([])
    setFinished(false)
    setSelectedCareer(null)
  }

  if (finished) {
    return (
      <div className="assessment-page">
        <div className="assessment-top">
          <div className="assessment-brand"><span><Sparkles size={19} /></span> Your career suggestions</div>
          <button className="assessment-quiet-button" onClick={restart}><RotateCcw size={15} /> Retake</button>
        </div>

        <section className="assessment-results">
          <div className="assessment-result-intro">
            <div className="assessment-success-icon"><CheckCircle2 size={28} /></div>
            <p className="assessment-eyebrow">ASSESSMENT COMPLETE</p>
            <h1>Explore what could fit you.</h1>
            <p>Based on your interests and preferences, here are three career paths worth exploring.</p>
          </div>

          <div className="career-results">
            {scores.slice(0, 3).map((career, index) => {
              const Icon = career.icon
              const isSelected = selectedCareer === career.id
              return (
                <article className={`career-result-card ${isSelected ? 'career-result-selected' : ''}`} key={career.id}>
                  <div className="career-result-top">
                    <div className={`career-result-icon career-color-${career.id}`}><Icon size={22} /></div>
                    {index === 0 && <span className="career-match-label">Top suggestion</span>}
                  </div>
                  <h2>{career.title}</h2>
                  <div className="career-match-score">
                    <span>Career match</span>
                    <strong>{career.matchPercentage}%</strong>
                  </div>

                  <div className="career-match-track">
                    <div
                      className="career-match-fill"
                      style={{ width: `${career.matchPercentage}%` }}
                    />
                  </div>

                  <p>{career.description}</p>
                  <div className="career-reason"><strong>Why explore it?</strong><span>{career.strengths}</span></div>
                  <div className="career-skills">
                    {career.skills.map((skill) => <span key={skill}>{skill}</span>)}
                  </div>
                  <button className={isSelected ? 'career-select-button selected' : 'career-select-button'} onClick={() => setSelectedCareer(career.id)}>
                    {isSelected ? <><CheckCircle2 size={16} /> Selected</> : <>Explore this career <ArrowRight size={16} /></>}
                  </button>
                </article>
              )
            })}
          </div>

          {selectedCareer && (
            <div className="assessment-next-step">
              <div>
                <p className="assessment-eyebrow">YOUR NEXT STEP</p>
                <h2>Ready to explore {careers.find((career) => career.id === selectedCareer)?.title}?</h2>
                <p>Next, compare the career's skills with your current experience and create a learning roadmap.</p>
              </div>
              <button className="assessment-primary-button" onClick={() => window.dispatchEvent(new CustomEvent('pathpilot-career-selected', { detail: selectedCareer }))}>
                Continue to roadmap <ArrowRight size={17} />
              </button>
            </div>
          )}

          <p className="assessment-disclaimer">These suggestions reflect your answers, not a scientific personality diagnosis or a guarantee of career success. Explore more than one path before deciding.</p>
        </section>
      </div>
    )
  }

  return (
    <div className="assessment-page">
      <div className="assessment-top">
        <div className="assessment-brand"><span><Sparkles size={19} /></span> Career discovery</div>
        <span className="assessment-step-label">Question {answers.length + 1} of {questions.length}</span>
      </div>

      <div className="assessment-progress-track">
        <div className="assessment-progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <section className="assessment-question-layout">
        <div className="assessment-question-intro">
          <div className="assessment-icon-large"><Brain size={29} /></div>
          <p className="assessment-eyebrow">GET TO KNOW YOURSELF</p>
          <h1>Find a direction<br />that feels like <span>you.</span></h1>
          <p>Answer a few simple questions about what you enjoy. There are no right or wrong answers.</p>
          <div className="assessment-time"><Target size={16} /> About 2 minutes</div>
        </div>

        <div className="assessment-question-card">
          <div className="assessment-card-heading">
            <span className="assessment-question-number">0{answers.length + 1}</span>
            <span className="assessment-eyebrow">YOUR INTERESTS</span>
          </div>
          <h2>{currentQuestion.title}</h2>
          <p className="assessment-question-subtitle">{currentQuestion.subtitle}</p>

          <div className="assessment-options">
            {currentQuestion.options.map((option, index) => (
              <button key={option.label} className="assessment-option" onClick={() => chooseAnswer(index)}>
                <span className="assessment-option-letter">{String.fromCharCode(65 + index)}</span>
                <span className="assessment-option-copy"><strong>{option.label}</strong><small>{option.detail}</small></span>
                <ArrowRight className="assessment-option-arrow" size={17} />
              </button>
            ))}
          </div>

          <div className="assessment-card-footer">
            <button className="assessment-quiet-button" onClick={goBack} disabled={answers.length === 0}><ArrowLeft size={16} /> Back</button>
            <span>Select one answer to continue</span>
          </div>
        </div>
      </section>
      <p className="assessment-bottom-note">Your answers help suggest possibilities. You can change your mind at any time.</p>
    </div>
  )
}
