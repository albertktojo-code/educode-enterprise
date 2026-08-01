type StatusCardProps = {
  title: string
  value: string | number
  detail: string
  state?: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  loading?: boolean
}

export function StatusCard({
  title,
  value,
  detail,
  state = 'neutral',
  loading = false,
}: StatusCardProps) {
  return (
    <article
      className={`status-card status-card--${state}`}
      aria-busy={loading}
    >
      <header className="status-card__header">
        <span className="status-card__label">{title}</span>
        <span className="status-card__signal" aria-hidden="true" />
      </header>
      {loading ? (
        <>
          <span className="skeleton-line skeleton-line--value" />
          <span className="skeleton-line skeleton-line--detail" />
          <span className="sr-only">Carregando {title}</span>
        </>
      ) : (
        <>
          <strong className="status-card__value">{value}</strong>
          <p className="status-card__detail">{detail}</p>
        </>
      )}
    </article>
  )
}
