// PathPilot backend: career advice endpoint.
// Uses Claude when ANTHROPIC_API_KEY is set, otherwise a rule-based fallback.

const CAREERS = {
  software: 'Software Developer',
  data: 'Data Analyst',
  design: 'UI/UX Designer',
  ai: 'AI / Machine Learning Engineer',
  product: 'Product Manager',
}

const FALLBACK_TIPS = {
  software: ['Build one small project per month and push it to GitHub.', 'Learn one language deeply (JavaScript or Python) before switching.', 'Practice debugging: read error messages before searching.'],
  data: ['Pick a public dataset you care about and answer one question with it.', 'Get comfortable with SQL GROUP BY and JOINs early.', 'Write short summaries of every chart you make.'],
  design: ['Redesign one app screen a week and explain your choices.', 'Learn Figma auto-layout and components.', 'Talk to 3 real users before designing anything.'],
  ai: ['Strengthen linear algebra, probability and Python first.', 'Reproduce a simple model (e.g. linear regression) from scratch.', 'Try a Kaggle beginner competition.'],
  product: ['Write a one-page problem statement for an app you use.', 'Learn basic SQL so you can read your own metrics.', 'Join or lead a club project to practice prioritization.'],
}

function fallbackAdvice({ answers = [], topCareers = [] }) {
  const [first = 'software', second = 'data'] = topCareers
  const picks = answers.slice(0, 2).map((a) => `“${String(a.answer).replace(/[“”"]/g, '')}”`).join(' and ')
  return {
    source: 'rules',
    summary: `Your answers${picks ? ` like ${picks}` : ''} point most strongly to ${CAREERS[first]}, with ${CAREERS[second]} as a close alternative. Try a small project in each before committing.`,
    tips: FALLBACK_TIPS[first] ?? [],
  }
}

async function claudeAdvice(body, apiKey) {
  const prompt = `A student answered a career-interest quiz.\nAnswers:\n${body.answers
    .map((a) => `- ${a.question} -> ${a.answer}`)
    .join('\n')}\nTop scored careers: ${body.topCareers.map((c) => CAREERS[c] ?? c).join(', ')}.\n\nReply ONLY with JSON: {"summary": "2-3 sentences referencing their specific answers, suggest the best-fit career and a suitable academic stream", "tips": ["3 concrete next steps"]}`

  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-api-key': apiKey, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({ model: process.env.ANTHROPIC_MODEL || 'claude-haiku-5-5', max_tokens: 500, messages: [{ role: 'user', content: prompt }] }),
  })
  if (!res.ok) throw new Error(`Claude API ${res.status}: ${await res.text()}`)
  const data = await res.json()
  const text = data.content?.find((c) => c.type === 'text')?.text ?? ''
  const json = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1))
  return { source: 'ai', summary: String(json.summary), tips: (json.tips ?? []).map(String).slice(0, 5) }
}

export async function getAdvice(body) {
  const apiKey = process.env.ANTHROPIC_API_KEY
  if (apiKey && Array.isArray(body.answers) && body.answers.length) {
    try {
      return await claudeAdvice(body, apiKey)
    } catch (error) {
      console.error('[pathpilot] AI advice failed, using fallback:', error.message)
    }
  }
  return fallbackAdvice(body)
}

/** Connect-style middleware usable by Vite dev/preview or a plain node server. */
export function apiMiddleware(req, res, next) {
  if (!req.url?.startsWith('/api/')) return next()
  const send = (status, payload) => {
    res.statusCode = status
    res.setHeader('content-type', 'application/json')
    res.end(JSON.stringify(payload))
  }
  if (req.url === '/api/health') return send(200, { ok: true, ai: Boolean(process.env.ANTHROPIC_API_KEY) })
  if (req.url === '/api/advice' && req.method === 'POST') {
    let raw = ''
    req.on('data', (chunk) => { raw += chunk; if (raw.length > 50_000) req.destroy() })
    req.on('end', async () => {
      try {
        send(200, await getAdvice(JSON.parse(raw || '{}')))
      } catch (error) {
        send(400, { error: error.message })
      }
    })
    return
  }
  send(404, { error: 'Not found' })
}
