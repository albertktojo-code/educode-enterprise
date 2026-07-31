type LoadingStateProps = {
  label?: string
  rows?: number
}

export function LoadingState({
  label = 'Carregando dados',
  rows = 3,
}: LoadingStateProps) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <div className="loading-state__row" key={index} aria-hidden="true">
          <span className="loading-state__avatar" />
          <span className="loading-state__copy">
            <i />
            <i />
          </span>
        </div>
      ))}
    </div>
  )
}
