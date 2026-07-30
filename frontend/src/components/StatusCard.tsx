type StatusCardProps = {
  title: string
  value: string
  detail: string
  state?: 'success' | 'warning' | 'neutral'
}

export function StatusCard({ title, value, detail, state = 'neutral' }: StatusCardProps) {
  return (
    <article className={`status-card status-card--${state}`}>
      <span className="status-card__label">{title}</span>
      <strong className="status-card__value">{value}</strong>
      <p className="status-card__detail">{detail}</p>
    </article>
  )
}
