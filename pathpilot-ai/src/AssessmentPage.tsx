
import { useState } from 'react'
import {
  ArrowLeft, ArrowRight, Brain, CheckCircle2,
  Code2, Database, Palette, Sparkles, Target,
  RotateCcw
} from 'lucide-react'

import { type CareerId, type Question, drawQuestions, pickAdaptiveQuestion } from './questionBank'
import { getAdvice, type Advice } from './api'

const RANDOM_COUNT = 5
const TOTAL_QUESTIONS = 8

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

const streams: Record<CareerId, { stream: string; subjects: string; degrees: string }> = {
  software: { stream: 'Science (PCM) with Computer Science', subjects: 'Maths, Physics, Computer Science', degrees: 'B.Tech/BE CSE or IT, BCA, B.Sc Computer Science' },
  data: { stream: 'Science (PCM) or Commerce with Maths', subjects: 'Maths, Statistics, Economics or CS', degrees: 'B.Sc Statistics/Data Science, BCA, B.Com (Hons) with analytics' },
  design: { stream: 'Any stream; Arts or Science both work', subjects: 'Fine Arts, Psychology, Computer basics', degrees: 'B.Des (NID/NIFT/UCEED), BFA, B.Sc Multimedia' },
  ai: { stream: 'Science (PCM) — Maths is essential', subjects: 'Maths, Physics, Computer Science', degrees: 'B.Tech CSE/AI & ML, B.Sc Maths/Data Science' },
  product: { stream: 'Commerce or Science; Arts also possible', subjects: 'Business Studies, Economics, Maths', degrees: 'BBA, B.Tech + MBA, B.Com, BA Economics' },
}

function emptyTotals(): Record<CareerId, number> {
  return { software: 0, data: 0, design: 0, ai: 0, product: 0 }
}

export default function AssessmentPage() {
  const [questions, setQuestions] = useState<Question[]>(() => drawQuestions(RANDOM_COUNT))
  const [answers, setAnswers] = useState<number[]>([])
  const [finished, setFinished] = useState(false)
  const [selectedCareer, setSelectedCareer] = useState<CareerId | null>(null)
  const [advice, setAdvice] = useState<Advice | null>(null)
  const [adviceLoading, setAdviceLoading] = useState(false)

  const currentQuestion = questions[answers.length]
  const progress = Math.round((answers.length / TOTAL_QUESTIONS) * 100)

  function totalsFor(answerList: number[]) {
    const totals = emptyTotals()
    answerList.forEach((answer, index) => {
      const option = questions[index]?.options[answer]
      if (!option) return
      for (const [id, value] of Object.entries(option.scores)) totals[id as CareerId] += value ?? 0
    })
    return totals
  }

  const scores = careers.map((career) => {
    const score = questions.reduce((total, question, index) => total + (question.options[answers[index]]?.scores[career.id] ?? 0), 0)
    const maxScore = questions.reduce((total, question) => total + Math.max(...question.options.map((o) => o.scores[career.id] ?? 0)), 0)
    const matchPercentage = maxScore === 0 ? 0 : Math.round((score / maxScore) * 100)
    return { ...career, score, matchPercentage }
  }).sort((a, b) => b.matchPercentage - a.matchPercentage || b.score - a.score)

  function chooseAnswer(index: number) {
    const updatedAnswers = [...answers, index]
    setAnswers(updatedAnswers)

    if (updatedAnswers.length >= TOTAL_QUESTIONS) {
      setFinished(true)
      requestAdvice(updatedAnswers)
      return
    }
    // After the random warm-up, ask adaptive questions that split the top matches.
    if (updatedAnswers.length >= questions.length) {
      const used = new Set(questions.map((q) => q.id))
      const next = pickAdaptiveQuestion(used, totalsFor(updatedAnswers))
      if (next) setQuestions([...questions, next])
      else { setFinished(true); requestAdvice(updatedAnswers) }
    }
  }

  async function requestAdvice(answerList: number[]) {
    setAdvice(null)
    setAdviceLoading(true)
    const answered = answerList.map((a, i) => ({ question: questions[i].title, answer: questions[i].options[a].label }))
    const totals = totalsFor(answerList)
    const ranked = (Object.keys(totals) as CareerId[]).sort((a, b) => totals[b] - totals[a])
    try {
      setAdvice(await getAdvice({ answers: answered, topCareers: ranked.slice(0, 3) }))
    } finally {
      setAdviceLoading(false)
    }
  }

  function goBack() {
    if (finished) {
      setFinished(false)
      setSelectedCareer(null)
      setAnswers((previous) => previous.slice(0, -1))
      return
    }
    const nextAnswers = answers.slice(0, -1)
    setAnswers(nextAnswers)
    // Drop adaptive questions beyond the one being re-answered.
    if (questions.length > Math.max(RANDOM_COUNT, nextAnswers.length + 1)) {
      setQuestions(questions.slice(0, Math.max(RANDOM_COUNT, nextAnswers.length + 1)))
    }
  }

  function restart() {
    setQuestions(drawQuestions(RANDOM_COUNT))
    setAnswers([])
    setFinished(false)
    setSelectedCareer(null)
    setAdvice(null)
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

          <div className="assessment-stream-card">
            <p className="assessment-eyebrow">SUITABLE STREAM FOR {scores[0].title.toUpperCase()}</p>
            <h2>{streams[scores[0].id].stream}</h2>
            <p><strong>Key subjects:</strong> {streams[scores[0].id].subjects}</p>
            <p><strong>Degree options:</strong> {streams[scores[0].id].degrees}</p>
          </div>

          <div className="assessment-stream-card">
            <p className="assessment-eyebrow">
              {advice?.source === 'ai' ? 'AI CAREER ADVICE' : 'PERSONAL ADVICE'}
            </p>
            {adviceLoading && <p>Thinking about your answers…</p>}
            {advice && (
              <>
                <p>{advice.summary}</p>
                {advice.tips.length > 0 && <ul>{advice.tips.map((tip) => <li key={tip}>{tip}</li>)}</ul>}
              </>
            )}
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
        <span className="assessment-step-label">Question {answers.length + 1} of {TOTAL_QUESTIONS}</span>
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
            <span className="assessment-question-number">{String(answers.length + 1).padStart(2, '0')}</span>
            <span className="assessment-eyebrow">{answers.length >= RANDOM_COUNT ? 'NARROWING IT DOWN' : 'YOUR INTERESTS'}</span>
          </div>
          <h2>{currentQuestion?.title}</h2>
          <p className="assessment-question-subtitle">{currentQuestion?.subtitle}</p>

          <div className="assessment-options">
            {currentQuestion?.options.map((option, index) => (
              <button key={currentQuestion.id + option.label} className="assessment-option" onClick={() => chooseAnswer(index)}>
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
