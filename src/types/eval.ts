/**
 * Evaluation and benchmark validation models.
 * Corresponds to eval/evaluate.py and eval/ring_recovery.py.
 */

export interface MetricScore {
  readonly precision: number;
  readonly recall: number;
  readonly f1_score: number;
  readonly true_positives: number;
  readonly false_positives: number;
  readonly false_negatives: number;
}

export interface ScenarioResult {
  readonly scenario_id: string;
  readonly scenario_type: string;
  readonly description: string;
  readonly ring_id?: string | null;
  readonly expected_rules: readonly string[];
  readonly detected: boolean;
  readonly recovery_jaccard?: number;
  readonly providers_count: number;
  readonly providers_detected: number;
}

export interface EvaluationSummary {
  readonly evaluated_at: string;
  readonly total_claims_evaluated: number;
  readonly total_providers_evaluated: number;
  readonly total_scenarios: number;
  readonly detected_scenarios: number;
  readonly scenario_recall: number;
  readonly claim_metrics: MetricScore;
  readonly provider_metrics: MetricScore;
  readonly ring_recovery_mean_jaccard: number;
  readonly scenario_breakdown: readonly ScenarioResult[];
  readonly rule_performance: Readonly<Record<string, MetricScore>>;
}
