import { useEffect, useMemo, useState } from 'react'
import type { FileMetadata } from '../types'

type Range = { start: number | null; end: number | null }

type Props = {
  file: FileMetadata
  pageStart: number | null
  pageEnd: number | null
  onChange: (next: Range) => void
}

type Mode = 'whole' | 'pages' | 'chapter'

/** Lets the user pick whether to synthesize the whole document, a page
 *  range, or a single TOC chapter. Hidden entirely for short files
 *  (item_count <= 1) where there's nothing to slice. */
export function ScopePicker({ file, pageStart, pageEnd, onChange }: Props) {
  const [open, setOpen] = useState(false)

  // Derive the current mode from the live page range. If the range matches
  // exactly one TOC chapter, we render as 'chapter' (with that chapter
  // selected). Otherwise it's 'pages' or 'whole'.
  const matchedChapter = useMemo(() => {
    if (!pageStart || !pageEnd) return null
    return file.toc.find(c => c.start === pageStart && c.end === pageEnd) || null
  }, [pageStart, pageEnd, file.toc])

  const mode: Mode = !pageStart && !pageEnd
    ? 'whole'
    : matchedChapter ? 'chapter' : 'pages'

  // Local edit state for the Pages inputs so the user can type "1" then "10"
  // without us round-tripping a half-typed value through the parent.
  const [pagesStart, setPagesStart] = useState<number>(pageStart ?? 1)
  const [pagesEnd, setPagesEnd]     = useState<number>(pageEnd ?? file.item_count)
  useEffect(() => {
    if (pageStart) setPagesStart(pageStart)
    if (pageEnd)   setPagesEnd(pageEnd)
  }, [pageStart, pageEnd])

  if (file.item_count <= 1) return null

  const isPdf = file.ext === '.pdf'
  const unitWord = isPdf ? 'page' : 'item'

  const summary = mode === 'whole'
    ? `Whole ${isPdf ? 'document' : 'file'}`
    : mode === 'chapter'
      ? `Chapter: ${matchedChapter!.title}`
      : `${unitWord}s ${pageStart}–${pageEnd}`

  const setMode = (next: Mode) => {
    if (next === 'whole') {
      onChange({ start: null, end: null })
    } else if (next === 'pages') {
      onChange({ start: pagesStart, end: pagesEnd })
    } else {
      // Default chapter selection: first one in the TOC
      const ch = file.toc[0]
      if (ch) onChange({ start: ch.start, end: ch.end })
    }
  }

  return (
    <div style={{
      border: '1px solid var(--line)',
      borderRadius: 12,
      background: 'var(--bg)',
      overflow: 'hidden',
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 16px',
          background: 'transparent',
          border: 'none',
          color: 'var(--ink)',
          fontSize: 13,
          fontFamily: 'inherit',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span>Scope</span>
        <span style={{
          display: 'flex', alignItems: 'center', gap: 8,
          color: 'var(--dim)', fontSize: 13,
          maxWidth: '60%',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{summary}</span>
          <span
            style={{
              color: 'var(--dim-2)',
              transform: open ? 'rotate(180deg)' : 'none',
              transition: 'transform 150ms ease',
              display: 'inline-block',
            }}
          >⌄</span>
        </span>
      </button>

      {open && (
        <div style={{
          padding: 16,
          borderTop: '1px solid var(--line)',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}>
          <ModeRadio mode={mode} onChange={setMode} hasToc={file.toc.length > 0} />

          {mode === 'pages' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--dim)' }}>From</span>
              <input
                type="number"
                min={1}
                max={file.item_count}
                value={pagesStart}
                onChange={e => {
                  const v = Math.max(1, Math.min(file.item_count, parseInt(e.target.value) || 1))
                  setPagesStart(v)
                  onChange({ start: v, end: Math.max(v, pagesEnd) })
                  if (v > pagesEnd) setPagesEnd(v)
                }}
                style={numInputStyle}
              />
              <span style={{ fontSize: 12, color: 'var(--dim)' }}>to</span>
              <input
                type="number"
                min={pagesStart}
                max={file.item_count}
                value={pagesEnd}
                onChange={e => {
                  const v = Math.max(pagesStart, Math.min(file.item_count, parseInt(e.target.value) || pagesStart))
                  setPagesEnd(v)
                  onChange({ start: pagesStart, end: v })
                }}
                style={numInputStyle}
              />
              <span style={{ fontSize: 11, color: 'var(--dim-2)', marginLeft: 4 }}>
                of {file.item_count}
              </span>
            </div>
          )}

          {mode === 'chapter' && file.toc.length > 0 && (
            <select
              value={matchedChapter ? `${matchedChapter.start}-${matchedChapter.end}` : ''}
              onChange={e => {
                const [s, end] = e.target.value.split('-').map(Number)
                onChange({ start: s, end })
              }}
              style={{
                ...numInputStyle,
                width: '100%',
                cursor: 'pointer',
              }}
            >
              {file.toc.map((c, i) => (
                <option key={i} value={`${c.start}-${c.end}`}>
                  {'  '.repeat(Math.max(0, c.level - 1))}
                  {c.title} ({unitWord}s {c.start}–{c.end})
                </option>
              ))}
            </select>
          )}

          {mode === 'chapter' && file.toc.length === 0 && (
            <div style={{ fontSize: 12, color: 'var(--dim)' }}>
              This document has no detectable chapters. Try Page range instead.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ModeRadio({
  mode, onChange, hasToc,
}: { mode: Mode; onChange: (m: Mode) => void; hasToc: boolean }) {
  const opts: Array<{ id: Mode; label: string; disabled?: boolean }> = [
    { id: 'whole',   label: 'Whole document' },
    { id: 'pages',   label: 'Page range' },
    { id: 'chapter', label: 'Chapter', disabled: !hasToc },
  ]
  return (
    <div style={{
      display: 'inline-flex',
      border: '1px solid var(--line)',
      borderRadius: 6,
      padding: 2,
      alignSelf: 'flex-start',
    }}>
      {opts.map(o => {
        const active = mode === o.id
        return (
          <button
            key={o.id}
            onClick={() => !o.disabled && onChange(o.id)}
            disabled={o.disabled}
            title={o.disabled ? 'No table of contents in this file' : undefined}
            style={{
              border: 0,
              background: active ? 'var(--bg-soft-2)' : 'transparent',
              color: o.disabled ? 'var(--dim-2)' : (active ? 'var(--ink)' : 'var(--dim)'),
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 12,
              fontFamily: 'inherit',
              cursor: o.disabled ? 'not-allowed' : 'pointer',
              fontWeight: active ? 500 : 400,
            }}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

const numInputStyle: React.CSSProperties = {
  background: 'var(--bg-soft)',
  border: '1px solid var(--line)',
  borderRadius: 6,
  padding: '6px 10px',
  fontSize: 13,
  color: 'var(--ink)',
  fontFamily: 'inherit',
  outline: 'none',
  width: 70,
}
