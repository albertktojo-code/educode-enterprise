import { useEffect, useState } from "react";

import { comicPageEditorApi } from "./api";
import type {
  BubbleConflict,
  BubbleLayer,
  EditorialComment,
} from "./types";

interface Props {
  open: boolean;
  projectId: string;
  panelId?: string;
  pageId?: string;
  schoolYear: string;
  onClose: () => void;
}

export function EditorialPanel({
  open,
  projectId,
  panelId,
  pageId,
  schoolYear,
  onClose,
}: Props) {
  const [layers, setLayers] = useState<BubbleLayer[]>([]);
  const [comments, setComments] = useState<EditorialComment[]>([]);
  const [conflicts, setConflicts] = useState<BubbleConflict[]>([]);
  const [selectedLayerId, setSelectedLayerId] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  const selected = layers.find((item) => item.id === selectedLayerId);

  useEffect(() => {
    if (!open) return;
    void load();
  }, [open, panelId, projectId]);

  async function load(): Promise<void> {
    setBusy(true);
    try {
      const [loadedComments, loadedLayers] = await Promise.all([
        comicPageEditorApi.editorialComments(projectId),
        panelId
          ? comicPageEditorApi.listPanelTextLayers(panelId)
          : Promise.resolve([]),
      ]);
      setComments(loadedComments);
      setLayers(loadedLayers);
      setSelectedLayerId(loadedLayers[0]?.id ?? "");
    } finally {
      setBusy(false);
    }
  }

  async function analyze(): Promise<void> {
    if (!panelId) return;
    const result = await comicPageEditorApi.analyzeBubbles(panelId);
    setConflicts(result.conflicts);
  }

  async function arrange(): Promise<void> {
    if (!panelId || !layers.length) return;
    await comicPageEditorApi.arrangeBubbles(
      panelId,
      layers.map((item) => item.id),
    );
    await load();
  }

  async function shorten(): Promise<void> {
    if (!selected) return;
    const suggestions =
      await comicPageEditorApi.dialogueSuggestions(
        selected.content,
        schoolYear,
      );
    const suggestion = suggestions.find(
      (item) => item.kind === "SHORTEN",
    );
    if (!suggestion) return;
    await comicPageEditorApi.updateTextLayer(selected.id, {
      content: suggestion.suggestion,
    });
    await load();
  }

  async function addComment(): Promise<void> {
    const targetId = selected?.id ?? panelId ?? pageId;
    if (!targetId || !comment.trim()) return;
    await comicPageEditorApi.createEditorialComment(projectId, {
      targetType: selected
        ? "TEXT_LAYER"
        : panelId
          ? "PANEL"
          : "PAGE",
      targetId,
      content: comment.trim(),
      priority: "NORMAL",
    });
    setComment("");
    await load();
  }

  if (!open) return null;

  return (
    <div className="editorial-overlay" role="dialog" aria-modal="true">
      <section className="editorial-dialog">
        <header>
          <div>
            <span className="hq-eyebrow">Sprint 16.10.3</span>
            <h2>Balões e revisão editorial</h2>
          </div>
          <button type="button" onClick={onClose}>Fechar</button>
        </header>

        <div className="editorial-actions">
          <button type="button" disabled={!panelId || busy} onClick={() => void analyze()}>
            Verificar conflitos
          </button>
          <button type="button" disabled={!layers.length || busy} onClick={() => void arrange()}>
            Organizar balões
          </button>
          <button type="button" disabled={!selected || busy} onClick={() => void shorten()}>
            Reduzir fala
          </button>
        </div>

        <div className="editorial-grid">
          <section>
            <h3>Balões do quadro</h3>
            {layers.map((layer) => (
              <button
                type="button"
                key={layer.id}
                className={layer.id === selectedLayerId ? "is-selected" : ""}
                onClick={() => setSelectedLayerId(layer.id)}
              >
                <b>{layer.readingOrder}. {layer.speakerName || layer.layerType}</b>
                <span>{layer.content}</span>
              </button>
            ))}
            {!layers.length ? <p>Nenhum balão neste quadro.</p> : null}
          </section>

          <section>
            <h3>Conflitos</h3>
            {conflicts.map((item, index) => (
              <article key={`${item.code}-${index}`} className={`severity-${item.severity.toLowerCase()}`}>
                <b>{item.severity}</b>
                <span>{item.message}</span>
              </article>
            ))}
            {!conflicts.length ? <p>Nenhum conflito analisado.</p> : null}
          </section>

          <section>
            <h3>Comentários editoriais</h3>
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Comente a página, o quadro ou o balão selecionado."
            />
            <button type="button" onClick={() => void addComment()}>
              Adicionar comentário
            </button>
            {comments.map((item) => (
              <article key={item.id}>
                <b>{item.priority} · {item.status}</b>
                <span>{item.content}</span>
              </article>
            ))}
          </section>
        </div>
      </section>
    </div>
  );
}
