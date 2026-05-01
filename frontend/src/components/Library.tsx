import type { LibraryEntry } from '../types'

const SPINE_COLORS = ['#fef3c7', '#dbeafe', '#dcfce7', '#fce7f3', '#ede9fe', '#fee2e2']

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
}: {
  entries: LibraryEntry[]
  onPlay: (entry: LibraryEntry) => void
  onDelete: (entry: LibraryEntry) => void
}) {
  return (
    <div>
      <div
        style={{
          fontSize: 11,
          color: 'var(--dim)',
          marginBottom: 8,
          paddingLeft: 4,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}
      >
        Library
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
        ) : (
          entries.map((r, i) => (
            <div
              key={r.id}
              onClick={() => onPlay(r)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: 12,
                borderBottom: i < entries.length - 1 ? '1px solid var(--line)' : 'none',
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
                <div
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
                <div className="mono" style={{ fontSize: 11, color: 'var(--dim)', marginTop: 2 }}>
                  {fmtDur(r.duration_s)}
                </div>
              </div>
              <span style={{ display: 'flex', gap: 6, flexShrink: 0 }} onClick={e => e.stopPropagation()}>
                <a
                  href={r.audio_url}
                  download={r.name}
                  title={`Download ${r.name}`}
                  style={iconBtnStyle('var(--dim)')}
                >
                  <svg width="10" height="10" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M7 1v9M3.5 6.5L7 10l3.5-3.5M2 12.5h10" />
                  </svg>
                </a>
                <button
                  onClick={() => onPlay(r)}
                  title={`Play ${r.name}`}
                  style={iconBtnStyle('var(--ink)')}
                >
                  <svg width="9" height="9" viewBox="0 0 9 9" fill="currentColor">
                    <path d="M2 1l5 3.5L2 8z" />
                  </svg>
                </button>
                <button
                  onClick={() => onDelete(r)}
                  title={`Delete ${r.name}`}
                  style={iconBtnStyle('var(--dim)')}
                >
                  <svg width="10" height="10" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
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
