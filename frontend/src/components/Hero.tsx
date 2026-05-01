export function Hero() {
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
      </h1>
      <p style={{ marginTop: 16, fontSize: 16, color: 'var(--dim)', maxWidth: 540 }}>
        Drop a PDF, EPUB, Markdown, or HTML file. Pick a voice. Get a clean audio file with chapter markers, ready for any player.
      </p>
    </div>
  )
}
