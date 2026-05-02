import { useEffect, useRef, useState, type RefObject } from 'react'

type Props = {
  /** Lifted up so callers can imperatively assign .src + .play() the same
   *  way they did with the native <audio>. The player reads state via
   *  native events ('timeupdate', 'play', 'pause', 'loadedmetadata', etc.). */
  audioRef: RefObject<HTMLAudioElement | null>
  /** What's currently loaded — drives the title strip + download link. */
  current: { url: string; name: string } | null
}

const SPEEDS = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

/** Custom audio player — wraps a hidden <audio> and reflects its state
 *  through tokens-styled controls. Same imperative interface as the
 *  native element (callers .src and .play() through audioRef). */
export function AudioPlayer({ audioRef, current }: Props) {
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [rate, setRate] = useState(1.0)
  const [volume, setVolume] = useState(1.0)

  // Subscribe to the audio element's events so React state mirrors the
  // playback state, even when callers mutate .src or .play() imperatively.
  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onTime = () => setTime(a.currentTime)
    const onMeta = () => setDuration(isFinite(a.duration) ? a.duration : 0)
    const onRate = () => setRate(a.playbackRate)
    const onVol = () => setVolume(a.volume)
    const onEnd = () => setPlaying(false)
    a.addEventListener('play', onPlay)
    a.addEventListener('pause', onPause)
    a.addEventListener('timeupdate', onTime)
    a.addEventListener('loadedmetadata', onMeta)
    a.addEventListener('durationchange', onMeta)
    a.addEventListener('ratechange', onRate)
    a.addEventListener('volumechange', onVol)
    a.addEventListener('ended', onEnd)
    return () => {
      a.removeEventListener('play', onPlay)
      a.removeEventListener('pause', onPause)
      a.removeEventListener('timeupdate', onTime)
      a.removeEventListener('loadedmetadata', onMeta)
      a.removeEventListener('durationchange', onMeta)
      a.removeEventListener('ratechange', onRate)
      a.removeEventListener('volumechange', onVol)
      a.removeEventListener('ended', onEnd)
    }
  }, [audioRef])

  // Persist volume across sessions — small UX win for nighttime listeners.
  const volRestored = useRef(false)
  useEffect(() => {
    const a = audioRef.current
    if (!a || volRestored.current) return
    const stored = parseFloat(localStorage.getItem('twink-audio-volume') ?? '')
    if (!isNaN(stored)) a.volume = Math.max(0, Math.min(1, stored))
    volRestored.current = true
  }, [audioRef])

  const togglePlay = () => {
    const a = audioRef.current
    if (!a || !a.src) return
    if (a.paused) a.play().catch(() => {})
    else a.pause()
  }

  const seek = (s: number) => {
    const a = audioRef.current
    if (!a) return
    a.currentTime = Math.max(0, Math.min(duration || a.duration || s, s))
  }

  const setSpeed = (r: number) => {
    if (audioRef.current) audioRef.current.playbackRate = r
  }

  const setVol = (v: number) => {
    const a = audioRef.current
    if (!a) return
    a.volume = v
    localStorage.setItem('twink-audio-volume', String(v))
  }

  const hasAudio = !!current
  const progressPct = duration > 0 ? (time / duration) * 100 : 0

  return (
    <div
      className="audio-player"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '10px 14px',
        border: '1px solid var(--line)',
        borderRadius: 10,
        background: hasAudio ? 'var(--bg)' : 'var(--bg-soft)',
        minHeight: 48,
        opacity: hasAudio ? 1 : 0.6,
        flexWrap: 'wrap',
      }}
    >
      <audio ref={audioRef} preload="metadata" style={{ display: 'none' }} />

      <button
        onClick={togglePlay}
        disabled={!hasAudio}
        aria-label={playing ? 'Pause' : 'Play'}
        title={playing ? 'Pause' : 'Play'}
        style={{
          flexShrink: 0,
          width: 32,
          height: 32,
          borderRadius: '50%',
          border: 'none',
          background: hasAudio ? 'var(--ink)' : 'var(--dim-2)',
          color: 'var(--bg)',
          display: 'grid',
          placeItems: 'center',
          cursor: hasAudio ? 'pointer' : 'not-allowed',
        }}
      >
        {playing ? (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden="true">
            <rect x="2" y="1.5" width="2" height="7" rx="0.5" />
            <rect x="6" y="1.5" width="2" height="7" rx="0.5" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden="true">
            <path d="M3 1.5l5.5 3.5L3 8.5z" />
          </svg>
        )}
      </button>

      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div
          style={{
            fontSize: 12,
            color: 'var(--ink)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {current?.name ?? 'No audio loaded yet'}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="mono" style={{ fontSize: 10, color: 'var(--dim)', minWidth: 32 }}>
            {fmt(time)}
          </span>
          <input
            type="range"
            min={0}
            max={duration || 1}
            step={0.1}
            value={time}
            disabled={!hasAudio || duration === 0}
            onChange={e => seek(parseFloat(e.target.value))}
            aria-label="Seek"
            style={{
              ...sliderStyle,
              // Custom track fill via gradient — works in webkit + firefox.
              background: hasAudio
                ? `linear-gradient(to right, var(--ink) 0%, var(--ink) ${progressPct}%, var(--line) ${progressPct}%, var(--line) 100%)`
                : 'var(--line)',
            }}
          />
          <span className="mono" style={{ fontSize: 10, color: 'var(--dim)', minWidth: 36, textAlign: 'right' }}>
            {fmt(duration)}
          </span>
        </div>
      </div>

      <select
        value={rate}
        onChange={e => setSpeed(parseFloat(e.target.value))}
        disabled={!hasAudio}
        aria-label="Playback speed"
        title="Playback speed"
        style={{
          flexShrink: 0,
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          color: 'var(--dim)',
          background: 'transparent',
          border: '1px solid var(--line)',
          borderRadius: 6,
          padding: '3px 6px',
          cursor: hasAudio ? 'pointer' : 'not-allowed',
        }}
      >
        {SPEEDS.map(s => (
          <option key={s} value={s}>{s.toFixed(2).replace(/\.?0+$/, '')}×</option>
        ))}
      </select>

      <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="var(--dim)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          {volume === 0 ? (
            <>
              <path d="M2 4.5v3h2L7 10V2L4 4.5H2z" fill="var(--dim)" />
              <path d="M9 4.5l2 3M11 4.5l-2 3" />
            </>
          ) : (
            <>
              <path d="M2 4.5v3h2L7 10V2L4 4.5H2z" fill="var(--dim)" />
              {volume > 0.5 && <path d="M9 3.5C10 4.5 10 7.5 9 8.5" />}
              {volume > 0 && <path d="M8 4.5C8.5 5 8.5 7 8 7.5" />}
            </>
          )}
        </svg>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={volume}
          onChange={e => setVol(parseFloat(e.target.value))}
          aria-label="Volume"
          style={{ ...sliderStyle, width: 60 }}
        />
      </div>

      {current && (
        <a
          href={current.url}
          download={current.name}
          aria-label={`Download ${current.name}`}
          title={`Download ${current.name}`}
          style={{
            flexShrink: 0,
            width: 28,
            height: 28,
            display: 'inline-grid',
            placeItems: 'center',
            border: '1px solid var(--line)',
            borderRadius: 6,
            color: 'var(--dim)',
            textDecoration: 'none',
          }}
        >
          <svg width="11" height="11" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M7 1v9M3.5 6.5L7 10l3.5-3.5M2 12.5h10" />
          </svg>
        </a>
      )}
    </div>
  )
}

function fmt(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return '0:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
}

const sliderStyle: React.CSSProperties = {
  flex: 1,
  height: 4,
  WebkitAppearance: 'none' as const,
  appearance: 'none' as const,
  borderRadius: 2,
  outline: 'none',
  cursor: 'pointer',
  margin: 0,
}
