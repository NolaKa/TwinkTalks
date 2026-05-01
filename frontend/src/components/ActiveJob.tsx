import type { ActiveJobInfo } from '../types'

function fmtEta(seconds: number) {
  if (!seconds || seconds <= 0) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

export function ActiveJob({ job }: { job: ActiveJobInfo | null }) {
  if (!job) {
    return (
      <div
        style={{
          border: '1px solid var(--line)',
          borderRadius: 12,
          background: 'var(--bg)',
          padding: 16,
          color: 'var(--dim)',
          fontSize: 12,
          textAlign: 'center',
        }}
      >
        No active job
      </div>
    )
  }

  const pct = job.total > 0 ? (job.current / job.total) * 100 : 0

  return (
    <div
      style={{
        border: '1px solid var(--line)',
        borderRadius: 12,
        background: 'var(--bg)',
        padding: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: 'var(--success)',
            boxShadow: '0 0 0 3px color-mix(in srgb, var(--success) 15%, transparent)',
          }}
        />
        <span style={{ fontSize: 12, fontWeight: 500 }}>Generating</span>
        <span className="mono" style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--dim)' }}>
          {job.current}/{job.total}
        </span>
      </div>
      <div
        style={{
          fontSize: 13.5,
          fontWeight: 500,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {job.filename}
      </div>
      <div style={{ fontSize: 12, color: 'var(--dim)', marginTop: 2 }}>
        chunk {job.current} · {job.duration_s.toFixed(1)}s rendered
      </div>
      <div
        style={{
          height: 4,
          background: 'var(--bg-soft)',
          borderRadius: 2,
          marginTop: 12,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: 'var(--ink)',
            borderRadius: 2,
            transition: 'width 300ms ease',
          }}
        />
      </div>
      <div
        className="mono"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: 6,
          fontSize: 11,
          color: 'var(--dim)',
        }}
      >
        <span>{Math.round(pct)}%</span>
        <span>~{fmtEta(job.eta_s)} left</span>
      </div>
    </div>
  )
}
