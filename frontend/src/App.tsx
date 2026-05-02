import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api/client'
import { ActiveJob } from './components/ActiveJob'
import { Dropzone } from './components/Dropzone'
import { FileCard } from './components/FileCard'
import { GenerateButton } from './components/GenerateButton'
import { Hero } from './components/Hero'
import { Library } from './components/Library'
import { ScopePicker } from './components/ScopePicker'
import { SettingsList } from './components/SettingsList'
import { VoicePicker } from './components/VoicePicker'
import { VoiceStyleControls } from './components/VoiceStyleControls'
import { useTheme } from './hooks/useTheme'
import {
  SUPPORTED_EXTENSIONS,
  type ActiveJobInfo,
  type BackendInfo,
  type FileMetadata,
  type Language,
  type LibraryEntry,
  type Preset,
  type Settings,
  type Voice,
} from './types'

const DEFAULT_SETTINGS: Settings = {
  voice_id: 'aiden',
  speed: 1.0,
  format: 'm4b',
  language: 'auto',
  instruct: '',
  skip_references: true,
  skip_tables: false,
  ocr: false,
  ocr_language: 'auto',
  chapter_markers: true,
  merge_chapters: false,
  page_start: null,
  page_end: null,
}

/** Heuristic count: a "short" file probably wants MP3, no merging. */
const SHORT_DOC_CHARS = 5000

