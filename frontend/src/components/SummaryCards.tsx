import { Card, Flex, Grid, Metric, Text } from "@tremor/react";

import type { SummaryResponse } from "../types";

interface Props {
  summary: SummaryResponse | null;
}

function taxColor(pct: number): string {
  if (pct >= 40) return "text-red-600 dark:text-red-400";
  if (pct >= 20) return "text-amber-600 dark:text-amber-400";
  return "text-emerald-600 dark:text-emerald-400";
}

export function SummaryCards({ summary }: Props) {
  const s = summary;

  return (
    <Grid numItemsSm={2} numItemsLg={5} className="gap-4">
      <Card decoration="top" decorationColor="red">
        <Flex alignItems="start">
          <div>
            <Text>Context-Switching Tax</Text>
            <Metric className={s ? taxColor(s.avg_context_switch_tax_pct) : ""}>
              {s ? `${s.avg_context_switch_tax_pct}%` : "--"}
            </Metric>
          </div>
        </Flex>
        <Text className="mt-2 text-tremor-content-subtle">
          Share of coding time lost before reaching 90+ min of uninterrupted flow
        </Text>
      </Card>

      <Card decoration="top" decorationColor="blue">
        <Text>Avg. Flow Block Duration</Text>
        <Metric>{s ? `${s.avg_flow_block_minutes} min` : "--"}</Metric>
        <Text className="mt-2 text-tremor-content-subtle">Average length of a genuine deep-work session</Text>
      </Card>

      <Card decoration="top" decorationColor="orange">
        <Text>Total Interruptions</Text>
        <Metric>{s ? s.total_interruptions : "--"}</Metric>
        <Text className="mt-2 text-tremor-content-subtle">Slack pings, Jira tickets, GitHub review requests</Text>
      </Card>

      <Card decoration="top" decorationColor="gray">
        <Text>Total Hours Worked</Text>
        <Metric>{s ? s.total_hours_worked : "--"}</Metric>
        <Text className="mt-2 text-tremor-content-subtle">Raw output metric -- the old vanity number</Text>
      </Card>

      <Card decoration="top" decorationColor="gray">
        <Text>Total Commits</Text>
        <Metric>{s ? s.total_commits : "--"}</Metric>
        <Text className="mt-2 text-tremor-content-subtle">Shown for contrast, not as a productivity score</Text>
      </Card>
    </Grid>
  );
}
