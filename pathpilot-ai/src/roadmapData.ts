// Roadmap content for each career.

export type RoadmapTask = {
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

const softwareTasks: RoadmapTask[] = [
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


const designTasks: RoadmapTask[] = [
  {
    id: 1, phase: 1, title: "Learn design fundamentals", duration: "4 hours",
    description: "Understand hierarchy, spacing, color, and typography.",
    instructions: ["Study visual hierarchy and alignment.", "Learn the 8-point spacing grid.", "Pick a color palette and two fonts.", "Recreate a simple card layout on paper."],
    criteria: ["You can explain hierarchy with an example.", "Your layout uses consistent spacing."],
    resource: "Material Design foundations", resourceUrl: "https://m3.material.io/foundations",
  },
  {
    id: 2, phase: 1, title: "Get comfortable in Figma", duration: "5 hours",
    description: "Use frames, auto-layout, and components to build screens.",
    instructions: ["Create a free Figma account.", "Learn frames, auto-layout, and constraints.", "Build a reusable button component.", "Design a login screen."],
    criteria: ["The login screen uses auto-layout.", "The button is a reusable component."],
    resource: "Figma Learn", resourceUrl: "https://help.figma.com/hc/en-us",
  },
  {
    id: 3, phase: 2, title: "Run a mini user research study", duration: "4 hours",
    description: "Talk to real users and turn their problems into insights.",
    instructions: ["Pick an app you and friends use.", "Interview 3 people about pain points.", "Group notes into themes.", "Write 3 problem statements."],
    criteria: ["3 interviews are documented.", "Problem statements are based on evidence."],
    resource: "NN/g: User interviews", resourceUrl: "https://www.nngroup.com/articles/user-interviews/",
  },
  {
    id: 4, phase: 2, title: "Prototype and usability test", duration: "6 hours",
    description: "Turn insights into a clickable prototype and test it.",
    instructions: ["Sketch 3 solution ideas.", "Build a clickable Figma prototype.", "Run a usability test with 3 people.", "List the changes you would make."],
    criteria: ["The prototype is clickable end-to-end.", "Test findings are written down."],
    resource: "NN/g: Usability testing 101", resourceUrl: "https://www.nngroup.com/articles/usability-testing-101/",
    project: "A tested clickable prototype.",
  },
  {
    id: 5, phase: 3, title: "Publish a UX case study", duration: "1 week",
    description: "Show your process, not just final screens.",
    instructions: ["Write the problem, research, ideas, and outcome.", "Include before/after screens.", "Publish on Behance or a portfolio site.", "Ask a peer for feedback."],
    criteria: ["The case study explains your decisions.", "It is publicly accessible."],
    resource: "Behance", resourceUrl: "https://www.behance.net/",
    project: "A public UX case study.",
  },
]

const aiTasks: RoadmapTask[] = [
  {
    id: 1, phase: 1, title: "Python for data and ML", duration: "6 hours",
    description: "Learn the Python you need for machine learning.",
    instructions: ["Practice lists, dicts, functions, and loops.", "Learn NumPy arrays.", "Load a CSV with pandas.", "Plot a chart with matplotlib."],
    criteria: ["You can load and plot a dataset.", "Code runs without errors in a notebook."],
    resource: "Kaggle Learn: Python", resourceUrl: "https://www.kaggle.com/learn/python",
  },
  {
    id: 2, phase: 1, title: "Math for machine learning", duration: "6 hours",
    description: "Build intuition for vectors, probability, and gradients.",
    instructions: ["Review vectors and matrix multiplication.", "Learn mean, variance, and probability.", "Understand what a gradient is.", "Solve 10 practice problems."],
    criteria: ["You can explain a gradient in plain words.", "Practice problems are completed."],
    resource: "Khan Academy: Linear algebra", resourceUrl: "https://www.khanacademy.org/math/linear-algebra",
  },
  {
    id: 3, phase: 2, title: "Train your first model", duration: "6 hours",
    description: "Use scikit-learn to train and evaluate a model.",
    instructions: ["Pick a beginner dataset (e.g. Titanic).", "Split into train and test sets.", "Train a logistic regression model.", "Measure accuracy and inspect errors."],
    criteria: ["The model is evaluated on held-out data.", "You can explain the accuracy score."],
    resource: "scikit-learn getting started", resourceUrl: "https://scikit-learn.org/stable/getting_started.html",
    project: "A notebook with a trained, evaluated model.",
  },
  {
    id: 4, phase: 2, title: "Build with neural networks or LLM APIs", duration: "8 hours",
    description: "Try deep learning or build an app using an AI API.",
    instructions: ["Follow a beginner PyTorch tutorial, or call an LLM API to build a small helper app.", "Test it on new inputs.", "Handle errors and bad inputs.", "Write down limitations you noticed."],
    criteria: ["The model or app works on new inputs.", "Limitations are documented."],
    resource: "PyTorch tutorials", resourceUrl: "https://pytorch.org/tutorials/beginner/basics/intro.html",
  },
  {
    id: 5, phase: 3, title: "Ship an end-to-end AI project", duration: "1 week",
    description: "Deploy a model or AI app someone else can try.",
    instructions: ["Choose a real problem you care about.", "Build and evaluate the solution.", "Deploy with Streamlit or Hugging Face Spaces.", "Write a README with results."],
    criteria: ["A public demo link works.", "The README explains data, model, and results."],
    resource: "Hugging Face Spaces", resourceUrl: "https://huggingface.co/spaces",
    project: "A deployed AI demo with documentation.",
  },
]

const productTasks: RoadmapTask[] = [
  {
    id: 1, phase: 1, title: "Understand the product role", duration: "3 hours",
    description: "Learn what product managers do day to day.",
    instructions: ["Read about the PM role and responsibilities.", "Watch one PM day-in-the-life video.", "List 5 skills a PM needs.", "Pick 2 you want to grow first."],
    criteria: ["You can describe the PM role in 3 sentences."],
    resource: "Atlassian: Product management", resourceUrl: "https://www.atlassian.com/agile/product-management",
  },
  {
    id: 2, phase: 1, title: "Write a problem statement", duration: "4 hours",
    description: "Practice identifying real user problems.",
    instructions: ["Choose an app you use daily.", "Interview 3 users about frustrations.", "Write a clear problem statement.", "Define who the user is."],
    criteria: ["The problem is backed by user quotes.", "The target user is specific."],
    resource: "Product School blog", resourceUrl: "https://productschool.com/blog",
  },
  {
    id: 3, phase: 2, title: "Prioritize features", duration: "4 hours",
    description: "Use frameworks to decide what to build first.",
    instructions: ["List 10 possible features.", "Score them with RICE.", "Pick the top 3 and justify them.", "Create a simple roadmap."],
    criteria: ["Each feature has a RICE score.", "The top picks are justified."],
    resource: "Intercom: RICE prioritization", resourceUrl: "https://www.intercom.com/blog/rice-simple-prioritization-for-product-managers/",
  },
  {
    id: 4, phase: 2, title: "Define metrics and read data", duration: "5 hours",
    description: "Learn to measure success with data.",
    instructions: ["Learn north-star and supporting metrics.", "Write basic SQL queries.", "Define success metrics for your feature.", "Mock a simple dashboard."],
    criteria: ["Metrics are specific and measurable.", "You can write a basic SELECT query."],
    resource: "Mode SQL tutorial", resourceUrl: "https://mode.com/sql-tutorial/",
  },
  {
    id: 5, phase: 3, title: "Create a product case study", duration: "1 week",
    description: "Bring it all together in a portfolio piece.",
    instructions: ["Write a PRD for your feature.", "Include wireframes, metrics, and roadmap.", "Present it to a friend or mentor.", "Publish it online."],
    criteria: ["The PRD covers problem, solution, and metrics.", "It is publicly shareable."],
    resource: "Lenny's Newsletter", resourceUrl: "https://www.lennysnewsletter.com/",
    project: "A published PRD-style case study.",
  },
]

export type RoadmapCareerId = 'software' | 'data' | 'design' | 'ai' | 'product'

export type RoadmapPhase = { id: number; title: string; subtitle: string }

export const roadmaps: Record<RoadmapCareerId, { title: string; tasks: RoadmapTask[]; phases: RoadmapPhase[] }> = {
  software: { title: 'Software Developer', tasks: softwareTasks, phases: [
    { id: 1, title: 'Build foundations', subtitle: 'HTML and CSS' },
    { id: 2, title: 'Write interactive code', subtitle: 'JavaScript and React' },
    { id: 3, title: 'Prove your skills', subtitle: 'Portfolio and deployment' }] },
  data: { title: 'Data Analyst', tasks: dataAnalystTasks, phases: [
    { id: 1, title: 'Build foundations', subtitle: 'Spreadsheets and SQL' },
    { id: 2, title: 'Analyze and visualize', subtitle: 'Python and charts' },
    { id: 3, title: 'Prove your skills', subtitle: 'Portfolio project' }] },
  design: { title: 'UI/UX Designer', tasks: designTasks, phases: [
    { id: 1, title: 'Build foundations', subtitle: 'Design basics and Figma' },
    { id: 2, title: 'Design for real users', subtitle: 'Research and prototyping' },
    { id: 3, title: 'Prove your skills', subtitle: 'Case study' }] },
  ai: { title: 'AI / ML Engineer', tasks: aiTasks, phases: [
    { id: 1, title: 'Build foundations', subtitle: 'Python and math' },
    { id: 2, title: 'Train models', subtitle: 'scikit-learn, PyTorch, LLM APIs' },
    { id: 3, title: 'Prove your skills', subtitle: 'Deployed AI project' }] },
  product: { title: 'Product Manager', tasks: productTasks, phases: [
    { id: 1, title: 'Build foundations', subtitle: 'Role and user problems' },
    { id: 2, title: 'Decide and measure', subtitle: 'Prioritization and metrics' },
    { id: 3, title: 'Prove your skills', subtitle: 'Product case study' }] },
}

/** Rough hours for a duration string like "3 hours" or "1 week". */
export function taskHours(duration: string): number {
  const n = parseFloat(duration) || 1
  return /week/i.test(duration) ? n * 10 : n
}
