import { useRef, useState } from 'react'

type Props = {
  onPick: (file: File) => void
  accept?: string
}

export function Dropzone({
  onPick,
  accept = '.pdf,.epub,.md,.txt,.html,.htm,.docx,.rtf,.fb2',
}: Props) {
  const [drag, setDrag] = useState(false)
  const ref = useRef<HTMLInputElement>(null)
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
      onClick={() => ref.current?.click()}
      style={{
        border: '1px dashed ' + (drag ? 'var(--accent)' : 'var(--line-strong)'),
        borderRadius: 12,
        padding: 48,
        textAlign: 'center',
        background: drag ? 'color-mix(in srgb, var(--accent) 5%, var(--bg))' : 'var(--bg-soft)',
        cursor: 'pointer',
        transition: 'all .15s',
      }}
    >
      <input
        ref={ref}
        type="file"
        hidden
        accept={accept}
        onChange={e => {
          const f = e.target.files?.[0]
          if (f) onPick(f)
        }}
      />
      <div
        style={{
          width: 40,
          height: 40,
          margin: '0 auto 14px',
          borderRadius: 10,
          background: 'var(--bg)',
          border: '1px solid var(--line)',
          display: 'grid',
          placeItems: 'center',
          color: 'var(--ink)',
        }}
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M9 12V3M5 7l4-4 4 4M3 14h12" />
        </svg>
      </div>
      <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 4 }}>Drop a file or click to browse</div>
      <div style={{ color: 'var(--dim)', fontSize: 13 }}>
        PDF, EPUB, DOCX, RTF, FB2, Markdown, TXT, HTML up to 200 MB
      </div>
      <div
        style={{ marginTop: 20, display: 'flex', gap: 8, justifyContent: 'center' }}
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={() => ref.current?.click()}
          style={{
            background: 'var(--ink)',
            color: 'var(--bg)',
            border: 0,
            borderRadius: 7,
            padding: '8px 14px',
            fontSize: 13,
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          Browse files
          <span
            className="mono"
            style={{
              background: 'color-mix(in srgb, var(--bg) 15%, transparent)',
              padding: '1px 5px',
              borderRadius: 3,
              fontSize: 11,
            }}
          >
            ⌘O
          </span>
        </button>
      </div>
    </div>
  )
}
