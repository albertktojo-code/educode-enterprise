type ComicCoverProps = {
  title: string
  eyebrow: string
  footer: string
  seed: string
  compact?: boolean
}

const themes = ['azure', 'violet', 'coral', 'emerald', 'sunset'] as const

function themeFor(seed: string) {
  const value = Array.from(seed).reduce(
    (total, character) => total + character.charCodeAt(0),
    0,
  )
  return themes[value % themes.length]
}

export function ComicCover({
  title,
  eyebrow,
  footer,
  seed,
  compact = false,
}: ComicCoverProps) {
  return (
    <div
      className={`comic-cover-art comic-cover-art--${themeFor(seed)}${compact ? ' comic-cover-art--compact' : ''}`}
      aria-hidden="true"
    >
      <span className="comic-cover-art__eyebrow">{eyebrow}</span>
      <strong>{title}</strong>
      <span className="comic-cover-art__footer">{footer}</span>
      <i className="comic-cover-art__burst" />
      <i className="comic-cover-art__dot comic-cover-art__dot--one" />
      <i className="comic-cover-art__dot comic-cover-art__dot--two" />
      <span className="comic-cover-art__mark">EC</span>
    </div>
  )
}
