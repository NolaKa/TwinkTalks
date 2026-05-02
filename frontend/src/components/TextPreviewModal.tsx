import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { FileMetadata, Settings } from '../types'

type Props = {
  file: FileMetadata
  settings: Settings
  onClose: () => void
}

type LoadState =
  | { status: 'loading' }
  | { status: 'ok'; text: string; word_count: number; char_count: number }
  | { status: 'error'; message: string }

/** Modal showing the exact text that will be sent to TTS — citations
 *  stripped, references cut, OCR applied — so the user can sanity-check
 *  before paying for a 30-minute synthesis. Uses the native <dialog>
 *  element for free ESC-to-close, focus trap, and backdrop. */
export function TextPreviewModal({ file, settings, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement | null>(null)
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  // Open the dialog imperatively so backdrop click and ESC work natively.
  useEffect(() => {
    const d = dialogRef.current
    if (!d) return
    if (!d.open) d.showModal()
    const onCancel = (e: Event) => {
      e.preventDefault()
      onClose()
    }
    d.addEventListener('cancel', onCancel)
    return () => {
      d.removeEventListener('cancel', onCancel)
      if (d.open) d.close()
    }
  }, [onClose])

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    api
      .preview(file.id, {
        skip_references: settings.skip_references,
        skip_tables: settings.skip_tables,
        page_start: settings.page_start,
        page_end: settings.page_end,
        ocr: settings.ocr,
        ocr_language: settings.ocr_language,
      })
      .then(r => {
        if (cancelled) return
        setState({ status: 'ok', ...r })
      })
      .catch(e => {
        if (cancelled) return
        const msg = e instanceof Error ? e.message : String(e)
        setState({ status: 'error', message: msg })
      })
    return () => {
      cancelled = true
    }
  }, [file.id, settings.skip_references, settings.skip_tables, settings.page_start, settings.page_end, settings.ocr, settings.ocr_language])

  return (
    <dialog
      ref={dialogRef}
      onClick={e => {
        // Click on the backdrop (the dialog element itself, not its content).
        if (e.target === dialogRef.current) onClose()
      }}
      style={{
        padding: 0,
        border: '1px solid var(--line)',
        borderRadius: 14,
        background: 'var(--bg)',
        color: 'var(--ink)',
        maxWidth: 720,
        width: '90vw',
        maxHeight: '85vh',
        overflow: 'hidden',
        boxShadow: '0 24px 64px rgba(0, 0, 0, 0.18)',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '85vh',
        }}
      >
        <header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            borderBottom: '1px solid var(--line)',
            flexShrink: 0,
          }}
        >
          <div>
            <div style={{ fontSize: 14, fontWeight: 500 }}>Text preview</div>
            <div style={{ fontSize: 11, color: 'var(--dim)', marginTop: 2 }}>
              {state.status === 'ok'
                ? `${state.word_count.toLocaleString()} words · ${state.char_count.toLocaleString()} characters`
                : 'What TwinkTalks will read aloud'}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close preview"
            style={{
              border: 'none',
              background: 'transparent',
              color: 'var(--dim)',
              fontSize: 20,
              lineHeight: 1,
              padding: 4,
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </header>

        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '20px 24px',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            lineHeight: 1.7,
            color: 'var(--ink)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {state.status === 'loading' && (
            <div style={{ color: 'var(--dim)', fontFamily: 'var(--font-sans)' }}>
              Extracting text…
            </div>
          )}
          {state.status === 'error' && (
            <div style={{ color: '#dc2626', fontFamily: 'var(--font-sans)', fontSize: 13 }}>
              Couldn't extract text: {state.message}
            </div>
          )}
          {state.status === 'ok' && (state.text.trim() ? state.text : (
            <div style={{ color: 'var(--dim)', fontFamily: 'var(--font-sans)' }}>
              No text extracted. Try enabling OCR if this is a scanned PDF.
            </div>
          ))}
        </div>

        <footer
          style={{
            padding: '12px 20px',
            borderTop: '1px solid var(--line)',
            fontSize: 11,
            color: 'var(--dim)',
            flexShrink: 0,
          }}
        >
          References, tables, and citations follow your Advanced settings. Edit those, then reopen this preview.
        </footer>
      </div>
    </dialog>
  )
}
