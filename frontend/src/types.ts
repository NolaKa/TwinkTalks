export const SUPPORTED_EXTENSIONS = [
  '.pdf', '.epub',
  '.md', '.txt',
  '.html', '.htm',
  '.docx', '.rtf', '.fb2',
] as const

export type Voice = {
  id: string
  name: string
  speaker: string
  tag: string
  avatarColor: string
}

export type Language = { id: string; name: string }

export type Format = 'wav' | 'mp3' | 'm4b'

export type ChapterOut = {
  title: string
  level: number
  start: number
  end: number
}

export type FileMetadata = {
  id: string
  name: string
  ext: string
  size_bytes: number
  item_count: number
  word_count: number
  est_duration_s: number
  title: string | null
  author: string | null
  has_cover: boolean
  needs_ocr: boolean
  toc: ChapterOut[]
}

export type Settings = {
  voice_id: string
  speed: number
  format: Format
  language: string
  instruct: string
  skip_references: boolean
  skip_tables: boolean
  ocr: boolean
  ocr_language: string
  chapter_markers: boolean
  merge_chapters: boolean
}

export type ActiveJobInfo = {
  job_id: string
  current: number
  total: number
  duration_s: number
  eta_s: number
  filename: string
  // Phase: 'loading_model' (waiting for Qwen weights) or 'synthesizing' (chunks rolling)
  phase?: 'loading_model' | 'synthesizing'
  model_needs_download?: boolean
}

export type Preset = {
  name: string
  speaker: string
  speed: number
  instruct: string
  builtin: boolean
}

export type LibraryEntry = {
  id: string
  name: string
  title: string | null
  author: string | null
  duration_s: number | null
  size_bytes: number
  format: string
  audio_url: string
  cover_url: string | null
}
