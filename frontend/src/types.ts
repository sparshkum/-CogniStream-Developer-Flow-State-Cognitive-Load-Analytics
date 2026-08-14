// Mirrors backend/app/schemas/metrics.py response shapes exactly.

export interface SummaryResponse {
  developer_count: number;
  total_commits: number;
  total_hours_worked: number;
  avg_context_switch_tax_pct: number;
  total_interruptions: number;
  total_flow_blocks: number;
  avg_flow_block_minutes: number;
}

export interface ContextSwitchTaxRow {
  developer: string;
  team: string;
  flow_minutes: number;
  interrupted_minutes: number;
  total_coding_minutes: number;
  context_switch_tax_pct: number;
}

export interface InterruptionSourceRow {
  source: string;
  count: number;
  pct: number;
}

export interface FlowBlockRow {
  developer: string;
  team: string;
  date: string;
  block_start: string;
  block_end: string;
  duration_minutes: number;
  interrupted_by: string | null;
}

export interface FlowTimelineBlock {
  block_start: string;
  block_end: string;
  duration_minutes: number;
  is_flow_block: boolean;
  interrupted_by: string | null;
}
