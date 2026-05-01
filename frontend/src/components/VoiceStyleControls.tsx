import { useState } from 'react'
import type { Preset } from '../types'

type Props = {
  presets: { builtin: Preset[]; user: Preset[] }
  instruct: string
  saveName: string
  supportsInstruct: boolean
  onInstructChange: (v: string) => void
  onSaveNameChange: (v: string) => void
  onApplyPreset: (preset: Preset) => void
  onSavePreset: (name: string) => void
  onDeletePreset: (name: string) => void
}

function summarizeInstruct(instruct: string): string {
  const trimmed = instruct.trim()
  if (!trimmed) return 'Default'
  if (trimmed.length <= 32) return trimmed
  return trimmed.slice(0, 32) + '…'
}

export function VoiceStyleControls(props: Props) {
  const {
    presets, instruct, saveName, supportsInstruct,
    onInstructChange, onSaveNameChange,
    onApplyPreset, onSavePreset, onDeletePreset,
  } = props
  const [open, setOpen] = useState(false)
  const all = [...presets.builtin, ...presets.user]
  const canSave = saveName.trim().length > 0

  return (
    <div
      style={{
        marginTop: 16,
        border: '1px solid var(--line)',
        borderRadius: 12,
        background: 'var(--bg)',
        overflow: 'hidden',
      }}
    >
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
        <span>Voice style</span>
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            color: 'var(--dim)',
            fontSize: 13,
            maxWidth: '60%',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {summarizeInstruct(instruct)}
          </span>
          <span
            style={{
              color: 'var(--dim-2)',
              transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 150ms ease',
              display: 'inline-block',
            }}
          >
            ⌄
          </span>
        </span>
      </button>

      {open && (
        <div
          style={{
            padding: 16,
            borderTop: '1px solid var(--line)',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <div style={{ display: 'flex', gap: 8 }}>
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

          {supportsInstruct ? (
            <textarea
              value={instruct}
              onChange={e => onInstructChange(e.target.value)}
              placeholder="e.g. Speak calmly like an audiobook narrator"
              rows={2}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          ) : (
            <div style={{ fontSize: 12, color: 'var(--dim)', padding: '8px 10px' }}>
              The active backend doesn't accept voice-style prompts — use a preset above
              or pick a different voice. Switch to the Qwen backend if you need this.
            </div>
          )}

          {presets.user.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
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
