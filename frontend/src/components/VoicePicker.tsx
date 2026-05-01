import { useMemo, useState } from 'react'
import type { Voice } from '../types'

type Props = {
  voices: Voice[]
  value: string
  onChange: (id: string) => void
}

export function VoicePicker({ voices, value, onChange }: Props) {
  // Filters only show up if the active backend tagged voices with language /
  // gender (Kokoro does, Qwen doesn't).
  const hasLanguage = voices.some(v => v.language)
  const hasGender = voices.some(v => v.gender)

  const languages = useMemo(
    () => Array.from(new Set(voices.map(v => v.language).filter(Boolean) as string[])).sort(),
    [voices],
  )
  const genders = useMemo(
    () => Array.from(new Set(voices.map(v => v.gender).filter(Boolean) as string[])).sort(),
    [voices],
  )

  const [langFilter, setLangFilter] = useState<string>('all')
  const [genderFilter, setGenderFilter] = useState<string>('all')

  const filtered = useMemo(
    () => voices.filter(v => {
      if (langFilter !== 'all' && v.language && v.language !== langFilter) return false
      if (genderFilter !== 'all' && v.gender && v.gender !== genderFilter) return false
      return true
    }),
    [voices, langFilter, genderFilter],
  )

  return (
    <>
      {(hasLanguage || hasGender) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
          {hasLanguage && (
            <FilterRow
              label="Language"
              options={['all', ...languages]}
              value={langFilter}
              onChange={setLangFilter}
            />
          )}
          {hasGender && (
            <FilterRow
              label="Gender"
              options={['all', ...genders]}
              value={genderFilter}
              onChange={setGenderFilter}
            />
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {filtered.map(v => {
          const active = value === v.id
          return (
            <button
              key={v.id}
              onClick={() => onChange(v.id)}
              title={v.tag || v.name}
              style={{
                border: '1px solid ' + (active ? 'var(--ink)' : 'var(--line)'),
                background: 'var(--bg)',
                borderRadius: 8,
                padding: '12px 14px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                boxShadow: active ? '0 0 0 3px var(--bg-soft)' : 'none',
                transition: 'all .12s',
                color: 'var(--ink)',
                cursor: 'pointer',
              }}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  background: v.avatarColor,
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: 11,
                  fontWeight: 600,
                  color: '#5a3a2a',
                  flexShrink: 0,
                }}
              >
                {v.name[0]}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 13, fontWeight: 500,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {v.name}
                </div>
                <div style={{
                  fontSize: 11, color: 'var(--dim)',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {v.tag}
                </div>
              </div>
              {active && (
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)' }} />
              )}
            </button>
          )
        })}
        {filtered.length === 0 && (
          <div style={{
            gridColumn: '1 / -1', padding: 16, fontSize: 12, color: 'var(--dim)',
            textAlign: 'center',
          }}>
            No voices match this filter.
          </div>
        )}
      </div>
    </>
  )
}

function FilterRow({
  label, options, value, onChange,
}: { label: string; options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <span style={{ fontSize: 11, color: 'var(--dim)', minWidth: 60 }}>{label}</span>
      {options.map(opt => {
        const active = value === opt
        return (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            style={{
              border: '1px solid ' + (active ? 'var(--ink)' : 'var(--line)'),
              background: active ? 'var(--bg-soft-2)' : 'var(--bg)',
              color: active ? 'var(--ink)' : 'var(--dim)',
              borderRadius: 999,
              padding: '3px 10px',
              fontSize: 11,
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontWeight: active ? 500 : 400,
            }}
          >
            {opt === 'all' ? 'All' : opt}
          </button>
        )
      })}
    </div>
  )
}
