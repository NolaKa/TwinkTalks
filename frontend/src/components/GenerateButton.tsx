type Props = {
  onClick: () => void
  disabled?: boolean
  label?: string
}

export function GenerateButton({ onClick, disabled, label = 'Generate audio' }: Props) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: disabled ? 'var(--bg-soft-2)' : 'var(--ink)',
        color: disabled ? 'var(--dim)' : 'var(--bg)',
        border: 0,
        borderRadius: 8,
        padding: '14px',
        fontSize: 14,
        fontWeight: 500,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'background 150ms ease',
      }}
    >
      {label}
      <span
        className="mono"
        style={{
          background: disabled
            ? 'var(--bg)'
            : 'color-mix(in srgb, var(--bg) 15%, transparent)',
          padding: '2px 7px',
          borderRadius: 4,
          fontSize: 11,
        }}
      >
        ⌘ ⏎
      </span>
    </button>
  )
}
