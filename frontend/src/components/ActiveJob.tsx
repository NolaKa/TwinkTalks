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

  // Phase 1: model loading — synthesis hasn't started yet.
  if (job.phase === 'loading_model') {
    const downloading = job.model_needs_download
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
          <Spinner />
          <span style={{ fontSize: 12, fontWeight: 500 }}>
            {downloading ? 'Downloading voice model' : 'Loading voice model'}
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
        <div style={{ fontSize: 12, color: 'var(--dim)', marginTop: 6, lineHeight: 1.5 }}>
          {downloading
            ? 'First-time setup — Qwen3-TTS weights are about 3.5 GB. This usually takes a few minutes; you only do it once. Synthesis starts as soon as the model is ready.'
            : 'Loading the voice model into memory — usually 10–30 seconds.'}
        </div>
        {/* Indeterminate progress bar */}
        <div
          style={{
            height: 4,
            background: 'var(--bg-soft)',
            borderRadius: 2,
            marginTop: 12,
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              width: '40%',
              background: 'var(--ink)',
              borderRadius: 2,
              animation: 'tt-indeterminate 1.4s ease-in-out infinite',
            }}
          />
        </div>
        <style>
          {`@keyframes tt-indeterminate {
              0%   { left: -40%; }
              100% { left: 100%; }
            }`}
        </style>
      </div>
    )
  }

  // Phase 2: synthesizing
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

function Spinner() {
  return (
    <span
      aria-hidden
      style={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        border: '1.5px solid var(--line-strong)',
        borderTopColor: 'var(--ink)',
        animation: 'tt-spin 0.9s linear infinite',
        display: 'inline-block',
      }}
    >
      <style>
        {`@keyframes tt-spin { to { transform: rotate(360deg); } }`}
      </style>
    </span>
  )
}
