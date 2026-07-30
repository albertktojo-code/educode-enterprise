import { api } from "../../lib/api";
import type {
  InterfacePreferences,
  SidebarMode,
} from "./types";

interface RawPreferences {
  sidebar_mode: SidebarMode;
  sidebar_width: number;
  editor_focus_default: boolean;
  reduce_motion: boolean;
  last_open_section: string;
}

function map(item: RawPreferences): InterfacePreferences {
  return {
    sidebarMode: item.sidebar_mode,
    sidebarWidth: item.sidebar_width,
    editorFocusDefault: item.editor_focus_default,
    reduceMotion: item.reduce_motion,
    lastOpenSection: item.last_open_section,
  };
}

export const uiPreferencesApi = {
  get: async (): Promise<InterfacePreferences> =>
    map(await api.get<RawPreferences>("/ui-preferences/me")),
  save: async (
    value: InterfacePreferences,
  ): Promise<InterfacePreferences> =>
    map(
      await api.put<RawPreferences>("/ui-preferences/me", {
        sidebar_mode: value.sidebarMode,
        sidebar_width: value.sidebarWidth,
        editor_focus_default: value.editorFocusDefault,
        reduce_motion: value.reduceMotion,
        last_open_section: value.lastOpenSection,
      }),
    ),
};
