import {
  useCallback,
  useRef,
  useState,
} from "react";

import type { EditorSnapshot } from "./types";

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(canonical);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, child]) => [key, canonical(child)]),
    );
  }
  return value;
}

export function stableJson(value: unknown): string {
  return JSON.stringify(canonical(value));
}

export async function sha256(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(stableJson(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((item) => item.toString(16).padStart(2, "0"))
    .join("");
}

export function useEditorHistory(initial: EditorSnapshot) {
  const [present, setPresent] = useState(initial);
  const past = useRef<EditorSnapshot[]>([]);
  const future = useRef<EditorSnapshot[]>([]);
  const [, setRevision] = useState(0);

  const commit = useCallback(
    (
      next:
        | EditorSnapshot
        | ((current: EditorSnapshot) => EditorSnapshot),
    ) => {
      setPresent((current) => {
        const resolved =
          typeof next === "function" ? next(current) : next;
        if (stableJson(current) === stableJson(resolved)) {
          return current;
        }
        past.current = [...past.current.slice(-49), current];
        future.current = [];
        setRevision((value) => value + 1);
        return resolved;
      });
    },
    [],
  );

  const replace = useCallback((next: EditorSnapshot) => {
    past.current = [];
    future.current = [];
    setPresent(next);
    setRevision((value) => value + 1);
  }, []);

  const undo = useCallback(() => {
    const previous = past.current.at(-1);
    if (!previous) return;
    setPresent((current) => {
      future.current = [current, ...future.current.slice(0, 49)];
      past.current = past.current.slice(0, -1);
      return previous;
    });
    setRevision((value) => value + 1);
  }, []);

  const redo = useCallback(() => {
    const next = future.current[0];
    if (!next) return;
    setPresent((current) => {
      past.current = [...past.current.slice(-49), current];
      future.current = future.current.slice(1);
      return next;
    });
    setRevision((value) => value + 1);
  }, []);

  return {
    present,
    commit,
    replace,
    undo,
    redo,
    canUndo: past.current.length > 0,
    canRedo: future.current.length > 0,
  };
}


export interface EditorHistory {
  past: EditorSnapshot[];
  present: EditorSnapshot;
  future: EditorSnapshot[];
}

export function createHistory(initial: EditorSnapshot): EditorHistory {
  return { past: [], present: structuredClone(initial), future: [] };
}

export function pushHistory(history: EditorHistory, next: EditorSnapshot): EditorHistory {
  if (stableJson(history.present) === stableJson(next)) return history;
  return {
    past: [...history.past.slice(-49), structuredClone(history.present)],
    present: structuredClone(next),
    future: [],
  };
}

export function undoHistory(history: EditorHistory): { history: EditorHistory; snapshot: EditorSnapshot | null } {
  const previous = history.past.at(-1);
  if (!previous) return { history, snapshot: null };
  const nextHistory: EditorHistory = {
    past: history.past.slice(0, -1),
    present: structuredClone(previous),
    future: [structuredClone(history.present), ...history.future.slice(0, 49)],
  };
  return { history: nextHistory, snapshot: structuredClone(nextHistory.present) };
}

export function redoHistory(history: EditorHistory): { history: EditorHistory; snapshot: EditorSnapshot | null } {
  const next = history.future[0];
  if (!next) return { history, snapshot: null };
  const nextHistory: EditorHistory = {
    past: [...history.past.slice(-49), structuredClone(history.present)],
    present: structuredClone(next),
    future: history.future.slice(1),
  };
  return { history: nextHistory, snapshot: structuredClone(nextHistory.present) };
}
