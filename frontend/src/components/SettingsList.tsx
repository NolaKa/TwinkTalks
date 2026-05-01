import type { Format, Language, Settings } from '../types'

type Props = {
  settings: Settings
  onChange: (next: Partial<Settings>) => void
  languages: Language[]
  advancedOpen: boolean
  onToggleAdvanced: () => void
}

const FORMATS: Array<{ id: Format; label: string }> = [
  { id: 'wav', label: 'WAV' },
  { id: 'mp3', label: 'MP3' },
  { id: 'm4b', label: 'M4B' },
]

export function SettingsList(props: Props) {
  const { settings, onChange, languages, advancedOpen, onToggleAdvanced } = props

  return (
    <div
      style={{
        border: '1px solid var(--line)',
        borderRadius: 12,
        background: 'var(--bg)',
        overflow: 'hidden',
      }}
    >
      <Row label="Language">
        <select
          value={settings.language}
          onChange={e => onChange({ language: e.target.value })}
          style={selectStyle}
        >
          {languages.map(l => (
            <option key={l.id} value={l.id}>{l.name}</option>
          ))}
        </select>
      </Row>

      <Row label="Speed">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 180 }}>
          <input
            type="range"
            min={0.5}
            max={2.0}
            step={0.05}
            value={settings.speed}
            onChange={e => onChange({ speed: parseFloat(e.target.value) })}
            style={{ flex: 1, accentColor: 'var(--ink)' }}
          />
          <span className="mono" style={{ minWidth: 44, textAlign: 'right', color: 'var(--ink)' }}>
            {settings.speed.toFixed(2)}×
          </span>
        </div>
      </Row>

      <Row label="Format">
        <div
          style={{
            display: 'inline-flex',
            border: '1px solid var(--line)',
            borderRadius: 6,
            padding: 2,
            gap: 0,
          }}
        >
          {FORMATS.map(f => {
            const active = settings.format === f.id
            return (
              <button
                key={f.id}
                onClick={() => onChange({ format: f.id })}
                style={{
                  border: 0,
                  background: active ? 'var(--bg-soft-2)' : 'transparent',
                  color: active ? 'var(--ink)' : 'var(--dim)',
                  padding: '4px 10px',
                  borderRadius: 4,
                  fontSize: 12,
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer',
                  fontWeight: active ? 500 : 400,
                }}
              >
                {f.label}
              </button>
            )
          })}
        </div>
      </Row>

      <ToggleRow
        label="Chapter markers"
        on={settings.chapter_markers}
        onChange={() => onChange({ chapter_markers: !settings.chapter_markers })}
      />
      <ToggleRow
        label="OCR fallback"
        on={settings.ocr}
        onChange={() => onChange({ ocr: !settings.ocr })}
        last
      />

      <button
        onClick={onToggleAdvanced}
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
        {advancedOpen ? '−' : '+'} Advanced (OCR language, skip rules, merge chapters)
      </button>

      {advancedOpen && (
        <div
          style={{
            padding: 16,
            borderTop: '1px solid var(--line)',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          <Field label="OCR language">
            <input
              type="text"
              value={settings.ocr_language}
              onChange={e => onChange({ ocr_language: e.target.value })}
              placeholder="auto / eng / pol / chi_sim / ..."
              style={inputStyle}
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

// --- Row primitives ----------------------------------------------------------

function Row({
  label, children, last,
}: { label: string; children: React.ReactNode; last?: boolean }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 16px',
        borderBottom: last ? 'none' : '1px solid var(--line)',
        gap: 12,
      }}
    >
      <span style={{ fontSize: 13, color: 'var(--ink)' }}>{label}</span>
      {children}
    </div>
  )
}

function ToggleRow({
  label, on, onChange, last,
}: { label: string; on: boolean; onChange: () => void; last?: boolean }) {
  return (
    <button
      onClick={onChange}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 16px',
        borderBottom: last ? 'none' : '1px solid var(--line)',
        border: 'none',
        background: 'transparent',
        color: 'var(--ink)',
        fontFamily: 'inherit',
        fontSize: 13,
        cursor: 'pointer',
        textAlign: 'left',
      }}
    >
      <span>{label}</span>
      <span
        style={{
          fontSize: 13,
          color: on ? 'var(--ink)' : 'var(--dim)',
          fontWeight: on ? 500 : 400,
        }}
      >
        {on ? 'On' : 'Off'}
      </span>
    </button>
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

// --- Shared styles -----------------------------------------------------------

const inputStyle: React.CSSProperties = {
  width: '100%',
  background: 'var(--bg-soft)',
  border: '1px solid var(--line)',
  borderRadius: 6,
  padding: '8px 10px',
  color: 'var(--ink)',
  fontFamily: 'inherit',
  fontSize: 13,
  outline: 'none',
}

const selectStyle: React.CSSProperties = {
  border: 'none',
  background: 'transparent',
  color: 'var(--dim)',
  fontSize: 13,
  fontFamily: 'inherit',
  cursor: 'pointer',
  padding: 0,
  outline: 'none',
  textAlign: 'right',
}
