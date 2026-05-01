import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

type Props = {
  text: string
}

const TOOLTIP_WIDTH = 240
const GAP = 8
const VIEWPORT_PADDING = 8

/** Tiny "?" icon that reveals an explanatory popover on hover/focus.
 *
 *  The popover is rendered through a portal to document.body so that
 *  ancestor `overflow: hidden` (e.g. on the SettingsList card) doesn't
 *  clip it. Position is recomputed on every open and on scroll/resize.
 */
export function Tooltip({ text }: Props) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [pos, setPos] = useState<{ left: number; top: number; placement: 'above' | 'below' } | null>(null)

  const updatePosition = () => {
    const el = triggerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const center = rect.left + rect.width / 2
    let left = center - TOOLTIP_WIDTH / 2
    left = Math.max(
      VIEWPORT_PADDING,
      Math.min(left, window.innerWidth - TOOLTIP_WIDTH - VIEWPORT_PADDING),
    )
    // Default above; if there's not enough room (e.g. tooltip in top rows),
    // flip below.
    const placeAbove = rect.top > 80
    const top = placeAbove ? rect.top - GAP : rect.bottom + GAP
    setPos({ left, top, placement: placeAbove ? 'above' : 'below' })
  }

  useEffect(() => {
    if (!open) {
      setPos(null)
      return
    }
    updatePosition()
    const handler = () => setOpen(false)
    window.addEventListener('scroll', handler, true)
    window.addEventListener('resize', handler)
    return () => {
      window.removeEventListener('scroll', handler, true)
      window.removeEventListener('resize', handler)
    }
  }, [open])

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center' }}>
      <button
        ref={triggerRef}
        type="button"
        aria-label="Help"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={e => {
          e.preventDefault()
          e.stopPropagation()
          setOpen(o => !o)
        }}
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
      {open && pos &&
        createPortal(
          <div
            role="tooltip"
            style={{
              position: 'fixed',
              left: pos.left,
              top: pos.top,
              width: TOOLTIP_WIDTH,
              transform: pos.placement === 'above' ? 'translateY(-100%)' : 'none',
              zIndex: 1000,
              background: 'var(--bg)',
              color: 'var(--ink)',
              border: '1px solid var(--line-strong)',
              borderRadius: 6,
              padding: '8px 10px',
              fontSize: 12,
              lineHeight: 1.45,
              fontFamily: 'var(--font-sans)',
              fontWeight: 400,
              letterSpacing: 0,
              textAlign: 'left',
              boxShadow: '0 6px 18px color-mix(in srgb, var(--ink) 18%, transparent)',
              pointerEvents: 'none',
            }}
          >
            {text}
          </div>,
          document.body,
        )}
    </span>
  )
}
