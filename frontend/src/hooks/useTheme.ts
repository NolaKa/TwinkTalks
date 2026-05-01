import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark' | 'auto'

const STORAGE_KEY = 'tt-theme'

function readStoredTheme(): Theme {
  if (typeof localStorage === 'undefined') return 'auto'
  const v = localStorage.getItem(STORAGE_KEY)
  return v === 'light' || v === 'dark' || v === 'auto' ? v : 'auto'
}

function systemPrefersDark(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyTheme(theme: Theme) {
  if (typeof document === 'undefined') return
  const effective = theme === 'auto' ? (systemPrefersDark() ? 'dark' : 'light') : theme
  document.documentElement.dataset.theme = effective
}

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme)

  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  // When user picks "auto", follow system changes live.
  useEffect(() => {
    if (theme !== 'auto') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme('auto')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  return [theme, setThemeState]
}
