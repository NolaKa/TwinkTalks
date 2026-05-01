import type { Preset } from '../types'

type Props = {
  presets: { builtin: Preset[]; user: Preset[] }
  instruct: string
  saveName: string
  onInstructChange: (v: string) => void
  onSaveNameChange: (v: string) => void
  onApplyPreset: (preset: Preset) => void
  onSavePreset: (name: string) => void
  onDeletePreset: (name: string) => void
}

export function VoiceStyleControls(props: Props) {
  const {
    presets, instruct, saveName,
    onInstructChange, onSaveNameChange,
    onApplyPreset, onSavePreset, onDeletePreset,
  } = props
  const all = [...presets.builtin, ...presets.user]
  const canSave = saveName.trim().length > 0

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Voice style</div>
      <div style={{ fontSize: 12, color: 'var(--dim)', marginBottom: 12 }}>
        Apply a saved preset, or describe how the voice should sound.
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <select
          value=""
          onChange={e => {
            const p = all.find(pp => pp.name === e.target.value)
            if (p) onApplyPreset(p)
            e.target.value = ''
          }}
          style={{ ...inputStyle, flex: 1 }}
        >
          <option value="">Apply a preset…</option>
          {presets.builtin.length > 0 && (
            <optgroup label="Built-in">
              {presets.builtin.map(p => (
                <option key={p.name} value={p.name}>{p.name}</option>
              ))}
            </optgroup>
          )}
          {presets.user.length > 0 && (
            <optgroup label="My presets">
              {presets.user.map(p => (
                <option key={p.name} value={p.name}>★ {p.name}</option>
              ))}
            </optgroup>
          )}
        </select>
        <input
          type="text"
          value={saveName}
          onChange={e => onSaveNameChange(e.target.value)}
          placeholder="Save current as…"
          style={{ ...inputStyle, flex: 1 }}
        />
        <button
          onClick={() => canSave && onSavePreset(saveName.trim())}
          disabled={!canSave}
          style={{
            border: 'none',
            background: canSave ? 'var(--ink)' : 'var(--bg-soft-2)',
            color: canSave ? 'var(--bg)' : 'var(--dim)',
            borderRadius: 6,
            padding: '8px 14px',
            fontSize: 13,
            fontWeight: 500,
            cursor: canSave ? 'pointer' : 'not-allowed',
            fontFamily: 'inherit',
          }}
        >
          Save
        </button>
      </div>

      <textarea
        value={instruct}
        onChange={e => onInstructChange(e.target.value)}
        placeholder="e.g. Speak calmly like an audiobook narrator"
        rows={2}
        style={{ ...inputStyle, resize: 'vertical' }}
      />

      {presets.user.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {presets.user.map(p => (
            <div
              key={p.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                fontSize: 12,
                background: 'var(--bg-soft)',
                borderRadius: 6,
              }}
            >
              <span>★ {p.name}</span>
              <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="mono" style={{ color: 'var(--dim)', fontSize: 11 }}>
                  {p.speaker} · {p.speed.toFixed(2)}×
                </span>
                <button
                  onClick={() => onDeletePreset(p.name)}
                  title="Delete preset"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--dim)',
                    cursor: 'pointer',
                    padding: 2,
                    fontSize: 14,
                    lineHeight: 1,
                  }}
                >
                  ×
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

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
