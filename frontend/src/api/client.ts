import type {
  ContextSwitchTaxRow,
  FlowBlockRow,
  FlowTimelineBlock,
  InterruptionSourceRow,
  SummaryResponse,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface DateRange {
  team?: string;
  from?: string;
  to?: string;
}

async function getJson<T>(path: string, params: object = {}): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, string | number | undefined>)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const qs = query.toString();
  const url = `${API_BASE_URL}${path}${qs ? `?${qs}` : ""}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getTeams: () => getJson<string[]>("/api/teams"),
  getDevelopers: (team?: string) => getJson<string[]>("/api/developers", { team }),
  getSummary: (range: DateRange) => getJson<SummaryResponse>("/api/summary", range),
  getContextSwitchTax: (range: DateRange) => getJson<ContextSwitchTaxRow[]>("/api/context-switch-tax", range),
  getInterruptionsBySource: (range: DateRange) =>
    getJson<InterruptionSourceRow[]>("/api/interruptions-by-source", range),
  getFlowBlocks: (range: DateRange & { min_duration?: number }) =>
    getJson<FlowBlockRow[]>("/api/flow-blocks", range),
  getFlowTimeline: (developer: string, date: string) =>
    getJson<FlowTimelineBlock[]>("/api/flow-timeline", { developer, date }),
};
