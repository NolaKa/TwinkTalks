import { useState } from 'react'

type Props = {
  text: string
  /** Distance in px from the trigger to the popover. Default 8. */
  gap?: number
}

/** Tiny "?" icon that reveals an explanatory popover on hover/focus.
 *  Keep the copy short — one or two sentences. */
export function Tooltip({ text, gap = 8 }: Props) {
  const [open, setOpen] = useState(false)
  return (
    <span
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label="Help"
        onClick={e => {
          e.preventDefault()
          e.stopPropagation()
          setOpen(o => !o)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        style={{
          width: 14,
          height: 14,
          padding: 0,
          border: '1px solid var(--line)',
          borderRadius: '50%',
          background: 'transparent',
          color: 'var(--dim-2)',
          fontSize: 9,
          fontWeight: 600,
          fontFamily: 'inherit',
          cursor: 'help',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          lineHeight: 1,
        }}
      >
        ?
      </button>
      {open && (
        <span
          role="tooltip"
          style={{
            position: 'absolute',
            bottom: `calc(100% + ${gap}px)`,
            right: 0,
            zIndex: 20,
            width: 240,
            background: 'var(--ink)',
            color: 'var(--bg)',
            border: '1px solid var(--line-strong)',
            borderRadius: 6,
            padding: '8px 10px',
            fontSize: 12,
            lineHeight: 1.45,
            fontWeight: 400,
            letterSpacing: 0,
            textAlign: 'left',
            boxShadow: '0 6px 18px color-mix(in srgb, var(--ink) 25%, transparent)',
          }}
        >
          {text}
        </span>
      )}
    </span>
  )
}
