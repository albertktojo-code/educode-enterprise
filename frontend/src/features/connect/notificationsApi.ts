import { api } from '../../lib/api'
import type { NotificationItem } from '../../types/delivery'

export const studentNotificationsApi = {
  list: () => api.get<NotificationItem[]>('/student/notifications'),
  markRead: (notificationId: string) =>
    api.patch<NotificationItem>(`/student/notifications/${notificationId}/read`),
  markAllRead: () =>
    api.patch<{ updated: number }>('/student/notifications/read-all'),
}
