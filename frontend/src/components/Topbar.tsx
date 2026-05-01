import type { Theme } from '../hooks/useTheme'

export function Topbar({ theme, setTheme }: { theme: Theme; setTheme: (t: Theme) => void }) {
  const next: Theme = theme === 'dark' ? 'light' : 'dark'
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
      <button
        onClick={() => setTheme(next)}
        title={`Switch to ${next} mode`}
        style={{
          width: 28,
          height: 28,
          display: 'grid',
          placeItems: 'center',
          border: '1px solid var(--line)',
          borderRadius: 6,
          background: 'transparent',
          color: 'var(--dim)',
          cursor: 'pointer',
          fontSize: 13,
          padding: 0,
        }}
      >
        {theme === 'dark' ? '☀' : '☾'}
      </button>
    </header>
  )
}
