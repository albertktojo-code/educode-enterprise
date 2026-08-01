import type { ReviewThread } from "./types";

interface Props {
  threads: ReviewThread[];
  selectedId?: string;
  onSelect: (thread: ReviewThread) => void;
}

export function CommentSidebar({ threads, selectedId, onSelect }: Props) {
  return (
    <aside className="crp-sidebar" aria-label="Comentarios da revisao">
      <header>
        <h2>Comentarios</h2>
        <span>{threads.filter((item) => item.status !== "RESOLVED").length} pendentes</span>
      </header>
      <div className="crp-thread-list">
        {threads.map((thread) => (
          <button
            type="button"
            className={thread.id === selectedId ? "crp-thread is-active" : "crp-thread"}
            key={thread.id}
            onClick={() => onSelect(thread)}
          >
            <strong>{thread.title}</strong>
            <small>{thread.anchor_type} · {thread.status}</small>
          </button>
        ))}
      </div>
    </aside>
  );
}
