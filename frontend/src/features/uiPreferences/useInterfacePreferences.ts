import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { uiPreferencesApi } from "./api";
import type {
  InterfacePreferences,
  SidebarMode,
} from "./types";

const STORAGE_KEY = "educode_ui_preferences_v1";

const defaults: InterfacePreferences = {
  sidebarMode: "expanded",
  sidebarWidth: 260,
  editorFocusDefault: false,
  reduceMotion: false,
  lastOpenSection: "",
};

function readLocal(): InterfacePreferences {
  try {
    const parsed = JSON.parse(
      localStorage.getItem(STORAGE_KEY) ?? "{}",
    ) as Partial<InterfacePreferences>;
    return {
      ...defaults,
      ...parsed,
      sidebarWidth:
        parsed.sidebarMode === "compact"
          ? 64
          : Math.max(
              210,
              Math.min(340, parsed.sidebarWidth ?? 260),
            ),
    };
  } catch {
    return defaults;
  }
}

export function useInterfacePreferences() {
  const [preferences, setPreferences] =
    useState<InterfacePreferences>(readLocal);
  const [loaded, setLoaded] = useState(false);
  const saveTimer = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    void uiPreferencesApi
      .get()
      .then((remote) => {
        if (!active) return;
        setPreferences(remote);
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify(remote),
        );
      })
      .catch(() => {
        // Local preference remains available offline.
      })
      .finally(() => {
        if (active) setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const update = useCallback(
    (patch: Partial<InterfacePreferences>) => {
      setPreferences((current) => {
        const next = { ...current, ...patch };
        if (next.sidebarMode === "compact") {
          next.sidebarWidth = 64;
        } else {
          next.sidebarWidth = Math.max(
            210,
            Math.min(340, next.sidebarWidth),
          );
        }
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify(next),
        );
        if (saveTimer.current !== null) {
          window.clearTimeout(saveTimer.current);
        }
        saveTimer.current = window.setTimeout(() => {
          void uiPreferencesApi.save(next).catch(() => {
            // The local copy is retained for the next sync.
          });
        }, 450);
        return next;
      });
    },
    [],
  );

  const setMode = useCallback(
    (sidebarMode: SidebarMode) =>
      update({ sidebarMode }),
    [update],
  );

  return {
    preferences,
    loaded,
    update,
    setMode,
  };
}
