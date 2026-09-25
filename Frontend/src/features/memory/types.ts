export type MemoryCategory =
  | "technical_decision"
  | "timeline"
  | "business_rule"
  | "convention";

export interface ProjectMemory {
  id: string;
  project_id: string;
  created_by_user_id: string | null;
  fact_text: string;
  category: MemoryCategory;
  confidence_score: number;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectMemoryCreate {
  fact_text: string;
  category: MemoryCategory;
}

export interface ProjectMemoryUpdate {
  fact_text?: string;
  category?: MemoryCategory;
  is_verified?: boolean;
}
