import { useEffect, useMemo, useState } from 'react'
import type { Voice } from '../types'

type Props = {
  voices: Voice[]
  value: string
  onChange: (id: string) => void
}

const VISIBLE_LIMIT = 6

const GENDER_SYMBOL: Record<string, string> = {
  'Female': '♀',
  'Male':   '♂',
}

export function VoicePicker({ voices, value, onChange }: Props) {
  const hasLanguage = voices.some(v => v.language)
  const hasGender   = voices.some(v => v.gender)

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
  const [expanded, setExpanded] = useState(false)

  const filtered = useMemo(
    () => voices.filter(v => {
      if (langFilter !== 'all' && v.language && v.language !== langFilter) return false
      if (genderFilter !== 'all' && v.gender && v.gender !== genderFilter) return false
      return true
    }),
    [voices, langFilter, genderFilter],
  )

  // Always make sure the currently selected voice is visible, even when it
  // would otherwise be past the show-more cutoff.
  const visible = useMemo(() => {
    if (expanded || filtered.length <= VISIBLE_LIMIT) return filtered
    const head = filtered.slice(0, VISIBLE_LIMIT)
    if (head.some(v => v.id === value)) return head
    const selected = filtered.find(v => v.id === value)
    return selected ? [...head.slice(0, VISIBLE_LIMIT - 1), selected] : head
  }, [filtered, expanded, value])

  // Collapse back to the limited view when filters change — feels less stale
  // than carrying an open state across an unrelated filter.
  useEffect(() => { setExpanded(false) }, [langFilter, genderFilter])

  const hidden = filtered.length - visible.length

  return (
    <>
      {(hasLanguage || hasGender) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
          {hasLanguage && (
            <FilterRow label="Language" options={['all', ...languages]} value={langFilter} onChange={setLangFilter} />
          )}
          {hasGender && (
            <FilterRow label="Gender" options={['all', ...genders]} value={genderFilter} onChange={setGenderFilter} />
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {visible.map(v => (
          <VoiceTile
            key={v.id}
            voice={v}
            active={value === v.id}
            onClick={() => onChange(v.id)}
          />
        ))}
        {filtered.length === 0 && (
          <div style={{
            gridColumn: '1 / -1', padding: 16, fontSize: 12, color: 'var(--dim)', textAlign: 'center',
          }}>
            No voices match this filter.
          </div>
        )}
      </div>

      {(hidden > 0 || expanded) && filtered.length > VISIBLE_LIMIT && (
        <button
          onClick={() => setExpanded(e => !e)}
          style={{
            marginTop: 8,
            width: '100%',
            background: 'transparent',
            border: '1px dashed var(--line)',
            borderRadius: 8,
            color: 'var(--dim)',
            padding: '8px 12px',
            fontSize: 12,
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          {expanded
            ? `Show fewer voices`
            : `Show all ${filtered.length} voices →`}
        </button>
      )}
    </>
  )
}

function VoiceTile({
  voice: v,
  active,
  onClick,
}: { voice: Voice; active: boolean; onClick: () => void }) {
  const gender = v.gender ? GENDER_SYMBOL[v.gender] : ''

  return (
    <button
      onClick={onClick}
      title={v.tag || v.name}
      style={{
        // 2px transparent border baseline; recolor on active. No box-shadow
        // halo, no padding swap — total tile size is identical in both
        // states so it doesn't visually grow on click.
        border: '2px solid ' + (active ? 'var(--ink)' : 'transparent'),
        outline: active ? 'none' : '1px solid var(--line)',
        outlineOffset: active ? 0 : -1,
        background: active
          ? 'color-mix(in srgb, var(--ink) 4%, var(--bg))'
          : 'var(--bg)',
        borderRadius: 8,
        padding: '12px 14px',
        textAlign: 'left',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        transition: 'border-color 120ms ease, background 120ms ease',
        color: 'var(--ink)',
        cursor: 'pointer',
        fontFamily: 'inherit',
      }}
    >
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          background: v.avatarColor,
          display: 'grid',
          placeItems: 'center',
          fontSize: 12,
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
          fontSize: 11, color: 'var(--dim)', marginTop: 2,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {v.language && v.gender
            ? `${gender} ${v.language.replace('American ', 'Am. ').replace('British ', 'Br. ')}`
            : v.tag}
        </div>
      </div>
      {active && (
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: 'var(--accent)', flexShrink: 0,
        }} />
      )}
    </button>
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
