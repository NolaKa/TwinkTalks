import type { Theme } from '../hooks/useTheme'

type Props = {
  theme: Theme
  setTheme: (t: Theme) => void
}

export function Hero({ theme, setTheme }: Props) {
  const next: Theme = theme === 'dark' ? 'light' : 'dark'
  return (
    <div style={{ marginBottom: 56 }}>
      <div className="mono" style={{ fontSize: 12, color: 'var(--dim)', marginBottom: 16 }}>
        ~/twinktalks · v0.5.0
      </div>
      <h1
        style={{
          margin: 0,
          fontSize: 56,
          lineHeight: 1.05,
          letterSpacing: '-0.035em',
          fontWeight: 600,
          maxWidth: 720,
        }}
      >
        Turn your reading list into <span style={{ color: 'var(--dim)' }}>an audiobook.</span>
        <button
          onClick={() => setTheme(next)}
          aria-label={`Switch to ${next} theme`}
          title={`Switch to ${next} mode`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 28,
            height: 28,
            marginLeft: 16,
            border: '1px solid var(--line)',
            borderRadius: 6,
            background: 'transparent',
            color: 'var(--dim)',
            fontSize: 13,
            fontWeight: 400,
            verticalAlign: 'middle',
            padding: 0,
            cursor: 'pointer',
            transition: 'border-color 150ms ease, color 150ms ease',
          }}
        >
          {theme === 'dark' ? '☀' : '☾'}
        </button>
      </h1>
      <p style={{ marginTop: 16, fontSize: 16, color: 'var(--dim)', maxWidth: 540 }}>
        Drop a PDF, EPUB, Markdown, or HTML file. Pick a voice. Get a clean audio file with chapter markers, ready for any player.
      </p>
    </div>
  )
}
