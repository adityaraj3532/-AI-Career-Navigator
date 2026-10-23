

import { useMemo, useState } from 'react'
import {
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  Circle,
  Clock3,
  Code2,
  ExternalLink,
  Flag,
  
  Rocket,
  Target,
} from 'lucide-react'

type RoadmapTask = {
  id: number
  phase: number
  title: string
  duration: string
  description: string
  instructions: string[]
  criteria: string[]
  resource: string
  resourceUrl: string
  project?: string
}

const tasks: RoadmapTask[] = [
  {
    id: 1,
    phase: 1,
    title: 'Build your first webpage',
    duration: '2 hours',
    description:
      'Learn how HTML gives a webpage its structure. Build a simple personal introduction page.',
    instructions: [
      'Learn the purpose of HTML, head, body, headings, and paragraphs.',
      'Create an index.html file in a new folder.',
      'Add a heading, an introduction paragraph, and links to two interests.',
      'Open the file in your browser and check the result.',
    ],
    criteria: [
      'The page has a heading and introduction.',
      'At least one link works.',
      'The page opens in a browser.',
    ],
    resource: 'MDN: Your first website',
    resourceUrl: 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Getting_started/Your_first_website',
  },
  {
    id: 2,
    phase: 1,
    title: 'Style it with CSS',
    duration: '3 hours',
    description:
      'Make your webpage readable and attractive using colors, spacing, and layout.',
    instructions: [
      'Learn selectors, colors, margins, padding, and fonts.',
      'Create a separate style.css file.',
      'Connect the CSS file to your HTML.',
      'Make the page readable on a mobile screen.',
    ],
    criteria: [
      'CSS is in a separate file.',
      'The page has consistent spacing and typography.',
      'The content remains readable on a narrow screen.',
    ],
    resource: 'MDN: CSS first steps',
    resourceUrl: 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics',
  },
  {
    id: 3,
    phase: 2,
    title: 'Learn JavaScript basics',
    duration: '5 hours',
    description:
      'Make your page interactive with variables, conditions, functions, and events.',
    instructions: [
      'Practice variables, strings, arrays, and functions.',
      'Learn how click events work.',
      'Add a button that changes a message on the page.',
      'Test the button in your browser.',
    ],
    criteria: [
      'The button responds to a click.',
      'The code uses a function and an event listener.',
      'No errors appear in the browser console.',
    ],
    resource: 'MDN: JavaScript first steps',
    resourceUrl: 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Getting_started/Your_first_website/Adding_interactivity',
  },
  {
    id: 4,
    phase: 2,
    title: 'Build a React task tracker',
    duration: '6 hours',
    description:
      'Use components and state to create a small app that manages tasks.',
    instructions: [
      'Create a React project with TypeScript.',
      'Split the interface into reusable components.',
      'Add tasks using an input and button.',
      'Allow users to mark tasks complete.',
    ],
    criteria: [
      'Users can add a task.',
      'Users can mark a task complete.',
      'The UI updates when state changes.',
    ],
    resource: 'React: Quick Start',
    resourceUrl: 'https://react.dev/learn',
    project: 'A working task tracker with a clear README.',
  },
  {
    id: 5,
    phase: 3,
    title: 'Publish a portfolio project',
    duration: '1 week',
    description:
      'Turn your work into evidence that another person can inspect and run.',
    instructions: [
      'Polish your task tracker and handle empty states.',
      'Add a README explaining the problem, features, and setup.',
      'Push the code to GitHub.',
      'Deploy the project and test the public link.',
    ],
    criteria: [
      'The GitHub repository is accessible.',
      'The README explains how to run the project.',
      'A live demo works.',
      'You can explain the main technical decisions.',
    ],
    resource: 'GitHub Skills',
    resourceUrl: 'https://skills.github.com/',
    project: 'A public repository plus a live demo.',
  },
]


