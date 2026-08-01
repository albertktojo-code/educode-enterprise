export type ItemFlag =
  | "INSUFFICIENT_SAMPLE"
  | "VERY_EASY"
  | "VERY_DIFFICULT"
  | "NEGATIVE_DISCRIMINATION"
  | "LOW_DISCRIMINATION"
  | "HIGH_OMISSION"
  | "HARDER_THAN_PREDICTED"
  | "EASIER_THAN_PREDICTED";

export interface ItemMetricSummary {
  questionVersionId: string;
  sampleSize: number;
  facilityIndex: number | null;
  observedDifficulty: number | null;
  discriminationIndex: number | null;
  omissionRate: number | null;
  flags: ItemFlag[];
}

export interface SkillMetricSummary {
  skillType: "BNCC" | "COMPUTATIONAL_THINKING" | "INSTITUTIONAL";
  skillCode: string;
  skillName: string;
  sampleSize: number;
  coverageScore: number;
  averageScore: number;
  trend: string | null;
}
