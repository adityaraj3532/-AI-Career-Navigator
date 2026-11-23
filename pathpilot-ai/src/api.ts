import type { CareerId } from './questionBank'

export type Advice = { source: 'ai' | 'rules' | 'offline'; summary: string; tips: string[] }

export async function getAdvice(body: { answers: { question: string; answer: string }[]; topCareers: CareerId[] }): Promise<Advice> {
  try {
    const res = await fetch('/api/advice', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
    if (!res.ok) throw new Error(String(res.status))
    return await res.json()
  } catch {
    return { source: 'offline', summary: 'Advice service is unavailable right now — your match scores above are still based on your answers.', tips: [] }
  }
}