const dataAnalystTasks: RoadmapTask[] = [
  {
    id: 1,
    phase: 1,
    title: 'Learn spreadsheet fundamentals',
    duration: '3 hours',
    description: 'Organize data, use formulas, and summarize information in spreadsheets.',
    instructions: [
      'Learn rows, columns, cell references, and basic data types.',
      'Practice SUM, AVERAGE, COUNTIF, and IF formulas.',
      'Sort and filter a sample dataset.',
      'Create a summary of your findings.',
    ],
    criteria: [
      'The dataset is organized and readable.',
      'At least three formulas work correctly.',
      'The summary communicates useful findings.',
    ],
    resource: 'Google Sheets training',
    resourceUrl: 'https://support.google.com/a/users/answer/9282959',
  },
  {
    id: 2,
    phase: 1,
    title: 'Query data with SQL',
    duration: '5 hours',
    description: 'Learn to retrieve and analyze information from relational databases.',
    instructions: [
      'Understand tables, rows, and columns.',
      'Practice SELECT, FROM, and WHERE.',
      'Use ORDER BY and GROUP BY.',
      'Calculate totals using aggregate functions.',
    ],
    criteria: [
      'Queries select the correct columns.',
      'Filters return the expected records.',
      'Grouped results use aggregate functions correctly.',
    ],
    resource: 'SQLBolt interactive lessons',
    resourceUrl: 'https://sqlbolt.com/',
  },
  {
    id: 3,
    phase: 2,
    title: 'Analyze data with Python',
    duration: '6 hours',
    description: 'Use Python and pandas to clean and explore datasets.',
    instructions: [
      'Learn Python variables, lists, and functions.',
      'Load a CSV file using pandas.',
      'Inspect missing values and duplicate rows.',
      'Calculate summary statistics.',
    ],
    criteria: [
      'The CSV file loads successfully.',
      'Missing values and duplicates are investigated.',
      'The analysis produces meaningful summary statistics.',
    ],
    resource: 'pandas getting started',
    resourceUrl: 'https://pandas.pydata.org/docs/getting_started/',
    project: 'A cleaned dataset with a short analysis.',
  },
  {
    id: 4,
    phase: 2,
    title: 'Visualize data and discover patterns',
    duration: '5 hours',
    description: 'Turn analysis into charts that communicate useful insights.',
    instructions: [
      'Choose a dataset that interests you.',
      'Create at least three suitable charts.',
      'Label chart axes and titles clearly.',
      'Write three observations supported by the data.',
    ],
    criteria: [
      'Charts represent the data accurately.',
      'Labels and titles are clear.',
      'Insights are supported by the dataset.',
    ],
    resource: 'Microsoft Power BI learning',
    resourceUrl: 'https://learn.microsoft.com/en-us/training/powerplatform/power-bi/',
    project: 'A small data analysis report with charts.',
  },
  {
    id: 5,
    phase: 3,
    title: 'Build a data analytics portfolio project',
    duration: '1 week',
    description: 'Complete an end-to-end analysis and present your findings.',
    instructions: [
      'Choose a public dataset.',
      'Clean and analyze it using SQL, Python, or spreadsheets.',
      'Create a dashboard or report.',
      'Document your methods and findings.',
      'Publish your project and explain your conclusions.',
    ],
    criteria: [
      'The dataset and methods are documented.',
      'The analysis is reproducible.',
      'The report includes meaningful findings.',
      'The project is ready to show in a portfolio.',
    ],
    resource: 'Kaggle datasets',
    resourceUrl: 'https://www.kaggle.com/datasets',
    project: 'A documented analysis with visualizations and conclusions.',
  },
]


const phases = [
  { id: 1, title: 'Build foundations', subtitle: 'HTML and CSS' },
  { id: 2, title: 'Write interactive code', subtitle: 'JavaScript and React' },
  { id: 3, title: 'Prove your skills', subtitle: 'Portfolio and deployment' },
]

