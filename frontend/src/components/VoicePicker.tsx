import type { Voice } from '../types'

type Props = {
  voices: Voice[]
  value: string
  onChange: (id: string) => void
}

export function VoicePicker({ voices, value, onChange }: Props) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
      {voices.map(v => {
        const active = value === v.id
        return (
          <button
            key={v.id}
            onClick={() => onChange(v.id)}
            style={{
              border: '1px solid ' + (active ? 'var(--ink)' : 'var(--line)'),
              background: 'var(--bg)',
              borderRadius: 8,
              padding: '12px 14px',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              boxShadow: active ? '0 0 0 3px var(--bg-soft)' : 'none',
              transition: 'all .12s',
              color: 'var(--ink)',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: v.avatarColor,
                display: 'grid',
                placeItems: 'center',
                fontSize: 11,
                fontWeight: 600,
                color: '#5a3a2a',
                flexShrink: 0,
              }}
            >
              {v.name[0]}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{v.name}</div>
              <div style={{ fontSize: 11, color: 'var(--dim)' }}>{v.tag}</div>
            </div>
            {active && (
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)' }} />
            )}
          </button>
        )
      })}
    </div>
  )
}
