import type { ReactNode } from 'react'

type EmptyStateIcon = 'folder' | 'search' | 'activity' | 'alert'

type EmptyStateProps = {
  title: string
  description: string
  icon?: EmptyStateIcon
  action?: ReactNode
}

const iconPaths: Record<EmptyStateIcon, string> = {
  folder:
    'M3.75 6.75h5l1.5 1.5h10v9.5a1.5 1.5 0 0 1-1.5 1.5h-15a1.5 1.5 0 0 1-1.5-1.5v-9.5a1.5 1.5 0 0 1 1.5-1.5Z',
  search:
    'm20.25 20.25-4.7-4.7m2.2-5.3a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z',
  activity:
    'M4 12h3.25l2-5.25 4 10.5 2.25-5.25H20',
  alert:
    'M12 8.25v4.5m0 3h.01M10.7 3.8 2.55 18a1.5 1.5 0 0 0 1.3 2.25h16.3a1.5 1.5 0 0 0 1.3-2.25L13.3 3.8a1.5 1.5 0 0 0-2.6 0Z',
}

export function EmptyState({
  title,
  description,
  icon = 'activity',
  action,
}: EmptyStateProps) {
  return (
    <section className="empty-state" role="status" aria-live="polite">
      <span className="empty-state__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <path d={iconPaths[icon]} />
        </svg>
      </span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {action ? <div className="empty-state__action">{action}</div> : null}
    </section>
  )
}
