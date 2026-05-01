import type { Theme } from '../types'

const THEMES: ReadonlyArray<[Theme, string]> = [
  ['light', '☀'],
  ['auto', '◐'],
  ['dark', '☾'],
]

export function Topbar({ theme, setTheme }: { theme: Theme; setTheme: (t: Theme) => void }) {
  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        background: 'color-mix(in srgb, var(--bg) 80%, transparent)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        borderBottom: '1px solid var(--line)',
        padding: '12px 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: 6,
            background:
              'linear-gradient(135deg, var(--ink), color-mix(in srgb, var(--ink) 60%, var(--bg)))',
            display: 'grid',
            placeItems: 'center',
            color: 'var(--bg)',
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '-0.04em',
          }}
        >
          tt
        </div>
        <span style={{ fontWeight: 600, letterSpacing: '-0.01em' }}>TwinkTalks</span>
        <span style={{ color: 'var(--dim-2)', fontSize: 12 }}>/</span>
        <span style={{ color: 'var(--dim)', fontSize: 12 }}>New session</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
        {['Docs', 'Library'].map(l => (
          <button
            key={l}
            style={{
              padding: '5px 10px',
              background: 'transparent',
              border: 0,
              color: 'var(--dim)',
              borderRadius: 5,
            }}
          >
            {l}
          </button>
        ))}
        <div style={{ width: 1, height: 16, background: 'var(--line)', margin: '0 4px' }} />
        <div
          style={{
            display: 'flex',
            border: '1px solid var(--line)',
            borderRadius: 6,
            padding: 2,
            fontSize: 11,
          }}
        >
          {THEMES.map(([v, s]) => (
            <button
              key={v}
              onClick={() => setTheme(v)}
              style={{
                padding: '3px 8px',
                border: 0,
                background: theme === v ? 'var(--bg-soft-2)' : 'transparent',
                borderRadius: 4,
                color: theme === v ? 'var(--ink)' : 'var(--dim)',
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
