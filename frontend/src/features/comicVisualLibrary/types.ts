export type LibraryScope = "PERSONAL" | "COMIC" | "ORGANIZATION" | "INSTITUTIONAL";

export interface VisualLibrary {
  id: string;
  code: string;
  name: string;
  description: string;
  scope: LibraryScope;
  status: string;
}

export interface CharacterIdentity {
  face?: string;
  hair?: string;
  eyes?: string;
  age_group?: string;
  body_type?: string;
  skin_tone?: string;
  glasses?: boolean;
}

export interface ComicCharacter {
  id: string;
  libraryId: string;
  name: string;
  slug: string;
  biography: string;
  personality: Record<string, unknown>;
  identityProfile: CharacterIdentity;
  defaultWardrobe: Record<string, unknown>;
  visualStyle: Record<string, unknown>;
  promptTemplate: string;
  negativePrompt: string;
  identityFingerprint: string;
  currentVersion: number;
  status: string;
  thumbnail?: string;
}

export interface ComicScenario {
  id: string;
  libraryId: string;
  name: string;
  slug: string;
  description: string;
  locationProfile: Record<string, unknown>;
  lightingProfile: Record<string, unknown>;
  requiredObjects: Array<Record<string, unknown>>;
  identityFingerprint: string;
  currentVersion: number;
  status: string;
}

export interface ConsistencyFinding {
  id: string;
  checkCode: string;
  severity: "INFO" | "WARNING" | "ERROR";
  status: string;
  message: string;
  pageId?: string;
  panelId?: string;
}

export interface BatchItem {
  id: string;
  panelId: string;
  status: string;
  retryCount: number;
}

export interface GenerationBatch {
  id: string;
  name: string;
  status: string;
  progressPercent: number;
  items: BatchItem[];
}
