export type RiskTier = "very_low" | "low" | "medium" | "high" | "very_high";
export type Recommendation = "approve" | "review" | "decline";
export type Confidence = "low" | "medium" | "high";

export interface Signal {
  category: string;
  name: string;
  key: string;
  value: number | string;
  normalised: number;
  weight: number;
  score_contribution: number;
  direction: "positive" | "neutral" | "negative" | "unknown";
  explanation: string;
  available: boolean;
}

export interface BusinessSummary {
  id?: string;
  name: string;
  registration_number: string;
  trading_age_months?: number | null;
  industry?: string | null;
  province?: string | null;
}

export interface ScoreResponse {
  scoring_request_id: string;
  score: number;
  risk_tier: RiskTier;
  recommendation: Recommendation;
  confidence: Confidence;
  business: BusinessSummary;
  signals: Signal[];
  top_strengths: { name: string; explanation: string; contribution: number }[];
  top_concerns: { name: string; explanation: string; missed_points: number }[];
  penalty_notes: string[];
  data_sources_used: string[];
  data_sources_unavailable: string[];
  processing_ms: number;
  score_generated_at: string;
}

export interface ScoreRequestPayload {
  registration_number: string;
  tax_number?: string;
  statement_months?: number;
  loan_amount_requested?: number;
  loan_term_months?: number;
  use_mock_bank_api?: boolean;
}

export interface HistoryItem {
  id: string;
  business_id: string;
  business_name: string;
  registration_number: string;
  score: number;
  risk_tier: RiskTier;
  recommendation: Recommendation;
  requested_at: string;
  processing_ms: number;
}

export interface HistoryPage {
  items: HistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface Analytics {
  score_distribution: { range: string; count: number }[];
  approval_rate_over_time: { date: string; approval_rate: number; count: number }[];
  average_score_by_industry: { industry: string; average_score: number; count: number }[];
  top_negative_signals: { signal: string; count: number }[];
  total_assessments: number;
  approval_rate: number;
}
