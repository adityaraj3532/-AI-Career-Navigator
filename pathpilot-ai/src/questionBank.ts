export type CareerId = 'software' | 'data' | 'design' | 'ai' | 'product'

export type Option = {
  label: string
  detail: string
  scores: Partial<Record<CareerId, number>>
}

export type Question = {
  id: string
  title: string
  subtitle: string
  options: Option[]
}

export const questionBank: Question[] = [
  { id: 'activity', title: 'What kind of activity sounds most interesting?', subtitle: 'Choose the activity you would enjoy trying.', options: [
    { label: 'Building an app or website', detail: 'Create something people can use', scores: { software: 3, ai: 1 } },
    { label: 'Finding patterns in information', detail: 'Explore numbers and discover insights', scores: { data: 3, ai: 2 } },
    { label: 'Designing a beautiful interface', detail: 'Make a product easier to use', scores: { design: 3, product: 1 } },
    { label: 'Solving a real user problem', detail: 'Understand needs and plan a solution', scores: { product: 3, design: 1 } },
  ] },
  { id: 'challenge', title: 'Which challenge would you choose?', subtitle: 'There is no right or wrong answer.', options: [
    { label: 'Debug a tricky coding problem', detail: 'Find why a program is not working', scores: { software: 3, ai: 1 } },
    { label: 'Explain what a dataset reveals', detail: 'Turn information into a useful conclusion', scores: { data: 3, ai: 1 } },
    { label: 'Improve a confusing app screen', detail: 'Make it simpler and clearer', scores: { design: 3, product: 1 } },
    { label: 'Decide which feature to build first', detail: 'Balance user needs and priorities', scores: { product: 3, software: 1 } },
  ] },
  { id: 'learn-first', title: 'What would you like to learn first?', subtitle: 'Pick the topic you are most curious about.', options: [
    { label: 'Programming and app development', detail: 'Write code and build projects', scores: { software: 3 } },
    { label: 'SQL, statistics, and data', detail: 'Work with information and evidence', scores: { data: 3, ai: 1 } },
    { label: 'Visual design and user experience', detail: 'Create clear digital experiences', scores: { design: 3 } },
    { label: 'AI tools and intelligent systems', detail: 'Explore how AI applications work', scores: { ai: 3, software: 1 } },
  ] },
  { id: 'solve', title: 'How do you prefer to solve problems?', subtitle: 'Think about what feels natural or enjoyable.', options: [
    { label: 'Break the problem into logical steps', detail: 'Work through it systematically', scores: { software: 2, ai: 1, data: 1 } },
    { label: 'Look for patterns and evidence', detail: 'Use information to reach a conclusion', scores: { data: 3, ai: 1 } },
    { label: 'Sketch ideas and try different layouts', detail: 'Explore visual possibilities', scores: { design: 3 } },
    { label: 'Discuss the problem and organize a plan', detail: 'Bring people and ideas together', scores: { product: 3 } },
  ] },
  { id: 'proud', title: 'Which result would make you proud?', subtitle: 'Imagine finishing a personal project.', options: [
    { label: 'A working app people can use', detail: 'Something functional from start to finish', scores: { software: 3 } },
    { label: 'A report that reveals an insight', detail: 'A discovery backed by data', scores: { data: 3 } },
    { label: 'A design people find easy to use', detail: 'A thoughtful, polished experience', scores: { design: 3 } },
    { label: 'A smart tool that automates a task', detail: 'A useful application powered by AI', scores: { ai: 3, software: 1 } },
  ] },
  { id: 'style', title: 'Which work style appeals to you?', subtitle: 'Most careers include a mix of these activities.', options: [
    { label: 'Focused individual problem solving', detail: 'Spend time building and improving', scores: { software: 2, ai: 1, data: 1 } },
    { label: 'Research and careful investigation', detail: 'Explore evidence before deciding', scores: { data: 2, ai: 2 } },
    { label: 'Creative iteration and feedback', detail: 'Try ideas and improve them', scores: { design: 3 } },
    { label: 'Collaborating and coordinating', detail: 'Help a team move toward a goal', scores: { product: 3 } },
  ] },
  { id: 'subject', title: 'Which subject do you enjoy most?', subtitle: 'Choose based on your interest, not your grades.', options: [
    { label: 'Logic, mathematics, or programming', detail: 'Rules, systems, and problem solving', scores: { software: 2, ai: 2 } },
    { label: 'Numbers, research, and interpretation', detail: 'Understand what the evidence means', scores: { data: 3, ai: 1 } },
    { label: 'Art, visuals, and human behavior', detail: 'How people see and use things', scores: { design: 3 } },
    { label: 'Business, teamwork, and planning', detail: 'People, goals, and decisions', scores: { product: 3 } },
  ] },
  { id: 'impact', title: 'What would you like your work to improve?', subtitle: 'Think about the impact you want to make.', options: [
    { label: 'Make technology work better', detail: 'Reliable, useful software', scores: { software: 3 } },
    { label: 'Help people make better decisions', detail: 'Clear insights from data', scores: { data: 3 } },
    { label: 'Make technology easier for people', detail: 'Simple and accessible experiences', scores: { design: 3 } },
    { label: 'Find new ways to solve hard problems', detail: 'Experiment with intelligent tools', scores: { ai: 3, product: 1 } },
  ] },
  { id: 'weekend', title: 'You have a free weekend. What do you try?', subtitle: 'Pick what you would actually do.', options: [
    { label: 'Code a small game or bot', detail: 'Tinker until it works', scores: { software: 3, ai: 1 } },
    { label: 'Track something and chart it', detail: 'Sleep, spending, sports stats…', scores: { data: 3 } },
    { label: 'Redesign a poster or app screen', detail: 'Make it look and feel better', scores: { design: 3 } },
    { label: 'Organize an event or club plan', detail: 'Get people moving together', scores: { product: 3 } },
  ] },
  { id: 'youtube', title: 'Which video would you click first?', subtitle: 'Go with your gut.', options: [
    { label: '“How ChatGPT actually works”', detail: 'Neural networks explained', scores: { ai: 3, data: 1 } },
    { label: '“Build a full app in one hour”', detail: 'Live coding walkthrough', scores: { software: 3 } },
    { label: '“Why this app design is genius”', detail: 'UX breakdown', scores: { design: 3, product: 1 } },
    { label: '“How startups pick what to build”', detail: 'Product strategy', scores: { product: 3 } },
  ] },
  { id: 'team-role', title: 'In a group project, you usually…', subtitle: 'Think about past school or college projects.', options: [
    { label: 'Build the actual working thing', detail: 'You are the maker', scores: { software: 3, ai: 1 } },
    { label: 'Research and back it with facts', detail: 'You are the analyst', scores: { data: 3, ai: 1 } },
    { label: 'Make the slides and visuals', detail: 'You are the designer', scores: { design: 3 } },
    { label: 'Divide work and keep deadlines', detail: 'You are the organizer', scores: { product: 3 } },
  ] },
  { id: 'math', title: 'How do you feel about mathematics?', subtitle: 'Honesty helps the suggestion.', options: [
    { label: 'I love it, especially stats and algebra', detail: 'Equations are fun', scores: { ai: 3, data: 2 } },
    { label: 'Fine when it solves a real problem', detail: 'Practical math', scores: { software: 2, data: 1 } },
    { label: 'I prefer visuals over numbers', detail: 'Shapes and layouts', scores: { design: 3 } },
    { label: 'I prefer people and ideas', detail: 'Words over numbers', scores: { product: 3, design: 1 } },
  ] },
  { id: 'frustration', title: 'What frustrates you most in apps?', subtitle: 'Your annoyances reveal your instincts.', options: [
    { label: 'They crash or load slowly', detail: 'Broken engineering', scores: { software: 3 } },
    { label: 'Buttons are confusing to find', detail: 'Poor design', scores: { design: 3 } },
    { label: 'Recommendations are not smart', detail: 'Weak intelligence', scores: { ai: 3, data: 1 } },
    { label: 'Features nobody actually needs', detail: 'Wrong priorities', scores: { product: 3 } },
  ] },
  { id: 'tool', title: 'Which tool would you like to master?', subtitle: 'Imagine being an expert at it.', options: [
    { label: 'VS Code and GitHub', detail: 'Developer tools', scores: { software: 3 } },
    { label: 'Excel, SQL and Power BI', detail: 'Analysis tools', scores: { data: 3 } },
    { label: 'Figma', detail: 'Design tool', scores: { design: 3 } },
    { label: 'Python notebooks and PyTorch', detail: 'ML tools', scores: { ai: 3, data: 1 } },
  ] },
  { id: 'feedback', title: 'Which compliment would feel best?', subtitle: 'What do you want to be known for?', options: [
    { label: '“Your code is so clean”', detail: 'Craft', scores: { software: 3 } },
    { label: '“Your insight changed our decision”', detail: 'Clarity', scores: { data: 3, product: 1 } },
    { label: '“This is so easy to use”', detail: 'Empathy', scores: { design: 3 } },
    { label: '“Your model is surprisingly accurate”', detail: 'Intelligence', scores: { ai: 3 } },
  ] },
  { id: 'future', title: 'In 5 years, you picture yourself…', subtitle: 'Dream a little.', options: [
    { label: 'Leading a product team', detail: 'Shaping what gets built', scores: { product: 3 } },
    { label: 'Training AI models', detail: 'At a research lab or startup', scores: { ai: 3 } },
    { label: 'Senior engineer shipping systems', detail: 'Owning critical code', scores: { software: 3 } },
    { label: 'Designing apps millions use', detail: 'Crafting experiences', scores: { design: 3 } },
  ] },
]

export function shuffle<T>(items: T[]): T[] {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

/** Pick a fresh random set of questions, with options in random order. */
export function drawQuestions(count: number): Question[] {
  return shuffle(questionBank)
    .slice(0, count)
    .map((q) => ({ ...q, options: shuffle(q.options) }))
}

/**
 * Adaptive pick: choose the unused question that best separates the
 * two careers currently closest to each other.
 */
export function pickAdaptiveQuestion(used: Set<string>, totals: Record<CareerId, number>): Question | undefined {
  const remaining = questionBank.filter((q) => !used.has(q.id))
  if (remaining.length === 0) return undefined
  const [first, second] = (Object.keys(totals) as CareerId[]).sort((a, b) => totals[b] - totals[a])
  const spread = (q: Question) =>
    q.options.reduce((sum, o) => sum + Math.abs((o.scores[first] ?? 0) - (o.scores[second] ?? 0)), 0)
  const best = Math.max(...remaining.map(spread))
  const candidates = remaining.filter((q) => spread(q) >= best - 1)
  const chosen = candidates[Math.floor(Math.random() * candidates.length)]
  return { ...chosen, options: shuffle(chosen.options) }
}
