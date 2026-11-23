import { useEffect, useState } from 'react'
import { BookMarked, BookOpen, Bookmark, ExternalLink, FileText, GraduationCap, Search, Sparkles } from 'lucide-react'
import { roadmaps, type RoadmapCareerId } from './roadmapData'
import { learnResources, type LearnResource, type ResourceKind } from './learnData'

const CAREER_KEY = 'pathpilot-selected-career'
const SAVED_KEY = 'pathpilot-reading-list'

const kindInfo: Record<ResourceKind, { label: string; action: string; icon: typeof BookOpen }> = {
  pdf: { label: 'Free PDF / online', action: 'Read free', icon: FileText },
  book: { label: 'Book', action: 'Find book', icon: BookOpen },
  course: { label: 'Course', action: 'Start course', icon: GraduationCap },
}

const filters: { id: 'all' | ResourceKind | 'saved'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'pdf', label: 'Free PDFs' },
  { id: 'book', label: 'Books' },
  { id: 'course', label: 'Courses' },
  { id: 'saved', label: 'My list' },
]

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null) return fallback
    return key === CAREER_KEY ? (raw as T) : (JSON.parse(raw) as T)
  } catch {
    return fallback
  }
}

export default function LearnPage() {
  const [career, setCareer] = useState<RoadmapCareerId>(() => {
    const saved = load<string>(CAREER_KEY, 'software')
    return saved in roadmaps ? (saved as RoadmapCareerId) : 'software'
  })
  const [filter, setFilter] = useState<(typeof filters)[number]['id']>('all')
  const [query, setQuery] = useState('')
  const [saved, setSaved] = useState<string[]>(() => load(SAVED_KEY, []))

  useEffect(() => {
    try { localStorage.setItem(SAVED_KEY, JSON.stringify(saved)) } catch { /* ignore */ }
  }, [saved])

  function chooseCareer(id: RoadmapCareerId) {
    setCareer(id)
    try { localStorage.setItem(CAREER_KEY, id) } catch { /* ignore */ }
  }

  const all = learnResources[career]
  const starter = all.find((r) => r.starter)
  const q = query.trim().toLowerCase()
  const shown = all.filter((r) =>
    (filter === 'all' || (filter === 'saved' ? saved.includes(r.title) : r.kind === filter)) &&
    (!q || `${r.title} ${r.author} ${r.why}`.toLowerCase().includes(q)),
  )

  const toggleSave = (title: string) =>
    setSaved((list) => (list.includes(title) ? list.filter((t) => t !== title) : [...list, title]))

  return (
    <main className="ln-page">
      <header>
        <p className="rm-eyebrow">LEARN</p>
        <h1>Books & resources for your career</h1>
        <p className="rm-muted">Pick a career to see the best books, free PDFs, and courses for it.</p>
      </header>

      <div className="ln-chips" role="tablist" aria-label="Target career">
        {(Object.keys(roadmaps) as RoadmapCareerId[]).map((id) => (
          <button
            key={id}
            role="tab"
            aria-selected={career === id}
            className={career === id ? 'ln-chip is-active' : 'ln-chip'}
            onClick={() => chooseCareer(id)}
          >
            {roadmaps[id].title}
          </button>
        ))}
      </div>

      {starter && (
        <section className="ln-starter">
          <div className="ln-starter-icon"><Sparkles size={22} /></div>
          <div>
            <p className="rm-eyebrow">START HERE</p>
            <h2>{starter.title}</h2>
            <p>{starter.author} · {starter.why}</p>
          </div>
          <a className="rm-primary" href={starter.url} target="_blank" rel="noreferrer">
            {kindInfo[starter.kind].action} <ExternalLink size={15} />
          </a>
        </section>
      )}

      <div className="ln-toolbar">
        <div className="ln-filters">
          {filters.map((f) => (
            <button key={f.id} className={filter === f.id ? 'ln-filter is-active' : 'ln-filter'} onClick={() => setFilter(f.id)}>
              {f.label}
              {f.id === 'saved' && saved.length > 0 && <span>{all.filter((r) => saved.includes(r.title)).length}</span>}
            </button>
          ))}
        </div>
        <label className="ln-search">
          <Search size={15} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search books…" />
        </label>
      </div>

      {shown.length === 0 ? (
        <p className="ln-empty">
          {filter === 'saved' ? 'Nothing saved yet. Tap the bookmark on any resource to add it to your list.' : 'No resources match your search.'}
        </p>
      ) : (
        <div className="ln-grid">
          {shown.map((r) => <ResourceCard key={r.title} resource={r} saved={saved.includes(r.title)} onSave={() => toggleSave(r.title)} />)}
        </div>
      )}

      <p className="ln-note">
        <BookMarked size={14} /> “Free PDF / online” books are published free by their authors. Other books open in
        Open Library, where you can borrow or find them.
      </p>
    </main>
  )
}

function ResourceCard({ resource: r, saved, onSave }: { resource: LearnResource; saved: boolean; onSave: () => void }) {
  const info = kindInfo[r.kind]
  const Icon = info.icon
  return (
    <article className={`ln-card ln-kind-${r.kind}`}>
      <div className="ln-card-top">
        <span className="ln-type"><Icon size={14} /> {info.label}</span>
        <button className={saved ? 'ln-save is-saved' : 'ln-save'} onClick={onSave} aria-label={saved ? 'Remove from my list' : 'Save to my list'}>
          <Bookmark size={17} fill={saved ? 'currentColor' : 'none'} />
        </button>
      </div>
      <h3>{r.title}</h3>
      <p className="ln-author">{r.author}</p>
      <p className="ln-why">{r.why}</p>
      <div className="ln-card-foot">
        <span className={`ln-level ln-level-${r.level.toLowerCase()}`}>{r.level}</span>
        <a href={r.url} target="_blank" rel="noreferrer">{info.action} <ExternalLink size={13} /></a>
      </div>
    </article>
  )
}
