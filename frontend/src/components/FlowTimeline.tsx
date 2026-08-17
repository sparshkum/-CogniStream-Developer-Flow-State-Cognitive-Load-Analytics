import { Card, Flex, Text, Title } from "@tremor/react";

import type { FlowTimelineBlock } from "../types";

interface Props {
  developer: string;
  date: string;
  blocks: FlowTimelineBlock[];
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function segmentLabel(block: FlowTimelineBlock): string {
  const range = `${formatTime(block.block_start)} - ${formatTime(block.block_end)}`;
  if (block.is_flow_block) return `Deep flow, ${range} (${Math.round(block.duration_minutes)} min)`;
  if (block.interrupted_by) return `Interrupted by ${block.interrupted_by}, ${range}`;
  return `Fragmented coding, ${range} (${Math.round(block.duration_minutes)} min)`;
}

export function FlowTimeline({ developer, date, blocks }: Props) {
  const totalMinutes = blocks.reduce((sum, b) => sum + b.duration_minutes, 0);

  return (
    <Card>
      <Flex justifyContent="between" alignItems="center">
        <Title>Flow Timeline -- {developer || "select a developer"}</Title>
        <Text>{date}</Text>
      </Flex>

      {blocks.length === 0 ? (
        <Text className="mt-6 text-tremor-content-subtle">No coding activity recorded for this day.</Text>
      ) : (
        <>
          <div className="mt-4 flex h-10 w-full overflow-hidden rounded-tremor-default border border-tremor-border">
            {blocks.map((block, i) => (
              <div
                key={i}
                title={segmentLabel(block)}
                className={
                  block.is_flow_block
                    ? "h-full bg-emerald-500 hover:bg-emerald-600"
                    : "h-full bg-red-400 hover:bg-red-500"
                }
                style={{ width: `${(block.duration_minutes / totalMinutes) * 100}%` }}
              />
            ))}
          </div>
          <Flex className="mt-3 gap-4" justifyContent="start">
            <Flex className="w-auto gap-1.5" justifyContent="start">
              <span className="h-3 w-3 rounded-tremor-full bg-emerald-500" />
              <Text>90+ min uninterrupted flow</Text>
            </Flex>
            <Flex className="w-auto gap-1.5" justifyContent="start">
              <span className="h-3 w-3 rounded-tremor-full bg-red-400" />
              <Text>Fragmented by a context switch</Text>
            </Flex>
          </Flex>
        </>
      )}
    </Card>
  );
}
