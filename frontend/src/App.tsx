import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api/client'
import { ActiveJob } from './components/ActiveJob'
import { Dropzone } from './components/Dropzone'
import { FileCard } from './components/FileCard'
import { GenerateButton } from './components/GenerateButton'
import { Hero } from './components/Hero'
import { Library } from './components/Library'
import { SettingsList } from './components/SettingsList'
import { Topbar } from './components/Topbar'
import { VoicePicker } from './components/VoicePicker'
import { useTheme } from './hooks/useTheme'
import type {
  ActiveJobInfo, FileMetadata, Language, LibraryEntry, Preset, Settings, Voice,
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
}

export function App() {
  const [theme, setTheme] = useTheme()

  const [voices, setVoices] = useState<Voice[]>([])
  const [languages, setLanguages] = useState<Language[]>([])
  const [presets, setPresets] = useState<{ builtin: Preset[]; user: Preset[] }>({ builtin: [], user: [] })
  const [library, setLibrary] = useState<LibraryEntry[]>([])

  const [file, setFile] = useState<FileMetadata | null>(null)
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [activeJob, setActiveJob] = useState<ActiveJobInfo | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  // Boot: load static data + library
  useEffect(() => {
    api.voices().then(setVoices).catch(e => setError(String(e)))
    api.languages().then(setLanguages).catch(() => {})
    api.presets().then(setPresets).catch(() => {})
    api.library().then(setLibrary).catch(() => {})
  }, [])

  useEffect(() => () => eventSourceRef.current?.close(), [])

  const handleUpload = useCallback(async (raw: File) => {
    setError(null)
    setBusy(true)
    try {
      if (file) await api.deleteFile(file.id).catch(() => {})
      const meta = await api.uploadFile(raw)
      setFile(meta)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }, [file])

  const handleReplace = useCallback(async () => {
    if (file) {
      api.deleteFile(file.id).catch(() => {})
      setFile(null)
    }
  }, [file])

  const updateSettings = useCallback((patch: Partial<Settings>) => {
    setSettings(prev => ({ ...prev, ...patch }))
  }, [])

  const handleApplyPreset = useCallback((preset: Preset) => {
    const matching = voices.find(v => v.speaker === preset.speaker)
    setSettings(s => ({
      ...s,
      voice_id: matching?.id ?? s.voice_id,
      speed: preset.speed,
      instruct: preset.instruct,
    }))
  }, [voices])

  const handleSavePreset = useCallback(async (name: string) => {
    const v = voices.find(vv => vv.id === settings.voice_id)
    if (!v) return
    try {
      await api.savePreset({
        name,
        speaker: v.speaker,
        speed: settings.speed,
        instruct: settings.instruct,
      })
      const fresh = await api.presets()
      setPresets(fresh)
      setSaveName('')
    } catch (e) {
      setError(String(e))
    }
  }, [voices, settings])

  const handleDeletePreset = useCallback(async (name: string) => {
    try {
      await api.deletePreset(name)
      const fresh = await api.presets()
      setPresets(fresh)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  const handleGenerate = useCallback(async () => {
    if (!file || busy) return
    setError(null)
    setBusy(true)
    try {
      const { job_id } = await api.startJob({ file_id: file.id, ...settings })
      eventSourceRef.current?.close()
      const es = new EventSource(api.jobStreamUrl(job_id))
      eventSourceRef.current = es

      setActiveJob({
        job_id,
        current: 0,
        total: 1,
        duration_s: 0,
        eta_s: 0,
        filename: file.title || file.name,
      })

      es.addEventListener('progress', (ev: MessageEvent) => {
        const data = JSON.parse(ev.data)
        setActiveJob(prev => prev && {
          ...prev,
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
        if (audioRef.current) {
          audioRef.current.src = data.audio_url
          audioRef.current.play().catch(() => {})
        }
        api.library().then(setLibrary).catch(() => {})
      })

      es.addEventListener('error', (ev: MessageEvent) => {
        const data = ev.data ? JSON.parse(ev.data) : { message: 'Stream closed unexpectedly' }
        es.close()
        setError(data.message || 'Synthesis failed')
        setBusy(false)
        setActiveJob(null)
      })
    } catch (e) {
      setError(String(e))
      setBusy(false)
    }
  }, [file, settings, busy])

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
  }, [])

  return (
    <>
      <Topbar theme={theme} setTheme={setTheme} />
      <main style={{ maxWidth: 1080, margin: '0 auto', padding: '56px 32px 80px' }}>
        <Hero />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 32 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {file ? (
              <FileCard file={file} onReplace={handleReplace} />
            ) : (
              <Dropzone onPick={handleUpload} />
            )}

            <div>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Voice</div>
              <div style={{ fontSize: 12, color: 'var(--dim)', marginBottom: 12 }}>
                6 presets, all from Qwen3-TTS.
              </div>
              <VoicePicker
                voices={voices}
                value={settings.voice_id}
                onChange={id => updateSettings({ voice_id: id })}
              />
            </div>

            <SettingsList
              settings={settings}
              onChange={updateSettings}
              languages={languages}
              presets={presets}
              onApplyPreset={handleApplyPreset}
              onSavePreset={handleSavePreset}
              onDeletePreset={handleDeletePreset}
              advancedOpen={advancedOpen}
              onToggleAdvanced={() => setAdvancedOpen(o => !o)}
              saveName={saveName}
              onSaveNameChange={setSaveName}
            />

            <GenerateButton
              onClick={handleGenerate}
              disabled={!file || busy}
              label={busy ? 'Working…' : 'Generate audio'}
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

            <audio ref={audioRef} controls style={{ width: '100%' }} />
          </div>

          <aside>
            <div style={{ position: 'sticky', top: 80, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <ActiveJob job={activeJob} />
              <Library entries={library} onPlay={handlePlay} />
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