export default function CareerRoadmapPage() {
//   const [career, setCareer] = useState('Frontend Developer')
  const [career, setCareer] = useState(() => {
  const savedCareer = localStorage.getItem('pathpilot-selected-career')

  const careerNames: Record<string, string> = {
    software: 'Software Developer',
    data: 'Data Analyst',
    design: 'UI/UX Designer',
    ai: 'AI / ML Engineer',
    product: 'Software Developer',
  }

  return careerNames[savedCareer ?? ''] ?? 'Frontend Developer'
})
const activeTasks =
  career === 'Data Analyst'
    ? dataAnalystTasks
    : tasks

  const [hours, setHours] = useState('8')
  const [completed, setCompleted] = useState<number[]>([])
  const [activeTaskId, setActiveTaskId] = useState(1)
  const [expandedPhase, setExpandedPhase] = useState<number>(1)
  const [showAll, setShowAll] = useState(false)


  
  
  const progress = Math.round(
    (completed.length / activeTasks.length) * 100
    )

    
    const nextTask = useMemo(
    () => activeTasks.find((task) => !completed.includes(task.id)),
    [activeTasks, completed],
    )

    const activeTask =
    activeTasks.find((task) => task.id === activeTaskId) ?? activeTasks[0]

  
    function toggleComplete(id: number) {
    const isDone = completed.includes(id)

    setCompleted((previous) =>
        isDone
        ? previous.filter((taskId) => taskId !== id)
        : [...previous, id],
    )

    if (!isDone) {
        const next = activeTasks.find(
        (task) => task.id !== id && !completed.includes(task.id),
        )

        if (next) {
        setActiveTaskId(next.id)
        setExpandedPhase(next.phase)
        }
    }
    }


  
    function selectCareer(value: string) {
    const careerIds: Record<string, string> = {
        'Frontend Developer': 'software',
        'Software Developer': 'software',
        'Data Analyst': 'data',
        'UI/UX Designer': 'design',
        'AI / ML Engineer': 'ai',
    }

    setCareer(value)
    localStorage.setItem(
        'pathpilot-selected-career',
        careerIds[value] ?? 'software',
    )
    setCompleted([])
    setActiveTaskId(1)
    setExpandedPhase(1)
    }


 
  return (
    <main className="roadmap-page">
      <header className="roadmap-header">
        <div>
          <p className="roadmap-eyebrow">YOUR CAREER PLAN</p>
          <h1>Your roadmap</h1>
          <p className="roadmap-muted">
            Small steps, practical projects, real evidence of your skills.
          </p>
        </div>
        <div className="roadmap-header-icon">
          <Target size={23} />
        </div>
      </header>

      <section className="roadmap-settings">
        <label>
          <span>Target career</span>
          <select
            value={career}
            onChange={(event) => selectCareer(event.target.value)}
          >
            <option>Frontend Developer</option>
            <option>Software Developer</option>
            <option>Data Analyst</option>
            <option>UI/UX Designer</option>
            <option>AI / ML Engineer</option>
          </select>
        </label>

        <label>
          <span>Study time each week</span>
          <select value={hours} onChange={(event) => setHours(event.target.value)}>
            <option value="3">1–3 hours</option>
            <option value="8">4–8 hours</option>
            <option value="15">9–15 hours</option>
            <option value="20">15+ hours</option>
          </select>
        </label>
      </section>

      <section className="roadmap-progress-card">
        <div className="roadmap-progress-top">
          <div>
            <p className="roadmap-eyebrow">YOUR PROGRESS</p>
            
            <h2>{completed.length} of {activeTasks.length} tasks completed</h2>
          </div>
          <strong>{progress}%</strong>
        </div>
        <div className="roadmap-progress-track">
          <div style={{ width: `${progress}%` }} />
        </div>
        <p className="roadmap-muted">
          {progress === 100
            ? 'Great work! You have completed this sample roadmap.'
            : 'Focus on the next task. You do not need to finish everything today.'}
        </p>
      </section>

      {nextTask && (
        <section className="roadmap-next-card">
          <div className="roadmap-next-icon">
            <Rocket size={21} />
          </div>
          <div className="roadmap-next-copy">
            <p className="roadmap-eyebrow">YOUR NEXT STEP</p>
            <h2>{nextTask.title}</h2>
            <p>{nextTask.description}</p>
            <span className="roadmap-duration">
              <Clock3 size={14} /> {nextTask.duration}
            </span>
          </div>
          <button
            className="roadmap-primary-button"
            onClick={() => {
              setActiveTaskId(nextTask.id)
              setExpandedPhase(nextTask.phase)
              document.getElementById('roadmap-task-detail')?.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
              })
            }}
          >
            Start task <ArrowRight size={16} />
          </button>
        </section>
      )}

      <section className="roadmap-phases">
        <div className="roadmap-section-title">
          <div>
            <h2>Your learning path</h2>
            <p>Open one stage at a time to keep things simple.</p>
          </div>
          <button
            className="roadmap-text-button"
            onClick={() => setShowAll((value) => !value)}
          >
            {showAll ? 'Show less' : 'Show all'}
          </button>
        </div>

        {phases.map((phase) => {
          const phaseTasks = activeTasks.filter((task) => task.phase === phase.id)
          const done = phaseTasks.filter((task) =>
            completed.includes(task.id),
          ).length
          const isOpen = showAll || expandedPhase === phase.id

          return (
            <article className="roadmap-phase" key={phase.id}>
              <button
                className="roadmap-phase-heading"
                onClick={() =>
                  setExpandedPhase(isOpen && !showAll ? 0 : phase.id)
                }
              >
                <span className="roadmap-phase-number">
                  {done === phaseTasks.length
                    ? <Check size={17} />
                    : phase.id}
                </span>
                <span className="roadmap-phase-copy">
                  <strong>{phase.title}</strong>
                  <small>{phase.subtitle}</small>
                </span>
                <span className="roadmap-phase-count">
                  {done}/{phaseTasks.length}
                </span>
                <ChevronDown
                  size={17}
                  className={isOpen ? 'roadmap-chevron-open' : ''}
                />
              </button>

              {isOpen && (
                <div className="roadmap-phase-tasks">


                {phaseTasks.map((task) => {  
                
                    const isDone = completed.includes(task.id)
                    const isActive = activeTaskId === task.id

                    return (
                      <button
                        className={`roadmap-task-row ${isActive ? 'roadmap-task-active' : ''}`}
                        key={task.id}
                        onClick={() => setActiveTaskId(task.id)}
                      >
                        {isDone ? (
                          <CheckCircle2 size={19} />
                        ) : (
                          <Circle size={19} />
                        )}
                        <span>
                          <strong>{task.title}</strong>
                          <small>{task.duration}</small>
                        </span>
                        {isActive && <span className="roadmap-current-tag">Selected</span>}
                      </button>
                    )
                  })}
                </div>
              )}
            </article>
          )
        })}
      </section>

      <section className="roadmap-task-detail" id="roadmap-task-detail">
        <div className="roadmap-detail-heading">
          <div className="roadmap-detail-icon"><BookOpen size={21} /></div>
          <div>
            <p className="roadmap-eyebrow">TASK DETAILS</p>
            <h2>{activeTask.title}</h2>
            <span className="roadmap-duration">
              <Clock3 size={14} /> {activeTask.duration}
            </span>
          </div>
        </div>

        <p className="roadmap-detail-description">{activeTask.description}</p>

        <h3>What to do</h3>
        <ol className="roadmap-instructions">
          {activeTask.instructions.map((instruction) => (
            <li key={instruction}>{instruction}</li>
          ))}
        </ol>

        <a
          className="roadmap-resource-link"
          href={activeTask.resourceUrl}
          target="_blank"
          rel="noreferrer"
        >
          <BookOpen size={17} />
          <span>
            <small>LEARNING RESOURCE</small>
            <strong>{activeTask.resource}</strong>
          </span>
          <ExternalLink size={15} />
        </a>

        {activeTask.project && (
          <div className="roadmap-project-note">
            <Code2 size={18} />
            <span><strong>Project deliverable</strong>{activeTask.project}</span>
          </div>
        )}

        <h3>Completion criteria</h3>
        <p className="roadmap-muted">
          Check each item before marking this task complete.
        </p>

        <CompletionCriteria
          key={activeTask.id}
          criteria={activeTask.criteria}
          completed={completed.includes(activeTask.id)}
          onComplete={() => toggleComplete(activeTask.id)}
        />
      </section>

      <section className="roadmap-job-ready">
        <div className="roadmap-job-icon"><Flag size={20} /></div>
        <div>
          <h2>Learning is only the beginning</h2>
          <p>
            Employers need evidence that you can solve problems. This roadmap
            builds toward projects, a public portfolio, clear explanations of
            your work, and interview practice—not just course completion.
          </p>
          <div className="roadmap-job-points">
            <span><CheckCircle2 size={15} /> Practical projects</span>
            {/* <span><Github size={15} /> Public code</span> */}
            <Code2 size={15} />
            <span><Target size={15} /> Job-readiness milestones</span>
          </div>
        </div>
      </section>
    </main>
  )
}

