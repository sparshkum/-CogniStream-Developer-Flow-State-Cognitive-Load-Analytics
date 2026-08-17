import { Callout } from "@tremor/react";
import { useEffect, useState } from "react";

import { api } from "../api/client";
import { ContextSwitchTaxChart } from "../components/ContextSwitchTaxChart";
import { FilterBar } from "../components/FilterBar";
import { FlowBlocksTable } from "../components/FlowBlocksTable";
import { FlowTimeline } from "../components/FlowTimeline";
import { InterruptionSourceChart } from "../components/InterruptionSourceChart";
import { SummaryCards } from "../components/SummaryCards";
import type {
  ContextSwitchTaxRow,
  FlowBlockRow,
  FlowTimelineBlock,
  InterruptionSourceRow,
  SummaryResponse,
} from "../types";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function Dashboard() {
  const [teams, setTeams] = useState<string[]>([]);
  const [developers, setDevelopers] = useState<string[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>("");
  const [selectedDeveloper, setSelectedDeveloper] = useState<string>("");
  const [selectedDate, setSelectedDate] = useState<string>(today());

  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [taxRows, setTaxRows] = useState<ContextSwitchTaxRow[]>([]);
  const [interruptionRows, setInterruptionRows] = useState<InterruptionSourceRow[]>([]);
  const [flowBlockRows, setFlowBlockRows] = useState<FlowBlockRow[]>([]);
  const [timelineBlocks, setTimelineBlocks] = useState<FlowTimelineBlock[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTeams().then(setTeams).catch(() => setError(connectionErrorMessage));
  }, []);

  useEffect(() => {
    api
      .getDevelopers(selectedTeam || undefined)
      .then((devs) => {
        setDevelopers(devs);
        setSelectedDeveloper((current) => (devs.includes(current) ? current : devs[0] ?? ""));
      })
      .catch(() => setError(connectionErrorMessage));
  }, [selectedTeam]);

  useEffect(() => {
    const range = { team: selectedTeam || undefined };
    setError(null);
    Promise.all([
      api.getSummary(range),
      api.getContextSwitchTax(range),
      api.getInterruptionsBySource(range),
      api.getFlowBlocks({ ...range, min_duration: 90 }),
    ])
      .then(([summaryRes, taxRes, interruptionsRes, blocksRes]) => {
        setSummary(summaryRes);
        setTaxRows(taxRes);
        setInterruptionRows(interruptionsRes);
        setFlowBlockRows(blocksRes);
      })
      .catch(() => setError(connectionErrorMessage));
  }, [selectedTeam]);

  useEffect(() => {
    if (!selectedDeveloper) return;
    api
      .getFlowTimeline(selectedDeveloper, selectedDate)
      .then(setTimelineBlocks)
      .catch(() => setError(connectionErrorMessage));
  }, [selectedDeveloper, selectedDate]);

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-6">
      <header>
        <h1 className="text-tremor-metric font-bold text-tremor-content-strong dark:text-dark-tremor-content-strong">
          CogniStream
        </h1>
        <p className="text-tremor-default text-tremor-content dark:text-dark-tremor-content">
          Developer Flow-State &amp; Cognitive Load Analytics -- what actually blocks focused work, not just lines
          of code or tickets closed.
        </p>
      </header>

      {error && (
        <Callout title="Can't reach the CogniStream API" color="red">
          {error}
        </Callout>
      )}

      <FilterBar
        teams={teams}
        developers={developers}
        selectedTeam={selectedTeam}
        selectedDeveloper={selectedDeveloper}
        selectedDate={selectedDate}
        onTeamChange={setSelectedTeam}
        onDeveloperChange={setSelectedDeveloper}
        onDateChange={setSelectedDate}
      />

      <SummaryCards summary={summary} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ContextSwitchTaxChart rows={taxRows} />
        <InterruptionSourceChart rows={interruptionRows} />
      </div>

      <FlowTimeline developer={selectedDeveloper} date={selectedDate} blocks={timelineBlocks} />

      <FlowBlocksTable rows={flowBlockRows} />
    </main>
  );
}

const connectionErrorMessage =
  "The API isn't responding. Make sure the backend + ClickHouse are running (docker-compose up) and the pipeline has loaded data.";
