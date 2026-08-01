import { comicReaderAnalyticsApi } from "./api";
import type { ReaderAnalyticsEventInput } from "./types";

let queue: ReaderAnalyticsEventInput[] = [];
let timer: number | null = null;

export function trackReaderEvent(event: ReaderAnalyticsEventInput): void {
  queue.push(event);
  if (queue.length >= 10) {
    void flushReaderEvents();
    return;
  }
  if (timer === null) {
    timer = window.setTimeout(() => {
      timer = null;
      void flushReaderEvents();
    }, 1200);
  }
}

export async function flushReaderEvents(): Promise<void> {
  if (!queue.length) return;
  const batch = queue.splice(0, 100);
  try {
    await comicReaderAnalyticsApi.events(batch);
  } catch {
    queue = [...batch, ...queue].slice(0, 300);
  }
}
