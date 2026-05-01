import { useState } from 'react'
import type { Settings } from '../types'

type Props = {
  settings: Settings
  onChange: (next: Partial<Settings>) => void
  languageDisplay: string
  formatDisplay: string
}

export function SettingsList({ settings, onChange, languageDisplay, formatDisplay }: Props) {
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const rows: Array<{ label: string; value: React.ReactNode; chev?: boolean; onClick?: () => void }> = [
    {
      label: 'Language',
      value: languageDisplay,
      chev: true,
      onClick: () => {
        const next = prompt('Language id (auto, English, German, ...)', settings.language)
        if (next) onChange({ language: next })
      },
    },
    {
      label: 'Speed',
      value: `${settings.speed.toFixed(2)}×`,
      chev: true,
      onClick: () => {
        const next = parseFloat(prompt('Speed 0.5 – 2.0', String(settings.speed)) || '')
        if (!Number.isNaN(next) && next >= 0.5 && next <= 2.0) onChange({ speed: next })
      },
    },
    {
      label: 'Format',
      value: formatDisplay,
      chev: true,
      onClick: () => {
        const next = prompt('Format: wav, mp3, m4b', settings.format) as Settings['format'] | null
        if (next === 'wav' || next === 'mp3' || next === 'm4b') onChange({ format: next })
      },
    },
    {
      label: 'Chapter markers',
      value: settings.chapter_markers ? 'Embedded' : 'Off',
      onClick: () => onChange({ chapter_markers: !settings.chapter_markers }),
    },
    {
      label: 'OCR fallback',
      value: settings.ocr ? 'On' : 'Off',
      onClick: () => onChange({ ocr: !settings.ocr }),
    },
  ]

  return (
    <div
      style={{
        border: '1px solid var(--line)',
        borderRadius: 12,
        background: 'var(--bg)',
        overflow: 'hidden',
      }}
    >
      {rows.map((row, i) => (
        <button
          key={row.label}
          onClick={row.onClick}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '14px 16px',
            borderBottom: i < rows.length - 1 ? '1px solid var(--line)' : 'none',
            border: 'none',
            background: 'transparent',
            cursor: row.onClick ? 'pointer' : 'default',
            color: 'var(--ink)',
            textAlign: 'left',
            fontFamily: 'inherit',
            fontSize: 13,
          }}
        >
          <span>{row.label}</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--dim)', fontSize: 13 }}>
            {row.value}
            {row.chev && <span style={{ color: 'var(--dim-2)' }}>⌄</span>}
          </span>
        </button>
      ))}
      <button
        onClick={() => setAdvancedOpen(o => !o)}
        style={{
          width: '100%',
          padding: '12px 16px',
          background: 'var(--bg-soft)',
          border: 0,
          borderTop: '1px solid var(--line)',
          color: 'var(--dim)',
          fontSize: 12,
          textAlign: 'left',
          cursor: 'pointer',
          fontFamily: 'inherit',
        }}
      >
        {advancedOpen ? '−' : '+'} Advanced (voice style, OCR language, batching)
      </button>
      {advancedOpen && (
        <div style={{ padding: '16px', borderTop: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Field label="Voice style instruct">
            <textarea
              value={settings.instruct}
              onChange={e => onChange({ instruct: e.target.value })}
              placeholder="e.g. Speak calmly like a narrator"
              rows={2}
              style={{
                width: '100%',
                resize: 'vertical',
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 6,
                padding: '8px 10px',
                color: 'var(--ink)',
                fontFamily: 'inherit',
                fontSize: 13,
              }}
            />
          </Field>
          <Field label="OCR language">
            <input
              type="text"
              value={settings.ocr_language}
              onChange={e => onChange({ ocr_language: e.target.value })}
              placeholder="auto / eng / pol / chi_sim / ..."
              style={{
                width: '100%',
                background: 'var(--bg-soft)',
                border: '1px solid var(--line)',
                borderRadius: 6,
                padding: '8px 10px',
                color: 'var(--ink)',
                fontFamily: 'inherit',
                fontSize: 13,
              }}
            />
          </Field>
          <CheckboxRow
            label="Skip references / bibliography"
            checked={settings.skip_references}
            onChange={v => onChange({ skip_references: v })}
          />
          <CheckboxRow
            label="Skip tables"
            checked={settings.skip_tables}
            onChange={v => onChange({ skip_tables: v })}
          />
          <CheckboxRow
            label="Merge all chapters into one audiobook"
            checked={settings.merge_chapters}
            onChange={v => onChange({ merge_chapters: v })}
          />
        </div>
      )}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={{ fontSize: 12, color: 'var(--dim)' }}>{label}</span>
      {children}
    </label>
  )
}

function CheckboxRow({
  label, checked, onChange,
}: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      {label}
    </label>
  )
}
