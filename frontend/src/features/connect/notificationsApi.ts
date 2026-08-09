import { api } from '../../lib/api'
import type { NotificationItem } from '../../types/delivery'

export const studentNotificationsApi = {
  list: () => api.get<NotificationItem[]>('/student/notifications'),
  markRead: (notificationId: string) =>
    api.patch<NotificationItem>(`/student/notifications/${notificationId}/read`),
  markAllRead: () =>
    api.patch<{ updated: number }>('/student/notifications/read-all'),
}

export interface ClassroomAnnouncementInput {
  classroom_ids: string[]
  title: string
  message: string
  action_path: string
}

export interface ClassroomAnnouncementResult {
  classrooms: number
  recipients: number
}

export const teacherAnnouncementsApi = {
  send: (input: ClassroomAnnouncementInput) =>
    api.post<ClassroomAnnouncementResult>('/connect/announcements', input),
}
