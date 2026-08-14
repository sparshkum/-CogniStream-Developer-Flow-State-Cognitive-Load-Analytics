import { BarChart, Card, Title } from "@tremor/react";

import type { ContextSwitchTaxRow } from "../types";

interface Props {
  rows: ContextSwitchTaxRow[];
}

export function ContextSwitchTaxChart({ rows }: Props) {
  const data = rows.map((row) => ({
    developer: `${row.developer} (${row.team})`,
    "Context-Switching Tax %": row.context_switch_tax_pct,
  }));

  return (
    <Card>
      <Title>Context-Switching Tax by Developer</Title>
      <BarChart
        className="mt-4 h-72"
        data={data}
        index="developer"
        categories={["Context-Switching Tax %"]}
        colors={["red"]}
        valueFormatter={(value: number) => `${value}%`}
        yAxisWidth={40}
        showLegend={false}
      />
    </Card>
  );
}