function CompletionCriteria({
  criteria,
  completed,
  onComplete,
}: {
  criteria: string[]
  completed: boolean
  onComplete: () => void
}) {
  const [checked, setChecked] = useState<boolean[]>(
    () => criteria.map(() => false),
  )

  const allChecked = checked.length > 0 && checked.every(Boolean)

  return (
    <div className="roadmap-completion">
      {criteria.map((criterion, index) => (
        <label className="roadmap-criterion" key={criterion}>
          <input
            type="checkbox"
            checked={checked[index]}
            disabled={completed}
            onChange={(event) =>
              setChecked((previous) =>
                previous.map((value, i) =>
                  i === index ? event.target.checked : value,
                ),
              )
            }
          />
          <span>{criterion}</span>
        </label>
      ))}

      {completed ? (
        <div className="roadmap-completed-message">
          <CheckCircle2 size={18} /> Task completed
          <button type="button" onClick={onComplete}>Undo</button>
        </div>
      ) : (
        <button
          type="button"
          className="roadmap-complete-button"
          disabled={!allChecked}
          onClick={onComplete}
        >
          <CheckCircle2 size={17} />
          Mark task complete
        </button>
      )}

      {!completed && !allChecked && (
        <p className="roadmap-helper">
          Complete all criteria above to unlock this action.
        </p>
      )}
    </div>
  )
}
