import type {
  BackendInfo, FileMetadata, Format, Language, LibraryEntry, Preset, Voice,
} from '../types'

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status} ${text}`)
  }
  return res.json()
}

export const api = {
  // Static reference data
  backends: () => fetch('/api/backends').then(r => jsonOrThrow<BackendInfo[]>(r)),
  voices: () => fetch('/api/voices').then(r => jsonOrThrow<Voice[]>(r)),
  languages: () => fetch('/api/languages').then(r => jsonOrThrow<Language[]>(r)),
  formats: () => fetch('/api/formats').then(r => jsonOrThrow<Format[]>(r)),
  presets: () =>
    fetch('/api/presets').then(r =>
      jsonOrThrow<{ builtin: Preset[]; user: Preset[] }>(r),
    ),
  savePreset: (preset: Omit<Preset, 'builtin'>) =>
    fetch('/api/presets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(preset),
    }).then(r => jsonOrThrow<Preset>(r)),
  deletePreset: (name: string) =>
    fetch(`/api/presets/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  // Files
  uploadFile: async (file: File): Promise<FileMetadata> => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/files', { method: 'POST', body: fd })
    return jsonOrThrow<FileMetadata>(res)
  },
  deleteFile: (id: string) =>
    fetch(`/api/files/${id}`, { method: 'DELETE' }),
  preview: (id: string) =>
    fetch(`/api/files/${id}/preview`).then(r =>
      jsonOrThrow<{ text: string; word_count: number; char_count: number }>(r),
    ),
  fileCoverUrl: (id: string) => `/api/files/${id}/cover`,

  // Library
  library: () => fetch('/api/library').then(r => jsonOrThrow<LibraryEntry[]>(r)),
  deleteLibraryEntry: (id: string) =>
    fetch(`/api/library/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  // Jobs
  startJob: (body: Record<string, unknown>) =>
    fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(r => jsonOrThrow<{ job_id: string; status: string }>(r)),
  startPreviewJob: (body: Record<string, unknown>) =>
    fetch('/api/jobs/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(r => jsonOrThrow<{ job_id: string; status: string }>(r)),
  cancelJob: (id: string) =>
    fetch(`/api/jobs/${id}/cancel`, { method: 'POST' }),
  jobStreamUrl: (id: string) => `/api/jobs/${id}/stream`,
  jobAudioUrl: (id: string) => `/api/jobs/${id}/audio`,
}