export function App() {
  const [theme, setTheme] = useTheme()

  const [voices, setVoices] = useState<Voice[]>([])
  const [languages, setLanguages] = useState<Language[]>([])
  const [backends, setBackends] = useState<BackendInfo[]>([])
  const activeBackend = backends.find(b => b.is_current) ?? null
  const [presets, setPresets] = useState<{ builtin: Preset[]; user: Preset[] }>({ builtin: [], user: [] })
  const [library, setLibrary] = useState<LibraryEntry[]>([])

  const [file, setFile] = useState<FileMetadata | null>(null)
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  // Track whether the user has manually touched format / merge / ocr so we
  // don't override their choice when applying smart defaults from a new file.
  const userTouched = useRef<Set<keyof Settings>>(new Set())
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [activeJob, setActiveJob] = useState<ActiveJobInfo | null>(null)
  const [busy, setBusy] = useState(false)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentAudio, setCurrentAudio] = useState<{ url: string; name: string } | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  // Boot
  useEffect(() => {
    api.backends().then(setBackends).catch(() => {})
    api.voices().then(setVoices).catch(e => setError(prettyError(e)))
    api.languages().then(setLanguages).catch(() => {})
    api.presets().then(setPresets).catch(() => {})
    api.library().then(setLibrary).catch(() => {})
  }, [])

  // When the backend changes (e.g. switching from Qwen to Kokoro), reset
  // settings whose values aren't valid in the new list — voice_id and
  // language. Otherwise the user can carry "Polish" or "aiden" into a
  // Kokoro session and be silently misrouted.
  useEffect(() => {
    if (voices.length === 0) return
    setSettings(prev => {
      const stillValid = voices.some(v => v.id === prev.voice_id)
      if (stillValid) return prev
      return { ...prev, voice_id: voices[0].id }
    })
  }, [voices])

  useEffect(() => {
    if (languages.length === 0) return
    setSettings(prev => {
      const stillValid = languages.some(l => l.id === prev.language)
      if (stillValid) return prev
      return { ...prev, language: languages[0].id }
    })
  }, [languages])

  useEffect(() => () => eventSourceRef.current?.close(), [])

  /** Apply heuristic defaults the user hasn't manually overridden. */
  const applySmartDefaults = useCallback((meta: FileMetadata) => {
    setSettings(prev => {
      const next = { ...prev }
      const hasToc = meta.toc.length > 0
      const looksShort =
        meta.word_count > 0 && meta.word_count * 6 < SHORT_DOC_CHARS

      if (!userTouched.current.has('format')) {
        next.format = hasToc && !looksShort ? 'm4b' : 'mp3'
      }
      if (!userTouched.current.has('merge_chapters')) {
        next.merge_chapters = hasToc && !looksShort
      }
      if (!userTouched.current.has('ocr')) {
        next.ocr = meta.needs_ocr
      }
      return next
    })
  }, [])

  const updateSettings = useCallback((patch: Partial<Settings>) => {
    for (const key of Object.keys(patch) as (keyof Settings)[]) {
      userTouched.current.add(key)
    }
    setSettings(prev => ({ ...prev, ...patch }))
  }, [])

  const handleUpload = useCallback(async (raw: File) => {
    setError(null)
    // Reject unsupported file types client-side so the user sees a clear,
    // friendly message instead of a raw 415 from the server.
    const lower = raw.name.toLowerCase()
    const ext = lower.includes('.') ? lower.slice(lower.lastIndexOf('.')) : ''
    if (!SUPPORTED_EXTENSIONS.includes(ext as typeof SUPPORTED_EXTENSIONS[number])) {
      setError(
        ext
          ? `"${raw.name}" — ${ext} files aren't supported. TwinkTalks reads ${SUPPORTED_EXTENSIONS.join(', ')}.`
          : `"${raw.name}" has no file extension. TwinkTalks reads ${SUPPORTED_EXTENSIONS.join(', ')}.`,
      )
      return
    }
    setBusy(true)
    try {
      if (file) await api.deleteFile(file.id).catch(() => {})
      const meta = await api.uploadFile(raw)
      setFile(meta)
      applySmartDefaults(meta)
    } catch (e) {
      setError(prettyError(e))
    } finally {
      setBusy(false)
    }
  }, [file, applySmartDefaults])

  const handleReplace = useCallback(async () => {
    if (file) {
      api.deleteFile(file.id).catch(() => {})
      setFile(null)
      // Reset "touched" so next file's smart defaults apply cleanly.
      userTouched.current.clear()
    }
  }, [file])

  const handleApplyPreset = useCallback((preset: Preset) => {
    const matching = voices.find(v => v.speaker === preset.speaker)
    setSettings(s => ({
      ...s,
      voice_id: matching?.id ?? s.voice_id,
      speed: preset.speed,
      instruct: preset.instruct,
    }))
    userTouched.current.add('speed')
    userTouched.current.add('instruct')
    userTouched.current.add('voice_id')
  }, [voices])

  const handleSavePreset = useCallback(async (name: string) => {
    const v = voices.find(vv => vv.id === settings.voice_id)
    if (!v) return
    try {
      await api.savePreset({
        name, speaker: v.speaker,
        speed: settings.speed, instruct: settings.instruct,
      })
      const fresh = await api.presets()
      setPresets(fresh)
      setSaveName('')
    } catch (e) {
      setError(prettyError(e))
    }
  }, [voices, settings])

  const handleDeletePreset = useCallback(async (name: string) => {
    try {
      await api.deletePreset(name)
      const fresh = await api.presets()
      setPresets(fresh)
    } catch (e) {
      setError(prettyError(e))
    }
  }, [])

  const startJobAndStream = useCallback(async (
    starter: () => Promise<{ job_id: string; status: string }>,
    mode: 'generate' | 'preview',
  ) => {
    if (!file || busy) return
    setError(null)
    setBusy(true)
    try {
      const { job_id } = await starter()
      setCurrentJobId(job_id)
      eventSourceRef.current?.close()
      const es = new EventSource(api.jobStreamUrl(job_id))
      eventSourceRef.current = es

      const baseFilename = file.title || file.name
      setActiveJob({
        job_id,
        current: 0,
        total: 1,
        duration_s: 0,
        eta_s: 0,
        filename: mode === 'preview' ? `Preview · ${baseFilename}` : baseFilename,
        phase: 'synthesizing',
      })

      es.addEventListener('model_loading', (ev: MessageEvent) => {
        const data = ev.data ? JSON.parse(ev.data) : {}
        setActiveJob(prev => prev && {
          ...prev,
          phase: 'loading_model',
          model_needs_download: !!data.needs_download,
        })
      })

      es.addEventListener('model_loaded', () => {
        setActiveJob(prev => prev && { ...prev, phase: 'synthesizing' })
      })

      es.addEventListener('progress', (ev: MessageEvent) => {
        const data = JSON.parse(ev.data)
        setActiveJob(prev => prev && {
          ...prev,
          phase: 'synthesizing',
          current: data.current,
          total: data.total,
          duration_s: data.duration_s,
          eta_s: data.eta_s,
        })
      })

      es.addEventListener('done', (ev: MessageEvent) => {
        const data = JSON.parse(ev.data)
        es.close()
        setBusy(false)
        setActiveJob(null)
        const stem = (file.title || file.name).replace(/\.[^.]+$/, '')
        const ext = data.format || (mode === 'preview' ? 'wav' : 'mp3')
        setCurrentAudio({
          url: data.audio_url,
          name: mode === 'preview' ? `${stem}_preview.${ext}` : `${stem}.${ext}`,
        })
        if (audioRef.current) {
          audioRef.current.src = data.audio_url
          // Auto-play only for short previews (≤60s of audition). Full
          // generations can finish hours later when the user has walked
          // away — surprise audio blasting from the laptop is bad UX.
          if (mode === 'preview') {
            audioRef.current.play().catch(() => {})
          }
        }
        // Previews don't land in the library, so don't bother refreshing it.
        if (mode === 'generate') {
          api.library().then(setLibrary).catch(() => {})
        }
      })

      es.addEventListener('cancelled', () => {
        es.close()
        setBusy(false)
        setActiveJob(null)
        setCurrentJobId(null)
      })

      es.addEventListener('error', (ev: MessageEvent) => {
        const data = ev.data ? JSON.parse(ev.data) : { message: 'Stream closed unexpectedly' }
        es.close()
        setError(data.message || `${mode === 'preview' ? 'Preview' : 'Synthesis'} failed`)
        setBusy(false)
        setActiveJob(null)
        setCurrentJobId(null)
      })
    } catch (e) {
      setError(prettyError(e))
      setBusy(false)
    }
  }, [file, busy])

  const handleGenerate = useCallback(() => {
    if (!file) return
    return startJobAndStream(
      () => api.startJob({ file_id: file.id, ...settings }),
      'generate',
    )
  }, [file, settings, startJobAndStream])

  const handlePreview = useCallback(() => {
    if (!file) return
    return startJobAndStream(
      () => api.startPreviewJob({ file_id: file.id, ...settings }),
      'preview',
    )
  }, [file, settings, startJobAndStream])

  const handleCancel = useCallback(async () => {
    // Optimistic teardown — close the SSE and reset state immediately so
    // the user sees the UI return to idle without waiting for the server's
    // 'cancelled' event to fly back through the stream.
    eventSourceRef.current?.close()
    eventSourceRef.current = null
    setBusy(false)
    setActiveJob(null)
    if (currentJobId) {
      api.cancelJob(currentJobId).catch(() => {/* best-effort */})
    }
    setCurrentJobId(null)
  }, [currentJobId])

  // Prevent the browser from opening files dropped anywhere outside our
  // explicit drop targets. Without this, dropping on padding / FileCard /
  // sidebar makes the browser navigate to the file instead of uploading.
  useEffect(() => {
    const onDragOver = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes('Files')) e.preventDefault()
    }
    const onDrop = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes('Files')) e.preventDefault()
    }
    window.addEventListener('dragover', onDragOver)
    window.addEventListener('drop', onDrop)
    return () => {
      window.removeEventListener('dragover', onDragOver)
      window.removeEventListener('drop', onDrop)
    }
  }, [])

  // ⌘⏎ shortcut
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey
      if (!meta) return
      if (e.key === 'Enter' && file && !busy) {
        e.preventDefault()
        void handleGenerate()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [file, busy, handleGenerate])

  const handlePlay = useCallback((entry: LibraryEntry) => {
    if (!audioRef.current) return
    audioRef.current.src = entry.audio_url
    audioRef.current.play().catch(() => {})
    setCurrentAudio({ url: entry.audio_url, name: entry.name })
  }, [])

  const handleDelete = useCallback(async (entry: LibraryEntry) => {
    const ok = window.confirm(
      `Delete "${entry.title || entry.name}" from your library?\n\nThis removes the file from ~/Audiobooks/ — there's no undo.`
    )
    if (!ok) return
    try {
      await api.deleteLibraryEntry(entry.id)
      setLibrary(prev => prev.filter(e => e.id !== entry.id))
      // If the deleted file is what's currently in the audio element, clear it.
      if (currentAudio?.url === entry.audio_url) {
        setCurrentAudio(null)
        if (audioRef.current) {
          audioRef.current.removeAttribute('src')
          audioRef.current.load()
        }
      }
    } catch (e) {
      setError(prettyError(e))
    }
  }, [currentAudio])

  return (
    <>
      <main style={{ maxWidth: 1080, margin: '0 auto', padding: '56px 32px 80px' }}>
        <Hero theme={theme} setTheme={setTheme} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 32 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {file ? (
              <>
                <FileCard
                  file={file}
                  onReplace={handleReplace}
                  onPick={handleUpload}
                  speedFactor={settings.speed}
                />
                {file.needs_ocr && (
                  <ScannedNotice forced={settings.ocr && !file.needs_ocr} />
                )}
                <ScopePicker
                  file={file}
                  pageStart={settings.page_start}
                  pageEnd={settings.page_end}
                  onChange={r => updateSettings({ page_start: r.start, page_end: r.end })}
                />
              </>
            ) : (
              <Dropzone onPick={handleUpload} />
            )}

            <div>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Voice</div>
              <div style={{ fontSize: 12, color: 'var(--dim)', marginBottom: 12 }}>
                {backendSubtitle(activeBackend, voices.length)}
              </div>
              <VoicePicker
                voices={voices}
                value={settings.voice_id}
                onChange={id => updateSettings({ voice_id: id })}
              />
              {/* Voice style + presets only mean something on a backend that
                  accepts natural-language instruct prompts. Kokoro doesn't,
                  and its voices wouldn't match the Qwen-keyed built-in
                  presets either, so the whole block is hidden there. */}
              {activeBackend?.supports_instruct && (
                <VoiceStyleControls
                  presets={presets}
                  instruct={settings.instruct}
                  saveName={saveName}
                  supportsInstruct={true}
                  onInstructChange={v => updateSettings({ instruct: v })}
                  onSaveNameChange={setSaveName}
                  onApplyPreset={handleApplyPreset}
                  onSavePreset={handleSavePreset}
                  onDeletePreset={handleDeletePreset}
                />
              )}
            </div>

            <SettingsList
              settings={settings}
              onChange={updateSettings}
              languages={languages}
              advancedOpen={advancedOpen}
              onToggleAdvanced={() => setAdvancedOpen(o => !o)}
            />

            {error && (
              <div
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: 12,
                  color: '#dc2626',
                  fontSize: 12,
                }}
              >
                {error}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <audio ref={audioRef} controls style={{ flex: 1, minWidth: 0 }} />
              {currentAudio && (
                <a
                  href={currentAudio.url}
                  download={currentAudio.name}
                  title={`Download ${currentAudio.name}`}
                  style={{
                    flexShrink: 0,
                    width: 36,
                    height: 36,
                    display: 'inline-grid',
                    placeItems: 'center',
                    border: '1px solid var(--line)',
                    borderRadius: 8,
                    background: 'var(--bg)',
                    color: 'var(--ink)',
                    textDecoration: 'none',
                    cursor: 'pointer',
                    transition: 'border-color 120ms ease, background 120ms ease',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-soft)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg)' }}
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M7 1v9M3.5 6.5L7 10l3.5-3.5M2 12.5h10" />
                  </svg>
                </a>
              )}
            </div>

            <div
              style={{
                position: 'sticky',
                bottom: 24,
                zIndex: 5,
                display: 'flex',
                gap: 8,
              }}
            >
              {busy ? (
                <button
                  onClick={handleCancel}
                  title="Cancel the running job and return to idle."
                  style={{
                    flex: 1,
                    background: 'var(--bg)',
                    color: 'var(--ink)',
                    border: '1px solid var(--line-strong)',
                    borderRadius: 8,
                    padding: '14px',
                    fontSize: 14,
                    fontWeight: 500,
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                  }}
                >
                  <svg width="11" height="11" viewBox="0 0 11 11" fill="currentColor">
                    <rect x="2" y="2" width="7" height="7" rx="1" />
                  </svg>
                  Cancel
                </button>
              ) : (
                <>
                  <button
                    onClick={handlePreview}
                    disabled={!file}
                    title="Render only the first chunk so you can audition the voice + speed before committing."
                    style={{
                      background: 'var(--bg)',
                      color: !file ? 'var(--dim)' : 'var(--ink)',
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      padding: '14px 18px',
                      fontSize: 13,
                      fontWeight: 500,
                      cursor: !file ? 'not-allowed' : 'pointer',
                      fontFamily: 'inherit',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 8,
                      flexShrink: 0,
                    }}
                  >
                    <svg width="11" height="11" viewBox="0 0 11 11" fill="currentColor">
                      <path d="M3 1.5l6 4-6 4z" />
                    </svg>
                    Preview
                  </button>
                  <div style={{ flex: 1 }}>
                    <GenerateButton
                      onClick={handleGenerate}
                      disabled={!file}
                      label="Generate audio"
                    />
                  </div>
                </>
              )}
            </div>
          </div>

          <aside>
            <div style={{ position: 'sticky', top: 32, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <ActiveJob job={activeJob} />
              <Library entries={library} onPlay={handlePlay} onDelete={handleDelete} />
              <div style={{ fontSize: 11, color: 'var(--dim-2)', padding: '0 4px', lineHeight: 1.5 }}>
                Local-first. Audio is processed on this machine; nothing is uploaded.
              </div>
            </div>
          </aside>
        </div>
      </main>
    </>
  )
}

function backendSubtitle(b: BackendInfo | null, voiceCount: number): string {
  if (!b) return `${voiceCount} voices`
  if (b.name === 'qwen') {
    return `${voiceCount} voices from Qwen3-TTS — multilingual, supports voice-style prompts.`
  }
  if (b.name === 'kokoro') {
    return `${voiceCount} Kokoro-82M voices across 9 languages — ~10× faster than Qwen, no voice-style prompts.`
  }
  return `${voiceCount} voices`
}


/** Strip raw status codes + JSON wrappers from fetch errors so the panel
 *  shows the human-readable detail instead of `Error: 415 {"detail":"…"}`. */
function prettyError(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e)
  // jsonOrThrow throws "Error: <status> <body>". Pull <body> out and try to
  // unwrap a {detail: ...} payload.
  const m = /^\s*\d{3}\s+(.+)$/.exec(msg)
  const body = m ? m[1] : msg
  try {
    const parsed = JSON.parse(body)
    if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
      return String(parsed.detail)
    }
  } catch {
    // not JSON, fall through
  }
  return body.replace(/^Error:\s*/, '')
}


