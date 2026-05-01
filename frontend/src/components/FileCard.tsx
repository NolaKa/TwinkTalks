import type { FileMetadata } from '../types'

function fmtBytes(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

function fmtDuration(seconds: number) {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `~${h}h ${m.toString().padStart(2, '0')}m audio`
  return `~${m}m audio`
}

function pluralUnit(n: number, ext: string) {
  if (ext === '.pdf') return n === 1 ? '1 page' : `${n.toLocaleString()} pages`
  if (ext === '.epub') return n === 1 ? '1 chapter' : `${n} chapters`
  return ''
}

export function FileCard({ file, onReplace }: { file: FileMetadata; onReplace: () => void }) {
  const ext = (file.name.split('.').pop() || '').toUpperCase()
  return (
    <div
      style={{
        border: '1px solid var(--line)',
        borderRadius: 12,
        background: 'var(--bg)',
        padding: 16,
        display: 'flex',
        alignItems: 'center',
        gap: 14,
      }}
    >
      <div
        style={{
          width: 44,
          height: 56,
          borderRadius: 6,
          flexShrink: 0,
          background: 'var(--bg-soft-2)',
          border: '1px solid var(--line)',
          display: 'grid',
          placeItems: 'center',
          fontSize: 10,
          fontWeight: 600,
          color: 'var(--dim)',
          letterSpacing: '0.06em',
        }}
      >
        {ext}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 13.5,
            fontWeight: 500,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {file.title || file.name}
        </div>
        <div className="mono" style={{ display: 'flex', gap: 14, fontSize: 11, color: 'var(--dim)', marginTop: 4 }}>
          <span>{fmtBytes(file.size_bytes)}</span>
          {pluralUnit(file.item_count, file.ext) && <span>{pluralUnit(file.item_count, file.ext)}</span>}
          {file.word_count > 0 && <span>{file.word_count.toLocaleString()} words</span>}
          {file.est_duration_s > 0 && (
            <span style={{ color: 'var(--ink)' }}>{fmtDuration(file.est_duration_s)}</span>
          )}
        </div>
      </div>
      <button
        onClick={onReplace}
        style={{
          background: 'transparent',
          border: '1px solid var(--line)',
          borderRadius: 6,
          padding: '6px 12px',
          fontSize: 12,
          color: 'var(--dim)',
        }}
      >
        Replace
      </button>
    </div>
  )
}
