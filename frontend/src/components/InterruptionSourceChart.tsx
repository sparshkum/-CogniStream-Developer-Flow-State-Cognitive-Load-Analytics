import { Card, DonutChart, Legend, Title } from "@tremor/react";

import type { InterruptionSourceRow } from "../types";

interface Props {
  rows: InterruptionSourceRow[];
}

const SOURCE_LABELS: Record<string, string> = {
  slack: "Slack messages",
  jira: "Jira ticket pings",
  github: "GitHub review requests",
};

const SOURCE_COLORS: Record<string, string> = {
  slack: "violet",
  jira: "blue",
  github: "gray",
};

export function InterruptionSourceChart({ rows }: Props) {
  const data = rows.map((row) => ({
    name: SOURCE_LABELS[row.source] ?? row.source,
    value: row.count,
  }));
  const colors = rows.map((row) => SOURCE_COLORS[row.source] ?? "gray");

  return (
    <Card>
      <Title>Why Developers Get Interrupted</Title>
      <DonutChart
        className="mt-4 h-56"
        data={data}
        category="value"
        index="name"
        colors={colors}
        valueFormatter={(value: number) => `${value} events`}
      />
      <Legend
        className="mt-3"
        categories={data.map((d) => d.name)}
        colors={colors}
      />
    </Card>
  );
}
