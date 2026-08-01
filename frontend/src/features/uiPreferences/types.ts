export type SidebarMode =
  | "expanded"
  | "compact"
  | "hidden"
  | "auto";

export interface InterfacePreferences {
  sidebarMode: SidebarMode;
  sidebarWidth: number;
  editorFocusDefault: boolean;
  reduceMotion: boolean;
  lastOpenSection: string;
}
