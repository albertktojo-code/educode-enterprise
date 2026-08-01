export type QuestionType =
  | "SINGLE_CHOICE"
  | "MULTIPLE_CHOICE"
  | "TRUE_FALSE"
  | "NUMERIC"
  | "SHORT_TEXT"
  | "ESSAY"
  | "PROJECT"
  | "MULTIMEDIA";

export interface QuestionItem {
  id: string;
  code: string;
  title: string;
  subject: string;
  school_year?: string | null;
  status: string;
  current_version: number;
}

export interface Blueprint {
  id: string;
  code: string;
  name: string;
  version: number;
  assessment_type: string;
  status: string;
}

export interface ExternalInstrument {
  id: string;
  code: string;
  name: string;
  version: string;
  instrument_type: string;
  license_status: string;
  status: string;
}
