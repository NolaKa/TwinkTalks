import type { Format, Language, Settings } from '../types'
import { Tooltip } from './Tooltip'

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

const TIPS = {
  language:
    "Pick the language the document is written in, or leave Auto and TwinkTalks will detect it from the first few hundred characters.",
  speed:
    "Speaking rate. 1.00× is normal pace. 0.85× is good for dense academic text; 1.20× shaves time off podcast-style content.",
  format:
    "WAV is uncompressed (largest file). MP3 is the universal podcast format with chapter markers. M4B is the audiobook container that iOS Books and Apple Podcasts treat as a real audiobook.",
  chapter_markers:
    "Embed jump-to-chapter points based on the document's table of contents. Works in MP3 (ID3v2) and M4B (MP4 chapter atoms). Has no effect for documents without a TOC.",
  merge_chapters:
    "When ON, every chapter from the table of contents is rendered into one combined audiobook file. When OFF (and you use the CLI's --chapters all), each chapter becomes its own file.",
  skip_references:
    "Drop the References / Bibliography section so the narration ends with the actual content instead of two hundred citations.",
  skip_tables:
    "Detect and skip tables, figures, and diagram captions — useful for textbooks where tables don't read well as speech.",
  force_ocr:
    "Force OCR on every PDF, including ones that already have a text layer. Normally TwinkTalks decides automatically based on whether text can be extracted.",
  ocr_language:
    "Tesseract language pack(s) for OCR. 'auto' joins every pack you have installed via brew tesseract-lang. Override with codes like 'eng', 'pol', 'eng+jpn'.",
}

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
      {/* Language is only worth showing when the active backend supports more
          than one. Kokoro is English-only and returns just one entry, so we
          hide the row instead of forcing the user to confirm "English" on
          every run. */}
      {languages.length > 1 && (
        <Row label="Language" tip={TIPS.language}>
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
      )}

      <Row label="Speed" tip={TIPS.speed}>
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

      <Row label="Format" tip={TIPS.format}>
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
        tip={TIPS.chapter_markers}
        on={settings.chapter_markers}
        onChange={() => onChange({ chapter_markers: !settings.chapter_markers })}
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
        {advancedOpen ? '−' : '+'} Advanced (skip rules, OCR, merge chapters)
      </button>

      {advancedOpen && (
        <div
          style={{
            padding: 16,
            borderTop: '1px solid var(--line)',
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
          }}
        >
          <CheckboxRow
            label="Skip references / bibliography"
            tip={TIPS.skip_references}
            checked={settings.skip_references}
            onChange={v => onChange({ skip_references: v })}
          />
          <CheckboxRow
            label="Skip tables and diagrams"
            tip={TIPS.skip_tables}
            checked={settings.skip_tables}
            onChange={v => onChange({ skip_tables: v })}
          />
          <CheckboxRow
            label="Combine chapters into a single audiobook file"
            tip={TIPS.merge_chapters}
            checked={settings.merge_chapters}
            onChange={v => onChange({ merge_chapters: v })}
          />
          <CheckboxRow
            label="Force OCR on every PDF"
            tip={TIPS.force_ocr}
            checked={settings.ocr}
            onChange={v => onChange({ ocr: v })}
          />
          <Field label="OCR language" tip={TIPS.ocr_language}>
            <input
              type="text"
              value={settings.ocr_language}
              onChange={e => onChange({ ocr_language: e.target.value })}
              placeholder="auto / eng / pol / chi_sim / ..."
              style={inputStyle}
            />
          </Field>
        </div>
      )}
    </div>
  )
}

// --- Row primitives ----------------------------------------------------------

function Row({
  label, tip, children, last,
}: {
  label: string
  tip?: string
  children: React.ReactNode
  last?: boolean
}) {
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
      <span style={{ fontSize: 13, color: 'var(--ink)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {label}
        {tip && <Tooltip text={tip} />}
      </span>
      {children}
    </div>
  )
}

function ToggleRow({
  label, tip, on, onChange, last,
}: {
  label: string
  tip?: string
  on: boolean
  onChange: () => void
  last?: boolean
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 16px',
        borderBottom: last ? 'none' : '1px solid var(--line)',
      }}
    >
      <span style={{ fontSize: 13, color: 'var(--ink)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {label}
        {tip && <Tooltip text={tip} />}
      </span>
      <button
        onClick={onChange}
        style={{
          border: 'none',
          background: 'transparent',
          color: on ? 'var(--ink)' : 'var(--dim)',
          fontWeight: on ? 500 : 400,
          fontSize: 13,
          cursor: 'pointer',
          fontFamily: 'inherit',
          padding: 0,
        }}
      >
        {on ? 'On' : 'Off'}
      </button>
    </div>
  )
}

function Field({
  label, tip, children,
}: { label: string; tip?: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={{ fontSize: 12, color: 'var(--dim)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {label}
        {tip && <Tooltip text={tip} />}
      </span>
      {children}
    </label>
  )
}

function CheckboxRow({
  label, tip, checked, onChange,
}: { label: string; tip?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {label}
        {tip && <Tooltip text={tip} />}
      </span>
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