function ScannedNotice({ forced }: { forced: boolean }) {
  return (
    <div
      style={{
        border: '1px solid var(--line)',
        borderRadius: 12,
        background: 'color-mix(in srgb, var(--accent) 6%, var(--bg))',
        padding: '12px 14px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        fontSize: 12.5,
        lineHeight: 1.5,
        color: 'var(--ink)',
      }}
    >
      <span
        aria-hidden
        style={{
          flexShrink: 0,
          width: 18,
          height: 18,
          borderRadius: '50%',
          background: 'var(--accent)',
          color: '#fff',
          fontSize: 11,
          fontWeight: 600,
          display: 'grid',
          placeItems: 'center',
          marginTop: 1,
        }}
      >
        i
      </span>
      <span>
        <strong>This PDF looks scanned.</strong> No text layer was found — TwinkTalks will run OCR
        (Tesseract) before generating audio. {forced ? '' : 'You can disable this in Advanced if the heuristic is wrong.'}{' '}
        Make sure <code style={{ fontFamily: 'var(--font-mono)' }}>ocrmypdf</code> + <code style={{ fontFamily: 'var(--font-mono)' }}>tesseract</code> are installed (<code style={{ fontFamily: 'var(--font-mono)' }}>brew install tesseract ghostscript qpdf && pip install ocrmypdf</code>).
      </span>
    </div>
  )
}
