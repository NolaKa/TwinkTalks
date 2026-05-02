import { useMemo, useState } from 'react'
import type { LibraryEntry } from '../types'

const SPINE_COLORS = ['#fef3c7', '#dbeafe', '#dcfce7', '#fce7f3', '#ede9fe', '#fee2e2']

/** Show the search input only once the library has enough entries that
 *  scanning by eye gets annoying. */
const SEARCH_THRESHOLD = 6

function iconBtnStyle(color: string): React.CSSProperties {
  return {
    width: 24,
    height: 24,
    border: '1px solid var(--line)',
    borderRadius: 6,
    background: 'var(--bg)',
    display: 'grid',
    placeItems: 'center',
    color,
    cursor: 'pointer',
    textDecoration: 'none',
  }
}

function fmtDur(seconds: number | null) {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m.toString().padStart(2, '0')}m`
  return `${m}m`
}

export function Library({
  entries,
  onPlay,
  onDelete,
  onRename,
}: {
  entries: LibraryEntry[]
  onPlay: (entry: LibraryEntry) => void
  onDelete: (entry: LibraryEntry) => void
  onRename: (entry: LibraryEntry, newStem: string) => Promise<void>
}) {
  const [query, setQuery] = useState('')
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const showSearch = entries.length >= SEARCH_THRESHOLD

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return entries
    return entries.filter(e =>
      (e.title?.toLowerCase().includes(q) ?? false) ||
      e.name.toLowerCase().includes(q) ||
      (e.author?.toLowerCase().includes(q) ?? false),
    )
  }, [entries, query])

  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 8,
          paddingLeft: 4,
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: 'var(--dim)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}
        >
          Library
        </div>
        {showSearch && (
          <input
            type="search"
            placeholder="Filter…"
            aria-label="Filter library"
            value={query}
            onChange={e => setQuery(e.target.value)}
            style={{
              fontFamily: 'inherit',
              fontSize: 11,
              color: 'var(--ink)',
              background: 'var(--bg-soft)',
              border: '1px solid var(--line)',
              borderRadius: 6,
              padding: '3px 8px',
              outline: 'none',
              width: 120,
            }}
          />
        )}
      </div>
      <div
        style={{
          border: '1px solid var(--line)',
          borderRadius: 12,
          background: 'var(--bg)',
          overflow: 'hidden',
        }}
      >
        {entries.length === 0 ? (
          <div style={{ padding: 16, color: 'var(--dim)', fontSize: 12, textAlign: 'center' }}>
            No saved audiobooks yet.
          </div>
        ) : visible.length === 0 ? (
          <div style={{ padding: 16, color: 'var(--dim)', fontSize: 12, textAlign: 'center' }}>
            No matches for "{query}".
          </div>
        ) : (
          visible.map((r, i) => (
            <div
              key={r.id}
              role="button"
              tabIndex={0}
              aria-label={`Play ${r.title || r.name}`}
              onClick={() => onPlay(r)}
              onKeyDown={e => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onPlay(r)
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: 12,
                borderBottom: i < visible.length - 1 ? '1px solid var(--line)' : 'none',
                cursor: 'pointer',
              }}
            >
              {r.cover_url ? (
                <img
                  src={r.cover_url}
                  alt=""
                  style={{
                    width: 28,
                    height: 36,
                    objectFit: 'cover',
                    borderRadius: 4,
                    flexShrink: 0,
                  }}
                />
              ) : (
                <div
                  style={{
                    width: 28,
                    height: 36,
                    borderRadius: 4,
                    background: SPINE_COLORS[i % SPINE_COLORS.length],
                    flexShrink: 0,
                  }}
                />
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                {renamingId === r.id ? (
                  <RenameField
                    initial={stemOf(r.name)}
                    onCancel={() => setRenamingId(null)}
                    onSubmit={async value => {
                      await onRename(r, value)
                      setRenamingId(null)
                    }}
                  />
                ) : (
                  <div
                    onDoubleClick={e => {
                      e.stopPropagation()
                      setRenamingId(r.id)
                    }}
                    title="Double-click to rename"
                    style={{
                      fontSize: 12.5,
                      fontWeight: 500,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {r.title || r.name}
                  </div>
                )}
                <div className="mono" style={{ fontSize: 11, color: 'var(--dim)', marginTop: 2 }}>
                  {fmtDur(r.duration_s)}
                </div>
              </div>
              <span style={{ display: 'flex', gap: 6, flexShrink: 0 }} onClick={e => e.stopPropagation()}>
                <a
                  href={r.audio_url}
                  download={r.name}
                  aria-label={`Download ${r.name}`}
                  title={`Download ${r.name}`}
                  style={iconBtnStyle('var(--dim)')}
                >
                  <svg width="10" height="10" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M7 1v9M3.5 6.5L7 10l3.5-3.5M2 12.5h10" />
                  </svg>
                </a>
                <button
                  onClick={() => onPlay(r)}
                  aria-label={`Play ${r.name}`}
                  title={`Play ${r.name}`}
                  style={iconBtnStyle('var(--ink)')}
                >
                  <svg width="9" height="9" viewBox="0 0 9 9" fill="currentColor" aria-hidden="true">
                    <path d="M2 1l5 3.5L2 8z" />
                  </svg>
                </button>
                <button
                  onClick={() => setRenamingId(r.id)}
                  aria-label={`Rename ${r.name}`}
                  title={`Rename ${r.name}`}
                  style={iconBtnStyle('var(--dim)')}
                >
                  <svg width="10" height="10" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M9.5 2l2.5 2.5-7 7H2.5V9l7-7zM8.5 3l2.5 2.5" />
                  </svg>
                </button>
                <button
                  onClick={() => onDelete(r)}
                  aria-label={`Delete ${r.name}`}
                  title={`Delete ${r.name}`}
                  style={iconBtnStyle('var(--dim)')}
                >
                  <svg width="10" height="10" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true">
                    <path d="M3 4h8M5.5 4V2.5h3V4M4 4l.5 8.5h5L10 4" />
                  </svg>
                </button>
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function stemOf(filename: string): string {
  const dot = filename.lastIndexOf('.')
  return dot > 0 ? filename.slice(0, dot) : filename
}

function RenameField({
  initial,
  onSubmit,
  onCancel,
}: {
  initial: string
  onSubmit: (value: string) => Promise<void>
  onCancel: () => void
}) {
  const [value, setValue] = useState(initial)
  const [busy, setBusy] = useState(false)
  return (
    <input
      autoFocus
      type="text"
      value={value}
      disabled={busy}
      aria-label="Rename audiobook"
      onChange={e => setValue(e.target.value)}
      onClick={e => e.stopPropagation()}
      onKeyDown={async e => {
        e.stopPropagation()
        if (e.key === 'Escape') {
          e.preventDefault()
          onCancel()
        } else if (e.key === 'Enter') {
          e.preventDefault()
          const trimmed = value.trim()
          if (!trimmed || trimmed === initial) {
            onCancel()
            return
          }
          setBusy(true)
          try {
            await onSubmit(trimmed)
          } catch {
            setBusy(false)
          }
        }
      }}
      onBlur={async () => {
        const trimmed = value.trim()
        if (!trimmed || trimmed === initial) {
          onCancel()
          return
        }
        setBusy(true)
        try {
          await onSubmit(trimmed)
        } catch {
          setBusy(false)
        }
      }}
      style={{
        fontSize: 12.5,
        fontWeight: 500,
        fontFamily: 'inherit',
        color: 'var(--ink)',
        background: 'var(--bg-soft)',
        border: '1px solid var(--accent)',
        borderRadius: 4,
        padding: '2px 6px',
        outline: 'none',
        width: '100%',
      }}
    />
  )
}
