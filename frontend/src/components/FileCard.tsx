import { useState } from 'react'
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

type Props = {
  file: FileMetadata
  onReplace: () => void
  onPick: (file: File) => void  // accept a fresh drop on the card itself
  onPreviewText: () => void
  /** Speed slider value — duration estimate scales by 1/speed. Defaults to 1.0. */
  speedFactor?: number
}

export function FileCard({ file, onReplace, onPick, onPreviewText, speedFactor = 1 }: Props) {
  const adjustedDuration =
    file.est_duration_s > 0 && speedFactor > 0
      ? file.est_duration_s / speedFactor
      : file.est_duration_s
  const ext = (file.name.split('.').pop() || '').toUpperCase()
  const [drag, setDrag] = useState(false)
  return (
    <div
      onDragOver={e => {
        e.preventDefault()
        setDrag(true)
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => {
        e.preventDefault()
        setDrag(false)
        const f = e.dataTransfer.files[0]
        if (f) onPick(f)
      }}
      style={{
        border: '1px ' + (drag ? 'dashed var(--accent)' : 'solid var(--line)'),
        background: drag ? 'color-mix(in srgb, var(--accent) 5%, var(--bg))' : 'var(--bg)',
        borderRadius: 12,
        padding: 16,
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        transition: 'border-color 120ms ease, background 120ms ease',
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
          {adjustedDuration > 0 && (
            <span style={{ color: 'var(--ink)' }}>{fmtDuration(adjustedDuration)}</span>
          )}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
        <button
          onClick={onPreviewText}
          title="See the exact text TwinkTalks will read — citations stripped, references cut, etc."
          style={iconActionStyle}
        >
          Preview text
        </button>
        <button
          onClick={onReplace}
          title="Drop a new file on this card, or click to clear"
          style={iconActionStyle}
        >
          Replace
        </button>
      </div>
    </div>
  )
}

const iconActionStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid var(--line)',
  borderRadius: 6,
  padding: '6px 12px',
  fontSize: 12,
  color: 'var(--dim)',
  cursor: 'pointer',
  fontFamily: 'inherit',
  whiteSpace: 'nowrap',
}
