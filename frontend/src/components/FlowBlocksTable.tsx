import {
  Badge,
  Card,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Title,
} from "@tremor/react";

import type { FlowBlockRow } from "../types";

interface Props {
  rows: FlowBlockRow[];
}

function formatRange(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const time = (d: Date) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${time(start)} - ${time(end)}`;
}

export function FlowBlocksTable({ rows }: Props) {
  return (
    <Card>
      <Title>Longest Uninterrupted Flow Blocks</Title>
      <Table className="mt-4">
        <TableHead>
          <TableRow>
            <TableHeaderCell>Developer</TableHeaderCell>
            <TableHeaderCell>Team</TableHeaderCell>
            <TableHeaderCell>Date</TableHeaderCell>
            <TableHeaderCell>Time Range</TableHeaderCell>
            <TableHeaderCell>Duration</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i}>
              <TableCell>{row.developer}</TableCell>
              <TableCell>
                <Badge color={row.team === "Team A" ? "amber" : "blue"}>{row.team}</Badge>
              </TableCell>
              <TableCell>{row.date}</TableCell>
              <TableCell>{formatRange(row.block_start, row.block_end)}</TableCell>
              <TableCell>{Math.round(row.duration_minutes)} min</TableCell>
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5}>No flow blocks in range yet.</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Card>
  );
}
